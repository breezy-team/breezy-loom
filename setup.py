#!/usr/bin/env python2.4
from distutils.core import setup
setup(name="Loom",
      version="0.1~",
      description="Loom plugin for bzr.",
      author="Robert Collins",
      author_email="robert.collins@canonical.com",
      license = "TBD",
      url="https://launchpad.net/products/loom",
      packages=['bzrlib.plugins.loom'],
      package_dir={'bzrlib.plugins.loom': '.'})
