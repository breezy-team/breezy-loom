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


"""Tests of the loom revision-specifiers."""


import bzrlib
from bzrlib.plugins.loom.tests import TestCaseWithLoom
import bzrlib.plugins.loom.tree
from bzrlib.revisionspec import RevisionSpec


class TestThreadRevSpec(TestCaseWithLoom):
    """Tests of the ThreadRevisionSpecifier."""
    
    def test_thread_colon_gets_next_lower_thread(self):
        tree = self.get_tree_with_loom('source')
        tree.branch.new_thread('bottom')
        tree.branch.new_thread('top')
        tree.branch.nick = 'bottom'
        rev_id = tree.commit('change bottom')
        loom_tree = bzrlib.plugins.loom.tree.LoomTreeDecorator(tree)
        loom_tree.up_thread()
        tree.commit('change top')
        spec = RevisionSpec('thread:')
        self.assertEqual(rev_id, spec.in_branch(tree.branch)[1])
