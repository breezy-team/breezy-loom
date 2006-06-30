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

    def test_disk_format(self):
        bzrdir = self.make_bzrdir('.')
        bzrdir.create_repository()
        format = bzrlib.plugins.loom.branch.BzrBranchLoomFormat1()
        branch = format.initialize(bzrdir)
        self.assertFileEqual('', '.bzr/branch/last-loom')

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

    def get_tree_with_loom(self, path="."):
        """Get a tree with no commits in loom format."""
        tree = self.make_branch_and_tree(path)
        format = bzrlib.plugins.loom.branch.BzrBranchLoomFormat1()
        format.take_over(tree.branch)
        return tree.bzrdir.open_workingtree()

    def get_tree_with_one_commit(self, path='.'):
        """Get a tree with a commit in loom format."""
        tree = self.get_tree_with_loom(path=path)
        rev_id = tree.commit('first post')
        return tree

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

    def test_clone_empty_loom(self):
        source_tree = self.get_tree_with_loom('source')
        # assertLoomTreeEqual looks to see if the nick is preserved.
        source_tree.branch.nick = 'source'
        target_tree = source_tree.bzrdir.clone('target').open_workingtree()
        self.assertLoomTreeEqual(source_tree, target_tree)

    def test_sprout_empty_loom(self):
        source_tree = self.get_tree_with_loom('source')
        target_tree = source_tree.bzrdir.sprout('target').open_workingtree()
        self.assertLoomSproutedOk(source_tree, target_tree)
        
    def test_clone_nonempty_loom_top(self):
        """Cloning a nonempty loom at the top should preserve the loom."""
        source_tree = self.get_tree_with_one_commit('source')
        source_tree.branch.new_thread('bottom')
        source_tree.branch.new_thread('top')
        source_tree.branch.nick = 'top'
        source_tree.commit('phwoar', allow_pointless=True)
        source_tree.branch.record_thread('top', source_tree.last_revision())
        target_tree = source_tree.bzrdir.clone('target').open_workingtree()
        self.assertLoomTreeEqual(source_tree, target_tree)

    def test_clone_nonempty_loom_bottom(self):
        """Cloning loom should preserve the current loom pointer."""
        source_tree = self.get_tree_with_one_commit('source')
        source_tree.branch.new_thread('bottom')
        source_tree.branch.new_thread('top')
        source_tree.branch.nick = 'top'
        bottom_rev = source_tree.last_revision()
        source_tree.commit('phwoar', allow_pointless=True)
        source_tree.branch.record_thread('top', source_tree.last_revision())
        # simulate a down_thread... currently trying to avoid a new tree 
        # format - that may be wishful thinking.
        source_tree.branch.nick = 'bottom'
        source_tree.branch.generate_revision_history(bottom_rev)
        source_tree.set_last_revision(bottom_rev)
        # now clone
        target_tree = source_tree.bzrdir.clone('target').open_workingtree()
        self.assertLoomTreeEqual(source_tree, target_tree)

    def test_sprout_nonempty_loom_bottom(self):
        """Sprouting always resets the loom to the top."""
        source_tree = self.get_tree_with_one_commit('source')
        source_tree.branch.new_thread('bottom')
        source_tree.branch.new_thread('top')
        source_tree.branch.nick = 'top'
        bottom_rev = source_tree.last_revision()
        source_tree.commit('phwoar', allow_pointless=True)
        source_tree.branch.record_thread('top', source_tree.last_revision())
        # simulate a down_thread... currently trying to avoid a new tree 
        # format - that may be wishful thinking.
        source_tree.branch.nick = 'bottom'
        source_tree.branch.generate_revision_history(bottom_rev)
        source_tree.set_last_revision(bottom_rev)
        # now sprout
        target_tree = source_tree.bzrdir.sprout('target').open_workingtree()

    def assertLoomSproutedOk(self, source_tree, target_tree):
        """A sprout resets the loom to the top to ensure up-thread works.
        
        Due to the calls made, this will ensure the loom content has been
        pulled, and that the tree state is correct.
        """
        # the loom pointer is the same,
        self.assertEqual(
            source_tree.branch.loom_parents(),
            target_tree.branch.loom_parents())
        # the branch nick is the top warp.
        source_threads = source_tree.branch.get_threads()
        if source_threads:
            self.assertEqual(
                source_threads[-1][0],
                target_tree.branch.nick)
        # no threads, nick is irrelevant
        self.assertEqual(
            source_threads,
            target_tree.branch.get_threads())
        # TODO: refactor generate_revision further into a revision
        # creation routine and a set call: until then change the source
        # to the right thread and compare
        if source_threads:
            source_tree.branch.generate_revision_history(source_threads[-1][1])
        self.assertEqual(
            source_tree.branch.revision_history(),
            target_tree.branch.revision_history())
        self.assertEqual(
            source_tree.branch.last_revision(),
            target_tree.last_revision())


    def assertLoomTreeEqual(self, source_tree, target_tree):
        """Check that the loom state of source_tree and target_tree is equal.
        
        Due to the calls made, this will ensure the loom content has been
        pulled, and that the tree state is correct.
        """
        self.assertEqual(
            source_tree.branch.loom_parents(),
            target_tree.branch.loom_parents())
        self.assertEqual(
            source_tree.branch.nick,
            target_tree.branch.nick)
        self.assertEqual(
            source_tree.branch.get_threads(),
            target_tree.branch.get_threads())
        self.assertEqual(
            source_tree.branch.revision_history(),
            target_tree.branch.revision_history())
        self.assertEqual(
            source_tree.last_revision(),
            target_tree.last_revision())
