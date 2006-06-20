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


"""Tests of the loom Branch related routines."""


import bzrlib
import bzrlib.revision
from bzrlib.tests import TestCaseWithTransport


class TestFormat(TestCaseWithTransport):

    def test_take_over_branch(self):
        branch = self.make_branch('.')
        format = bzrlib.plugins.loom.branch.BzrBranchLoomFormat1()
        branch.lock_write()
        try:
            format.take_over(branch)
        finally:
            branch.unlock()
        # a loomed branch opens with a different format
        branch = bzrlib.branch.Branch.open('.')
        self.assertIsInstance(branch, bzrlib.plugins.loom.branch.LoomBranch)
        # and it should have recorded loom content so we can do
        self.assertFileEqual('', '.bzr/branch/last-loom')
        self.assertEqual([], branch.loom_parents())


class TestLoom(TestCaseWithTransport):

    def test_new_thread_empty_branch(self):
        branch = self.make_branch('.')
        format = bzrlib.plugins.loom.branch.BzrBranchLoomFormat1()
        format.take_over(branch)
        branch = bzrlib.branch.Branch.open('.')
        loom_rev_id = branch.new_thread('foo')
        self.assertNotEqual(None, loom_rev_id)
        self.assertEqual([loom_rev_id], branch.loom_parents())
        self.assertEqual(
            [('foo', bzrlib.revision.NULL_REVISION)],
            branch.get_threads())
        loom_rev_id_2 = branch.new_thread('bar')
        self.assertNotEqual(loom_rev_id, loom_rev_id_2)
        self.assertNotEqual(None, loom_rev_id_2)
        self.assertEqual([loom_rev_id_2], branch.loom_parents())
        self.assertEqual(
            [('foo', bzrlib.revision.NULL_REVISION),
             ('bar', bzrlib.revision.NULL_REVISION)],
            branch.get_threads())

    def test_new_thread_no_duplicate_names(self):
        branch = self.make_branch('.')
        format = bzrlib.plugins.loom.branch.BzrBranchLoomFormat1()
        format.take_over(branch)
        branch = bzrlib.branch.Branch.open('.')
        branch.new_thread('foo')
        self.assertRaises(bzrlib.plugins.loom.branch.DuplicateThreadName, 
            branch.new_thread, 'foo')
        self.assertEqual([('foo', bzrlib.revision.NULL_REVISION)], branch.get_threads())

    def get_tree_with_one_commit(self):
        """Get a tree with a commit in loom format."""
        tree = self.make_branch_and_tree('.')
        rev_id = tree.commit('first post')
        format = bzrlib.plugins.loom.branch.BzrBranchLoomFormat1()
        format.take_over(tree.branch)
        return tree.bzrdir.open_workingtree()

    def test_new_thread_with_commits(self):
        """Test converting a branch to a loom once it has commits."""
        tree = self.get_tree_with_one_commit()
        tree.branch.new_thread('foo')
        self.assertEqual(
            [('foo', tree.last_revision())],
            tree.branch.get_threads())

    def test_new_thread_after(self):
        """Test adding a thread at a nominated position."""
        tree = self.get_tree_with_one_commit()
        rev_id = tree.last_revision()
        tree.branch.new_thread('baseline')
        tree.branch.new_thread('middlepoint')
        tree.branch.new_thread('endpoint')
        tree.branch.nick = 'middlepoint'
        rev_id2 = tree.commit('middle', allow_pointless=True)
        tree.branch.record_thread('middlepoint', rev_id2)
        tree.branch.nick = 'endpoint'
        rev_id3 = tree.commit('end', allow_pointless=True)
        tree.branch.record_thread('endpoint', rev_id3)
        tree.branch.new_thread('afterbase', 'baseline')
        tree.branch.new_thread('aftermiddle', 'middlepoint')
        tree.branch.new_thread('atend', 'endpoint')
        self.assertEqual(
            [('baseline', rev_id),
             ('afterbase', rev_id),
             ('middlepoint', rev_id2),
             ('aftermiddle', rev_id2),
             ('endpoint', rev_id3),
             ('atend', rev_id3),
             ],
            tree.branch.get_threads())

    def test_record_thread(self):
        tree = self.get_tree_with_one_commit()
        tree.branch.new_thread('baseline')
        tree.branch.new_thread('tail')
        tree.branch.nick = 'baseline'
        first_rev = tree.last_revision()
        tree.commit('change something', allow_pointless=True)
        tree.branch.record_thread('baseline', tree.last_revision())
        self.assertEqual(
            [('baseline', tree.last_revision()), ('tail', first_rev)], 
            tree.branch.get_threads())
