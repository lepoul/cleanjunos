#!/usr/bin/python2.7

import logging
import os
from ansible.module_utils.basic import AnsibleModule


try:
    from ansible.module_utils.junosgc import Collector, Cleaner
    HAS_JUNOSGC = True
except ImportError as import_err:
    HAS_JUNOSGC = False
# logger = logging.getLogger('logger')


def clean(module):
    args = module.params
    results = dict()
    results['changed'] = False

    template = os.path.basename(args['template'])
    template_dir = os.path.dirname(args['template'])
    abs_path_to_templ = os.path.abspath(template_dir)

    try:
        dev = Collector(host=args['host'], user=args['user'], password=args['passwd'],
                        defs=args['garbages'], extra_file=args['extra_file'])
        c = Cleaner(dev, args['dest'])
        c.create_deletes(path=abs_path_to_templ, template=template)
        msg = 'Successfully connected and retrieved garbages from {}'.format(args['host'])
        # logger.info(msg)
        results['changed'] = True
    except Exception as err:
       msg = 'Unable to collect garbages from {}: {}'.format(args['host'], str(err))
       module.fail_json(msg=msg)

    module.exit_json(**results)


# ------------------
# Main module
# ------------------


def main():

    module = AnsibleModule(
        argument_spec=dict(
            host=dict(required=True),
            dest=dict(required=True),
            garbages=dict(required=True),
            template=dict(required=True),
            user=dict(required=False, default=os.getenv('USER')),
            extra_file=dict(required=False),
            passwd=dict(required=False, no_log=True)
        )
    )

    if not HAS_JUNOSGC:
        module.fail_json(msg='Could not import junosgc')
    else:
        clean(module)


if __name__ == '__main__':
    main()
