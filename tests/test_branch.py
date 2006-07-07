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
import bzrlib.errors as errors
from bzrlib.plugins.loom.tests import TestCaseWithLoom
from bzrlib.plugins.loom.tree import LoomTreeDecorator
import bzrlib.revision
from bzrlib.tests import TestCaseWithTransport


class TestFormat(TestCaseWithTransport):

    def test_disk_format(self):
        bzrdir = self.make_bzrdir('.')
        bzrdir.create_repository()
        format = bzrlib.plugins.loom.branch.BzrBranchLoomFormat1()
        branch = format.initialize(bzrdir)
        self.assertFileEqual('Loom current 1\n\n', '.bzr/branch/last-loom')

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
        # and it should have no recorded loom content so we can do
        self.assertFileEqual('Loom current 1\n\n', '.bzr/branch/last-loom')
        self.assertEqual([], branch.loom_parents())


class TestLoom(TestCaseWithLoom):

    def test_new_thread_empty_branch(self):
        branch = self.make_branch('.')
        format = bzrlib.plugins.loom.branch.BzrBranchLoomFormat1()
        format.take_over(branch)
        branch = bzrlib.branch.Branch.open('.')
        branch.new_thread('foo')
        # assert that no loom data is committed, this change should
        # have been current-loom only
        self.assertEqual([], branch.loom_parents())
        self.assertEqual(
            [('foo', bzrlib.revision.NULL_REVISION)],
            branch.get_loom_state().get_threads())
        branch.new_thread('bar')
        self.assertEqual([], branch.loom_parents())
        self.assertEqual(
            [('foo', bzrlib.revision.NULL_REVISION),
             ('bar', bzrlib.revision.NULL_REVISION)],
            branch.get_loom_state().get_threads())

    def test_new_thread_no_duplicate_names(self):
        branch = self.make_branch('.')
        format = bzrlib.plugins.loom.branch.BzrBranchLoomFormat1()
        format.take_over(branch)
        branch = bzrlib.branch.Branch.open('.')
        branch.new_thread('foo')
        self.assertRaises(bzrlib.plugins.loom.branch.DuplicateThreadName, 
            branch.new_thread, 'foo')
        self.assertEqual([('foo', bzrlib.revision.NULL_REVISION)], branch.get_loom_state().get_threads())

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
            tree.branch.get_loom_state().get_threads())

    def test_new_thread_after(self):
        """Test adding a thread at a nominated position."""
        tree = self.get_tree_with_one_commit()
        rev_id = tree.last_revision()
        tree.branch.new_thread('baseline')
        tree.branch.new_thread('middlepoint')
        tree.branch.new_thread('endpoint')
        tree.branch.nick = 'middlepoint'
        rev_id2 = tree.commit('middle', allow_pointless=True)
        tree.branch.nick = 'endpoint'
        rev_id3 = tree.commit('end', allow_pointless=True)
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
            tree.branch.get_loom_state().get_threads())

    def test_record_loom_no_changes(self):
        tree = self.get_tree_with_loom()
        self.assertRaises(errors.PointlessCommit, tree.branch.record_loom, 'foo')
            
    def test_record_thread(self):
        tree = self.get_tree_with_one_commit()
        tree.branch.new_thread('baseline')
        tree.branch.new_thread('tail')
        tree.branch.nick = 'baseline'
        first_rev = tree.last_revision()
        # lock the tree to prevent unlock triggering implicit record
        tree.lock_write()
        try:
            tree.commit('change something', allow_pointless=True)
            self.assertEqual(
                [('baseline', first_rev), ('tail', first_rev)], 
                tree.branch.get_loom_state().get_threads())
            tree.branch.record_thread('baseline', tree.last_revision())
            self.assertEqual(
                [('baseline', tree.last_revision()), ('tail', first_rev)], 
                tree.branch.get_loom_state().get_threads())
            self.assertEqual([], tree.branch.loom_parents())
        finally:
            tree.unlock()

    def test_clone_empty_loom(self):
        source_tree = self.get_tree_with_loom('source')
        source_tree.branch.nick = 'source'
        target_tree = source_tree.bzrdir.clone('target').open_workingtree()
        self.assertLoomSproutedOk(source_tree, target_tree)

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
        source_tree.branch.record_loom('commit to loom')
        target_tree = source_tree.bzrdir.clone('target').open_workingtree()
        self.assertLoomSproutedOk(source_tree, target_tree)

    def test_clone_nonempty_loom_bottom(self):
        """Cloning loom should reset the current loom pointer."""
        source_tree = self.get_tree_with_one_commit('source')
        source_tree.branch.new_thread('bottom')
        source_tree.branch.new_thread('top')
        source_tree.branch.nick = 'top'
        source_tree.commit('phwoar', allow_pointless=True)
        source_tree.branch.record_loom('commit to loom')
        LoomTreeDecorator(source_tree).down_thread()
        # now clone
        target_tree = source_tree.bzrdir.clone('target').open_workingtree()
        self.assertLoomSproutedOk(source_tree, target_tree)

    def test_sprout_nonempty_loom_bottom(self):
        """Sprouting always resets the loom to the top."""
        source_tree = self.get_tree_with_one_commit('source')
        source_tree.branch.new_thread('bottom')
        source_tree.branch.new_thread('top')
        source_tree.branch.nick = 'top'
        source_tree.commit('phwoar', allow_pointless=True)
        source_tree.branch.record_loom('commit to loom')
        LoomTreeDecorator(source_tree).down_thread()
        # now sprout
        target_tree = source_tree.bzrdir.sprout('target').open_workingtree()
        self.assertLoomSproutedOk(source_tree, target_tree)

    def assertLoomSproutedOk(self, source_tree, target_tree):
        """A sprout resets the loom to the top to ensure up-thread works.
        
        Due to the calls made, this will ensure the loom content has been
        pulled, and that the tree state is correct.
        """
        # the loom pointer has a parent of the source looms tip
        source_parents = source_tree.branch.loom_parents()
        self.assertEqual(
            source_parents[:1],
            target_tree.branch.loom_parents())
        # the branch nick is the top warp.
        if source_parents:
            source_threads = source_tree.branch.get_threads(rev_id = source_parents[0])
        else:
            source_threads = []
        if source_threads:
            self.assertEqual(
                source_threads[-1][0],
                target_tree.branch.nick)
        # no threads, nick is irrelevant
        self.assertEqual(
            source_threads,
            target_tree.branch.get_loom_state().get_threads())
        # check content is mirrored
        for thread, rev_id in source_threads:
            self.assertTrue(target_tree.branch.repository.has_revision(rev_id))
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

    def test_pull_loom_at_bottom(self):
        """Pulling from a loom when in the bottom warp pulls all warps."""
        source = self.get_tree_with_loom('source')
        source.branch.new_thread('bottom')
        source.branch.new_thread('top')
        source.branch.nick = 'bottom'
        source.branch.record_loom('commit to loom')
        target = source.bzrdir.sprout('target').open_branch()
        target.nick = 'top'
        # put a commit in the bottom and top of this loom
        bottom_rev1 = source.commit('commit my arse')
        source_loom_tree = LoomTreeDecorator(source)
        source_loom_tree.up_thread()
        top_rev1 = source.commit('integrate bottom changes.')
        source_loom_tree.down_thread()
        # and now another commit at the bottom
        bottom_rev2 = source.commit('bottom 2', allow_pointless=True)
        source.branch.record_loom('commit to loom again')
        # we now have two commits in the bottom warp, one in the top, and
        # all three should be pulled. We are pulling into a loom which has
        # a different current thread too, which should not affect us.
        target.pull(source.branch)
        for rev in (bottom_rev1, bottom_rev2, top_rev1):
            self.assertTrue(target.repository.has_revision(rev))
        # check loom threads
        threads = target.get_loom_state().get_threads()
        self.assertEqual(
            [('bottom', bottom_rev2),
             ('top', top_rev1)],
            threads)
        # check loom tip was pulled
        loom_rev_ids = source.branch.loom_parents()
        for rev_id in loom_rev_ids:
            self.assertTrue(target.repository.has_revision(rev_id))
        self.assertEqual(source.branch.loom_parents(), target.loom_parents())

    def test_implicit_record(self):
        tree = self.get_tree_with_loom('source')
        tree.branch.new_thread('bottom')
        tree.branch.nick = 'bottom'
        tree.lock_write()
        try:
            bottom_rev1 = tree.commit('commit my arse')
            # regular commands should not record
            self.assertEqual(
                [('bottom', bzrlib.revision.NULL_REVISION)],
                tree.branch.get_loom_state().get_threads())
        finally:
            tree.unlock()
        # unlocking should have detected the discrepancy and recorded.
        self.assertEqual(
            [('bottom', bottom_rev1)],
            tree.branch.get_loom_state().get_threads())

    def test_trivial_record_loom(self):
        tree = self.get_tree_with_loom('.')
        # for this test, we want to ensure that we have an empty loom-branch.
        self.assertEqual([], tree.branch.loom_parents())
        # add a thread and record it.
        tree.branch.new_thread('bottom')
        tree.branch.nick = 'bottom'
        rev_id = tree.branch.record_loom('Setup test loom.')
        # after recording, the parents list should have changed.
        self.assertEqual([rev_id], tree.branch.loom_parents())

    def test_revert_loom(self):
        tree = self.get_tree_with_loom(',')
        # ensure we have some stuff to revert
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        tree.branch.revert_loom()
        self.assertEqual([], tree.branch.get_loom_state().get_threads())

    def test_revert_thread(self):
        tree = self.get_tree_with_loom(',')
        # ensure we have some stuff to revert
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        # do a commit, so the last_revision should change.
        tree.branch.nick = 'bar'
        tree.commit('bar-ness', allow_pointless=True)
        tree.branch.revert_thread('bar')
        self.assertEqual(
            [('foo', bzrlib.revision.NULL_REVISION)],
            tree.branch.get_loom_state().get_threads())
        self.assertEqual(None, tree.branch.last_revision())
