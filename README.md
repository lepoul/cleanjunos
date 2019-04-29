JunOS Garbage Collection 
========================

//junosgc// is a mini python module for collecting potential configuration garbages 
on a device running JunOS. A garbage is considered a piece of configuration that
is defined in a specific configuration path but is unreferenced. 
User has to define the aforementioned garbage paths.  

The [py-junos-eznc](https://github.com/Juniper/py-junos-eznc) 
is used to connect to the devices and retrieve configuration. 

junosgc
-------

The module connects to a device and retrieves the full configuration in XML format.
User has to define a YAML file with the desired XPath operations to collect 'defined' 
and 'used' items.

```
garbage_definitions: <fixed name>
  'prefix_lists':
    defined: './policy-options/prefix-list/name'
    used:
      - './policy-options/policy-statement/term/from/*[contains(local-name(), "prefix-list")]/list_name'
      - './firewall/family/*/filter/term/from/*[contains(local-name(), "prefix-list")]/name' 
      - './policy-options/policy-statement/term/from/*[contains(local-name(), "prefix-list")]/name'

  'firewalls4':
    defined: './firewall/family/inet/filter/name'
    used: 
      - './interfaces/interface/unit/family/inet/filter/*[contains(local-name(), "put")]/filter-name'
      - './interfaces/interface/unit/family/inet/filter/input-list'
      - './firewall/family/inet/filter/term/filter'

```

The result of the comparison of the above is returned in a dictionary.

This dictionary can then populate a Jinja2 template to create the delete commands. 

```
{% for p in garbages['prefix_lists'] -%}
delete policy-options prefix-list {{ p }}
{% endfor %}

{% for f in garbages['firewalls4'] -%}
delete firewall family inet filter {{ f }}
{% endfor %}

```

//jgarbage// creates a configuration file of delete commands to remove collected garbages. 
Nothing is uploaded/committed/checked automatically.

HOW-TO
------

A way to interact with the module is the cli tool. This should be considered a WIP. 

```
usage: jgarbagec.py [-h] [--garbages GARBAGES] [-d DEV] [--verbose]
                    [--output FILE] [--extra-file EXTRA_FILE]

jgarbagec is a cli tool to collect given JunOS configuration 'garbages'

optional arguments:
  -h, --help            show this help message and exit
  --garbages GARBAGES, -g GARBAGES
                        the path to a .yml file with theXPaths definitions to
                        collect
  -d DEV, --device DEV  Hostname/IP of the device to run garbage collection on
  --verbose, -v         Verbosity level
  --output FILE, -o FILE
                        Path to store the delete commands created
  --extra-file EXTRA_FILE, -e EXTRA_FILE
                        Path to a list of immunes

jgarbagec --host='example.com' --garbage='prefix-lists' --verbose=DEBUG
jgarbagec -h 'example.com' -g 'prefix-lists' -vvvv

```

Ansible module
==============

//junos_garbagec// is an Ansible module based on //junosgc//.

```
    - name: Run garbage collection 
      junos_garbagec:
        host: "{{inventory_hostname}}"
        garbages: "path/to/garbage/definitions" 
        extra_file: "path/to/extra/file/to/use/as/reference"
        template: "path/to/template/to/create/delete/commands" 
        dest: "path/to/save/the/commands"

```
