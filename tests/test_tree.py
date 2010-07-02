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


"""Tests of the loom Tree related routines."""


import bzrlib
from bzrlib import (
    errors,
    merge as _mod_merge,
)

from bzrlib.plugins.loom.branch import EMPTY_REVISION
from bzrlib.plugins.loom.tests import TestCaseWithLoom
import bzrlib.plugins.loom.tree
from bzrlib.revision import NULL_REVISION


class TestTreeDecorator(TestCaseWithLoom):
    """Tests of the LoomTreeDecorator class."""
    
    def get_loom_with_two_threads(self):
        tree = self.get_tree_with_loom('source')
        tree.branch.new_thread('bottom')
        tree.branch.new_thread('top')
        tree.branch._set_nick('bottom')
        return bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)

    def test_down_thread(self):
        tree = self.get_tree_with_loom('source')
        tree.branch.new_thread('bottom')
        tree.branch.new_thread('top')
        tree.branch._set_nick('top')
        loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        loom_tree.down_thread()
        self.assertEqual('bottom', tree.branch.nick)

    def _add_thread(self, tree, name):
        """Create a new thread with a commit and return the commit id."""
        tree.branch.new_thread(name)
        tree.branch._set_nick(name)
        return tree.commit(name)

    def test_down_named_thread(self):
        tree = self.get_tree_with_loom('source')
        loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        bottom_id = self._add_thread(tree, 'bottom')
        self._add_thread(tree, 'middle')
        self._add_thread(tree, 'top')
        self.assertNotEqual(bottom_id, tree.last_revision())
        loom_tree.down_thread('bottom')
        self.assertEqual('bottom', tree.branch.nick)
        self.assertEqual([bottom_id], tree.get_parent_ids())

    def test_up_thread(self):
        loom_tree = self.get_loom_with_two_threads()
        tree = loom_tree.tree
        loom_tree.up_thread()
        self.assertEqual('top', tree.branch.nick)
        self.assertEqual([], tree.get_parent_ids())

    def test_up_to_no_commits(self):
        tree = self.get_tree_with_loom('tree')
        tree.branch.new_thread('bottom')
        tree.branch.new_thread('top')
        tree.branch._set_nick('bottom')
        bottom_rev1 = tree.commit('bottom_commit')
        tree_loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        tree_loom_tree.up_thread()
        self.assertEqual('top', tree.branch.nick)
        self.assertEqual([bottom_rev1], tree.get_parent_ids())

    def test_up_already_merged(self):
        """up-thread into a thread that already has this thread is a no-op."""
        tree = self.get_tree_with_loom('tree')
        tree.branch.new_thread('bottom')
        tree.branch._set_nick('bottom')
        bottom_rev1 = tree.commit('bottom_commit')
        tree.branch.new_thread('top', 'bottom')
        tree.branch._set_nick('top')
        top_rev1 = tree.commit('top_commit', allow_pointless=True)
        tree_loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        tree_loom_tree.down_thread()
        # check the test will be valid
        self.assertEqual([None, bottom_rev1, top_rev1],
            tree.branch.repository.get_ancestry(top_rev1))
        self.assertEqual([bottom_rev1], tree.get_parent_ids())
        tree_loom_tree.up_thread()
        self.assertEqual('top', tree.branch.nick)
        self.assertEqual([top_rev1], tree.get_parent_ids())

    def test_up_not_merged(self):
        """up-thread from a thread with new work."""
        tree = self.get_tree_with_loom('tree')
        tree.branch.new_thread('bottom')
        tree.branch._set_nick('bottom')
        bottom_rev1 = tree.commit('bottom_commit')
        tree.branch.new_thread('top', 'bottom')
        tree.branch._set_nick('top')
        top_rev1 = tree.commit('top_commit', allow_pointless=True)
        tree_loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        tree_loom_tree.down_thread()
        # check the test will be valid
        self.assertEqual([None, bottom_rev1, top_rev1],
            tree.branch.repository.get_ancestry(top_rev1))
        self.assertEqual([bottom_rev1], tree.get_parent_ids())
        bottom_rev2 = tree.commit('bottom_two', allow_pointless=True)
        tree_loom_tree.up_thread()
        self.assertEqual('top', tree.branch.nick)
        self.assertEqual([top_rev1, bottom_rev2], tree.get_parent_ids())

    def test_up_thread_at_top_with_lower_commit(self):
        loom_tree = self.get_loom_with_two_threads()
        self.build_tree_contents([('source/a', 'a')])
        loom_tree.tree.commit('add a')
        loom_tree.up_thread()
        e = self.assertRaises(errors.BzrCommandError, loom_tree.up_thread)
        self.assertEqual('Cannot move up from the highest thread.', str(e))

    def test_up_thread_merge_type(self):
        loom_tree = self.get_loom_with_two_threads()
        self.build_tree_contents([('source/a', 'a')])
        loom_tree.tree.add('a')
        loom_tree.tree.commit('add a')
        loom_tree.up_thread()
        self.build_tree_contents([('source/a', 'b')])
        loom_tree.tree.commit('content to b')
        loom_tree.down_thread()
        self.build_tree_contents([('source/a', 'c')])
        loom_tree.tree.commit('content to c')
        loom_tree.up_thread(_mod_merge.WeaveMerger)
        # Disabled because WeaveMerger writes BASE files now. XXX: Figure out
        # how to test this actually worked, again.
        # self.failIfExists('source/a.BASE')

    def get_loom_with_three_threads(self):
        tree = self.get_tree_with_loom('source')
        tree.branch.new_thread('bottom')
        tree.branch.new_thread('middle')
        tree.branch.new_thread('top')
        tree.branch._set_nick('bottom')
        return bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)

    def test_up_many(self):
        loom_tree = self.get_loom_with_three_threads()
        loom_tree.up_many()
        self.assertEqual('top', loom_tree.tree.branch.nick)
        self.assertEqual([], loom_tree.tree.get_parent_ids())

    def test_up_many_commits(self):
        loom_tree = self.get_loom_with_two_threads()
        loom_tree.tree.commit('bottom', rev_id='bottom-1')
        loom_tree.up_thread()
        loom_tree.tree.commit('top', rev_id='top-1')
        loom_tree.down_thread()
        loom_tree.tree.commit('bottom', rev_id='bottom-2')
        loom_tree.up_many()
        last_revision = loom_tree.tree.last_revision()
        self.assertNotEqual(last_revision, 'top-1')
        rev = loom_tree.tree.branch.repository.get_revision(last_revision)
        self.assertEqual(['top-1', 'bottom-2'], rev.parent_ids)
        self.assertEqual('Merge bottom into top', rev.message)

    def test_up_many_halts_on_conflicts(self):
        loom_tree = self.get_loom_with_three_threads()
        tree = loom_tree.tree
        self.build_tree_contents([('source/file', 'contents-a')])
        tree.add('file')
        tree.commit('bottom', rev_id='bottom-1')
        loom_tree.up_thread()
        self.build_tree_contents([('source/file', 'contents-b')])
        tree.commit('middle', rev_id='middle-1')
        loom_tree.down_thread()
        self.build_tree_contents([('source/file', 'contents-c')])
        tree.commit('bottom', rev_id='bottom-2')
        loom_tree.up_many()
        self.assertEqual('middle', tree.branch.nick)
        self.assertEqual(['middle-1', 'bottom-2'], tree.get_parent_ids())
        self.assertEqual(1, len(tree.conflicts()))

    def test_up_many_target_thread(self):
        loom_tree = self.get_loom_with_three_threads()
        tree = loom_tree.tree
        loom_tree.up_many(target_thread='middle')
        self.assertEqual('middle', tree.branch.nick)

    def test_up_many_target_thread_lower(self):
        loom_tree = self.get_loom_with_three_threads()
        tree = loom_tree.tree
        loom_tree.up_many(target_thread='top')
        e = self.assertRaises(errors.BzrCommandError,
                              loom_tree.up_many, target_thread='middle')
        self.assertEqual('Cannot up-thread to lower thread.', str(e))

    def test_revert_loom(self):
        tree = self.get_tree_with_loom(',')
        # ensure we have some stuff to revert
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        tree.branch._set_nick('bar')
        tree.commit('change something', allow_pointless=True)
        loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        loom_tree.revert_loom()
        # the tree should be reverted
        self.assertEqual(NULL_REVISION, tree.last_revision())
        # the current loom should be reverted 
        # (we assume this means branch.revert_loom was called())
        self.assertEqual([], tree.branch.get_loom_state().get_threads())

    def test_revert_thread(self):
        tree = self.get_tree_with_loom(',')
        # ensure we have some stuff to revert
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        tree.branch._set_nick('bar')
        tree.commit('change something', allow_pointless=True)
        loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        loom_tree.revert_loom(thread='bar')
        # the tree should be reverted
        self.assertEqual(NULL_REVISION, tree.last_revision())
        # the current loom should be reverted 
        # (we assume this means branch.revert_loom was called())
        self.assertEqual(
            [('foo', EMPTY_REVISION, [])],
            tree.branch.get_loom_state().get_threads())
        
    def test_revert_thread_different_thread(self):
        tree = self.get_tree_with_loom(',')
        # ensure we have some stuff to revert
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        tree.branch._set_nick('bar')
        tree.commit('change something', allow_pointless=True)
        loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        loom_tree.revert_loom(thread='foo')
        # the tree should not be reverted
        self.assertNotEqual(NULL_REVISION, tree.last_revision())
        # the bottom thread should be reverted
        # (we assume this means branch.revert_thread was 
        # called())
        self.assertEqual([('bar', tree.last_revision(), [])],
            tree.branch.get_loom_state().get_threads())
