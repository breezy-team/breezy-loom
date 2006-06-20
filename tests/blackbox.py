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


"""UI tests for loom."""


import bzrlib
from bzrlib.tests import TestCaseWithTransport


class TestLoomify(TestCaseWithTransport):

    def test_loomify_new_branch(self):
        b = self.make_branch('.')
        out, err = self.run_bzr('loomify', retcode=3)
        self.assertEqual('', out)
        self.assertEqual(
            'bzr: ERROR: You must have a branch nickname set to loomify a branch\n', 
            err)
        
    def test_loomify_new_branch_with_nick(self):
        b = self.make_branch('.')
        b.nick = 'base'
        out, err = self.run_bzr('loomify')
        # a loomed branch opens with a unique format
        b = bzrlib.branch.Branch.open('.')
        self.assertIsInstance(b, bzrlib.plugins.loom.branch.LoomBranch)
        threads = b.get_threads()
        self.assertEqual(
            [('base', bzrlib.revision.NULL_REVISION)], 
            threads)


class TestCreate(TestCaseWithTransport):
    
    def get_vendor_loom(self):
        """Make a loom with a vendor thread."""
        tree = self.make_branch_and_tree('.')
        tree.branch.nick = 'vendor'
        tree.commit('first release')
        self.run_bzr('loomify')
        return tree.bzrdir.open_workingtree()
    
    def test_create_no_changes(self):
        tree = self.get_vendor_loom()
        out, err = self.run_bzr('create-thread', 'debian')
        self.assertEqual('', out)
        self.assertEqual('', err)
        revid = tree.last_revision()
        self.assertEqual(
            [('vendor', revid), ('debian', revid)],
            tree.branch.get_threads())
        self.assertEqual('debian', tree.branch.nick)

    def test_create_not_end(self):
        tree = self.get_vendor_loom()
        tree.branch.new_thread('debian')
        # now we are at vendor, with debian after, so if we add
        # feature-foo we should get:
        # vendor - feature-foo - debian
        out, err = self.run_bzr('create-thread', 'feature-foo')
        self.assertEqual('', out)
        self.assertEqual('', err)
        revid = tree.last_revision()
        self.assertEqual(
            [('vendor', revid), ('feature-foo', revid), ('debian', revid)],
            tree.branch.get_threads())
        self.assertEqual('feature-foo', tree.branch.nick)

