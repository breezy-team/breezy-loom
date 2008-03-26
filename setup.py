#!/usr/bin/env python2.4
from distutils.core import setup

bzr_plugin_name = 'loom'
bzr_commands = [
    'combine-thread',
    'create-thread',
    'down-thread',
    'loomify',
    'record',
    'revert-loom',
    'show-loom',
    'up-thread',
    ]

# Disk formats
bzr_branch_formats = {
    "Bazaar-NG Loom branch format 1\n":"Loom branch format 1",
    "Bazaar-NG Loom branch format 6\n":"Loom branch format 6",
    }

bzr_plugin_version = (1, 4, 0, 'dev', 0)
bzr_minimum_version = (1, 0, 0)
bzr_maximum_version = None

if __name__ == 'main':
    setup(name="Loom",
          version="1.4.0dev0",
          description="Loom plugin for bzr.",
          author="Canonical Ltd",
          author_email="bazaar@lists.canonical.com",
          license = "GNU GPL v2",
          url="https://launchpad.net/bzr-loom",
          packages=['bzrlib.plugins.loom',
                    'bzrlib.plugins.loom.tests',
                    ],
          package_dir={'bzrlib.plugins.loom': '.'})
