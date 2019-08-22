#!/usr/bin/env python3
from distutils.core import setup

brz_plugin_name = 'loom'
brz_commands = [
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
brz_branch_formats = {
    "Bazaar-NG Loom branch format 1\n": "Loom branch format 1",
    "Bazaar-NG Loom branch format 6\n": "Loom branch format 6",
    }

from version import *

if __name__ == '__main__':
    setup(name="Loom",
          version="3.0.0",
          description="Loom plugin for bzr.",
          author="Canonical Ltd",
          author_email="bazaar@lists.canonical.com",
          license="GNU GPL v2",
          url="https://launchpad.net/brz-loom",
          packages=['breezy.plugins.loom',
                    'breezy.plugins.loom.tests',
                    ],
          package_dir={'breezy.plugins.loom': '.'})
