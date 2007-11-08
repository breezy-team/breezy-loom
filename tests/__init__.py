# Loom, a plugin for bzr to assist in developing focused patches.
# Copyright (C) 2006 Canonical Limited.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation; either version 2 of the License, or
# (at your option) any later version.
# 
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
# 
# You should have received a copy of the GNU General Public License
# along with this program; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA  02110-1301 USA
# 


"""Tests for the loom plugin."""


import bzrlib.plugins.loom.branch
from bzrlib.tests import TestCaseWithTransport
from bzrlib.tests.TestUtil import TestLoader, TestSuite


def test_suite():
    module_names = [
        'bzrlib.plugins.loom.tests.test_branch',
        'bzrlib.plugins.loom.tests.test_loom_io',
        'bzrlib.plugins.loom.tests.test_loom_state',
        'bzrlib.plugins.loom.tests.test_revspec',
        'bzrlib.plugins.loom.tests.test_tree',
        'bzrlib.plugins.loom.tests.blackbox',
        ]
    loader = TestLoader()
    return loader.loadTestsFromModuleNames(module_names)


class TestCaseWithLoom(TestCaseWithTransport):

    def get_tree_with_loom(self, path="."):
        """Get a tree with no commits in loom format."""
        tree = self.make_branch_and_tree(path)
        bzrlib.plugins.loom.branch.loomify(tree.branch)
        return tree.bzrdir.open_workingtree()

