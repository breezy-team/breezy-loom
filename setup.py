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
    'status',
    'up-thread',
    ]

# Disk formats
bzr_branch_formats = {
    "Bazaar-NG Loom branch format 1\n":"Loom branch format 1",
    "Bazaar-NG Loom branch format 6\n":"Loom branch format 6",
    }

from version import *

if __name__ == '__main__':
    setup(name="Loom",
          version="2.2.1dev0",
          description="Loom plugin for bzr.",
          author="Canonical Ltd",
          author_email="bazaar@lists.canonical.com",
          license = "GNU GPL v2",
          url="https://launchpad.net/bzr-loom",
          packages=['breezy.plugins.loom',
                    'breezy.plugins.loom.tests',
                    ],
          package_dir={'breezy.plugins.loom': '.'})
