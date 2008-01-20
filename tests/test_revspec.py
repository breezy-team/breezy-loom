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


"""Tests of the loom revision-specifiers."""


import bzrlib
from bzrlib.plugins.loom.branch import NoLowerThread, NoSuchThread
from bzrlib.plugins.loom.tests import TestCaseWithLoom
import bzrlib.plugins.loom.tree
from bzrlib.revisionspec import RevisionSpec


class TestThreadRevSpec(TestCaseWithLoom):
    """Tests of the ThreadRevisionSpecifier."""
    
    def get_two_thread_loom(self):
        tree = self.get_tree_with_loom('source')
        tree.branch.new_thread('bottom')
        tree.branch.new_thread('top')
        tree.branch.nick = 'bottom'
        rev_id_bottom = tree.commit('change bottom')
        loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        loom_tree.up_thread()
        rev_id_top = tree.commit('change top')
        return tree, loom_tree, rev_id_bottom, rev_id_top
    
    def test_thread_colon_at_bottom_errors(self):
        tree, loom_tree, rev_id, _ = self.get_two_thread_loom()
        loom_tree.down_thread()
        spec = RevisionSpec.from_string('thread:')
        self.assertRaises(NoLowerThread, spec.in_branch, tree.branch)

    def test_thread_colon_gets_next_lower_thread(self):
        tree, loom_tree, rev_id, _ = self.get_two_thread_loom()
        spec = RevisionSpec.from_string('thread:')
        self.assertEqual(rev_id, spec.in_branch(tree.branch)[1])

    def test_thread_colon_bad_name_errors(self):
        tree, loom_tree, _, _ = self.get_two_thread_loom()
        loom_tree.down_thread()
        spec = RevisionSpec.from_string('thread:foo')
        err = self.assertRaises(NoSuchThread, spec.in_branch, tree.branch)
        self.assertEqual('foo', err.thread)

    def test_thread_colon_name_gets_named_thread(self):
        tree, loom_tree, _, rev_id = self.get_two_thread_loom()
        loom_tree.down_thread()
        spec = RevisionSpec.from_string('thread:top')
        self.assertEqual(rev_id, spec.in_branch(tree.branch)[1])
