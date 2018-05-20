# Loom, a plugin for bzr to assist in developing focused patches.
# Copyright (C) 2006 Canonical Limited.
# 
# This program is free software; you can redistribute it and/or modify
# it under the terms of the GNU General Public License version 2 as published
# by the Free Software Foundation.
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


import breezy.plugins.loom.branch
from breezy.tests import TestCaseWithTransport
from breezy.tests.TestUtil import TestLoader, TestSuite
from breezy.workingtree import WorkingTree


def test_suite():
    module_names = [
        'breezy.plugins.loom.tests.test_branch',
        'breezy.plugins.loom.tests.test_loom_io',
        'breezy.plugins.loom.tests.test_loom_state',
        'breezy.plugins.loom.tests.test_revspec',
        'breezy.plugins.loom.tests.test_tree',
        'breezy.plugins.loom.tests.blackbox',
        ]
    loader = TestLoader()
    return loader.loadTestsFromModuleNames(module_names)


class TestCaseWithLoom(TestCaseWithTransport):

    def get_tree_with_loom(self, path="."):
        """Get a tree with no commits in loom format."""
        # May open on Remote - we want the vfs backed version for loom tests.
        self.make_branch_and_tree(path)
        tree = WorkingTree.open(path)
        breezy.plugins.loom.branch.loomify(tree.branch)
        return tree.controldir.open_workingtree()

