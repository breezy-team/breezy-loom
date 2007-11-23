#!/usr/bin/env python2.4
from distutils.core import setup
setup(name="Loom",
      version="0.1~",
      description="Loom plugin for bzr.",
      author="Canonical Ltd",
      author_email="bazaar@lists.canonical.com",
      license = "GNU GPL v2",
      url="https://launchpad.net/bzr-loom",
      packages=['bzrlib.plugins.loom',
                'bzrlib.plugins.loom.tests',
                ],
      package_dir={'bzrlib.plugins.loom': '.'})
