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


"""Tests of the loom Tree related routines."""


import bzrlib
from bzrlib.plugins.loom.tests import TestCaseWithLoom
import bzrlib.plugins.loom.tree
import bzrlib.revision


class TestTreeDecorator(TestCaseWithLoom):
    """Tests of the LoomTreeDecorator class."""
    
    def test_down_thread(self):
        tree = self.get_tree_with_loom('source')
        tree.branch.new_thread('bottom')
        tree.branch.new_thread('top')
        tree.branch.nick = 'top'
        loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        loom_tree.down_thread()
        self.assertEqual('bottom', tree.branch.nick)

    def test_up_thread(self):
        tree = self.get_tree_with_loom('source')
        tree.branch.new_thread('bottom')
        tree.branch.new_thread('top')
        tree.branch.nick = 'bottom'
        loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        loom_tree.up_thread()
        self.assertEqual('top', tree.branch.nick)

    def test_up_to_no_commits(self):
        tree = self.get_tree_with_loom('tree')
        tree.branch.new_thread('bottom')
        tree.branch.new_thread('top')
        tree.branch.nick = 'bottom'
        bottom_rev1 = tree.commit('bottom_commit')
        tree_loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        tree_loom_tree.up_thread()
        self.assertEqual('top', tree.branch.nick)

    def test_revert_loom(self):
        tree = self.get_tree_with_loom(',')
        # ensure we have some stuff to revert
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        tree.branch.nick = 'bar'
        tree.commit('change something', allow_pointless=True)
        loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        loom_tree.revert_loom()
        # the tree should be reverted
        self.assertEqual(None, tree.last_revision())
        # the current loom should be reverted 
        # (we assume this means branch.revert_loom was called())
        self.assertEqual([], tree.branch.get_threads())

    def test_revert_thread(self):
        tree = self.get_tree_with_loom(',')
        # ensure we have some stuff to revert
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        tree.branch.nick = 'bar'
        tree.commit('change something', allow_pointless=True)
        loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        loom_tree.revert_loom(thread='bar')
        # the tree should be reverted
        self.assertEqual(None, tree.last_revision())
        # the current loom should be reverted 
        # (we assume this means branch.revert_loom was called())
        self.assertEqual(
            [('foo', bzrlib.revision.NULL_REVISION)],
            tree.branch.get_threads())
        
    def test_revert_thread_different_thread(self):
        tree = self.get_tree_with_loom(',')
        # ensure we have some stuff to revert
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        tree.branch.nick = 'bar'
        tree.commit('change something', allow_pointless=True)
        loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        loom_tree.revert_loom(thread='foo')
        # the tree should not be reverted
        self.assertNotEqual(None, tree.last_revision())
        # the bottom thread should be reverted
        # (we assume this means branch.revert_thread was 
        # called())
        self.assertEqual([('bar', tree.last_revision())],
            tree.branch.get_threads())
