#!/usr/bin/python2.7

from jnpr.junos.device import Device
from jnpr.junos.exception import *

import logging
import os

import yaml
from xml.etree.ElementTree import fromstring, tostring

from jinja2 import Environment, FileSystemLoader

logger = logging.getLogger('logger')
default_user = os.environ.get('USER')


class Collector(object):

    def __init__(self, host, password=None, defs=None, extra_file=None, user=default_user, port=22):
        self.host = host
        self.user = user
        self.port = port
        self.password = password
        self.__session = self.__connect()
        self.config = None
        self.__get_config()
        self.defs = defs
        self.immune_defs = None
        if self.defs is not None:
            try:

                defs = self.__get_cfg_defs()

                if 'garbage_definitions' in defs:
                    self.gdefs = defs['garbage_definitions']
                else:
                    logging.error("garbage_definitions key not found in the provided definitions file")
                    raise AttributeError("Could not find Garbage definitions in file given")

                if 'immunes' in defs:
                    self.immune_defs = defs['immunes']
                elif extra_file is not None and os.path.isfile(extra_file):
                    self.immune_defs = extra_file
                else:
                    logging.info('No immunes provided, everything unreferenced will be considered as garbage')

            except OSError as err:
                logging.error('Could not find or process the definitions file given: {}'.format(err))
        else:
            raise AttributeError("A garbage definitions file must be provided")

    def __connect(self):
        try:
            dev = Device(host=self.host, user=self.user, port=self.port, password=self.password)
            dev.open()
            return dev
        except Exception as err:
            logger.error('Unable to connect to {} with error: {}.'
                         'Ensure SSH-key pairs, connectivity, passwords'.format(self.host, err))

    def __get_config(self):
        dev = self.__session
        if dev.connected:
            try:
                conf = dev.rpc.get_config()
                dev.close()
                self.config = conf
            except ConnectError as err:
                logger.error('XML RPC get-config failed with error: {}'.format(err))

    def __get_cfg_defs(self):
        if os.path.exists(self.defs):
            try:
                with open(self.defs, 'r') as _cfg:
                    cfg_defs = yaml.load(_cfg)
                return cfg_defs
            except Exception as err:
                logging.error('Unexpected error while loading yaml file: {}'.format(err))

    @property
    def _garbage_paths(self):
        return self.gdefs

    @property
    def garbage_objects(self):

        xpaths = self._garbage_paths
        conf = self.config
        res = dict()

        for gitem, path in xpaths.items():
            found_defined = []
            found_used = []
            res[str(gitem)] = dict()

            for u in path['used']:
                for i in conf.xpath(u):
                    garbage = i.xpath("string()")
                    if garbage not in found_used:
                        found_used.append(garbage)
            res[str(gitem)]['used'] = found_used
            defined = conf.xpath(path['defined'])
            for d in defined:
                d = d.xpath("string()")
                if d not in found_defined:
                    found_defined.append(d)
            res[str(gitem)]['defined'] = found_defined
        return res

    @property
    def immune_objects(self):
        if self.immune_defs is None:
            return None
        elif isinstance(self.immune_defs, str) and os.path.isfile(self.immune_defs):
            defs = self.immune_defs
            if defs.endswith('.set'):
                set_paths = self.__xpath_to_set_path()
                imm_dict = dict()
                for gitem in set_paths:
                    imm_dict[str(gitem)] = list()
                with open(defs, 'r') as conf:
                    for line in conf:
                        for gitem, p in set_paths.items():
                            if p in line:
                                imm_obj = line.strip().split()[len(p.split())]
                                if imm_obj not in imm_dict[str(gitem)]:
                                    imm_dict[str(gitem)].append(imm_obj)
            if defs.endswith('.xml'):
                with open(defs, 'r') as conf:
                    conf = fromstring(conf.read().replace('\n', ''))
                    paths = self._garbage_paths
                    imm_dict = dict()
                    for gitem, p in paths.items():
                        imm_dict[str(gitem)] = list()
                        imms = conf.findall(p['defined'])
                        for i in imms:
                            imm_obj = tostring(i).replace('<name>', '').replace('</name>', '').strip()
                            imm_dict[str(gitem)].append(imm_obj)
            return imm_dict
        elif isinstance(self.immune_defs, dict):
            return self.immune_defs

    def __xpath_to_set_path(self):
        # Used to get a set command from an xpath
        # useful to objectify a .set config file into garbages
        used_paths = self._garbage_paths
        stanzas = dict()
        for g, path in used_paths.items():
            segs = path['defined'].split('/')
            for s in segs:
                if s == 'name' or s == '.':
                    segs.remove(s)
            segs.insert(0, "set")
            stanzas[str(g)] = " ".join((" ".join(segs).split()))
        return stanzas


class Cleaner(object):

    def __init__(self, collector, output):
        self.collector = collector
        self.output = output
        self.unreferenced = self.__find_unref()

    def __find_unref(self):
        garbage = {}
        col = self.collector

        immunes = col.immune_objects

        for i, data in col.garbage_objects.items():
            glist = []
            garbage[str(i)] = {}
            for g in data['defined']:
                if (g not in data['used']) and (g not in glist):
                    if immunes is None or str(i) not in immunes:
                        glist.append(g)
                    elif str(i) in immunes and g not in immunes[str(i)]:
                        glist.append(g)
            garbage[str(i)] = glist
        return garbage

    def create_deletes(self, path='module_utils/templates', template='delete_garbages.j2'):

        env = Environment(loader=FileSystemLoader(path))

        try:
            tmpl = env.get_template(template)
            output = tmpl.render(garbages=self.unreferenced)
            with open(self.output, 'w') as out:
                out.write(output)
                out.close()
        except Exception as err:
            logger.error(err)
