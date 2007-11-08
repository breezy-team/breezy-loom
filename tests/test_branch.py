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
from bzrlib.plugins.loom.branch import (
    EMPTY_REVISION,
    loomify,
    UnsupportedBranchFormat,
    )
from bzrlib.plugins.loom.tests import TestCaseWithLoom
from bzrlib.plugins.loom.tree import LoomTreeDecorator
import bzrlib.revision
from bzrlib.revision import NULL_REVISION
from bzrlib.tests import TestCaseWithTransport


class TestFormat(TestCaseWithTransport):

    def test_disk_format(self):
        bzrdir = self.make_bzrdir('.')
        bzrdir.create_repository()
        format = bzrlib.plugins.loom.branch.BzrBranchLoomFormat1()
        branch = format.initialize(bzrdir)
        self.assertFileEqual('Loom current 1\n\n', '.bzr/branch/last-loom')


class LockableStub(object):

    def __init__(self):
        self._calls = []
        self._format = "Nothing to see."

    def lock_write(self):
        self._calls.append(("write",))

    def unlock(self):
        self._calls.append(("unlock",))


class TestLoomify(TestCaseWithTransport):

    def assertConvertedBranchFormat(self, branch, branch_class, format):
        """Assert that branch has been successfully converted to a loom."""
        self.assertFalse(branch.is_locked())
        # a loomed branch opens with a different format
        branch = bzrlib.branch.Branch.open('.')
        self.assertIsInstance(branch, branch_class)
        self.assertIsInstance(branch._format, format)
        # and it should have no recorded loom content so we can do
        self.assertFileEqual('Loom current 1\n\n', '.bzr/branch/last-loom')
        self.assertEqual([], branch.loom_parents())

    def test_loomify_locks_branch(self):
        # loomify should take out a lock even on a bogus format as someone
        # might e.g. change the format if you don't hold the lock - its what we
        # are about to do!
        branch = LockableStub()
        self.assertRaises(UnsupportedBranchFormat, loomify, branch)
        self.assertEqual([("write",), ("unlock",)], branch._calls)

    def test_loomify_unknown_format(self):
        branch = self.make_branch('.', format='weave')
        self.assertRaises(UnsupportedBranchFormat, loomify, branch)
        self.assertFalse(branch.is_locked())

    def test_loomify_branch_format_5(self):
        branch = self.make_branch('.', format='dirstate')
        loomify(branch)
        self.assertConvertedBranchFormat(branch,
            bzrlib.plugins.loom.branch.LoomBranch,
            bzrlib.plugins.loom.branch.BzrBranchLoomFormat1)

    def test_loomify_branch_format_6(self):
        branch = self.make_branch('.', format='dirstate-tags')
        loomify(branch)
        self.assertConvertedBranchFormat(branch,
            bzrlib.plugins.loom.branch.LoomBranch6,
            bzrlib.plugins.loom.branch.BzrBranchLoomFormat6)


class TestLoom(TestCaseWithLoom):

    def make_loom(self, path):
        bzrlib.plugins.loom.branch.loomify(self.make_branch(path))
        return bzrlib.branch.Branch.open(path)

    def test_new_thread_empty_branch(self):
        branch = self.make_loom('.')
        branch.new_thread('foo')
        # assert that no loom data is committed, this change should
        # have been current-loom only
        self.assertEqual([], branch.loom_parents())
        self.assertEqual(
            [('foo', EMPTY_REVISION, [])],
            branch.get_loom_state().get_threads())
        branch.new_thread('bar')
        self.assertEqual([], branch.loom_parents())
        self.assertEqual(
            [('foo', EMPTY_REVISION, []),
             ('bar', EMPTY_REVISION, [])],
            branch.get_loom_state().get_threads())

    def test_new_thread_no_duplicate_names(self):
        branch = self.make_loom('.')
        branch.new_thread('foo')
        self.assertRaises(bzrlib.plugins.loom.branch.DuplicateThreadName, 
            branch.new_thread, 'foo')
        self.assertEqual(
            [('foo', EMPTY_REVISION, [])],
            branch.get_loom_state().get_threads())

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
            [('foo', tree.last_revision(), [])],
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
            [('baseline', rev_id, []),
             ('afterbase', rev_id, []),
             ('middlepoint', rev_id2, []),
             ('aftermiddle', rev_id2, []),
             ('endpoint', rev_id3, []),
             ('atend', rev_id3, []),
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
                [('baseline', first_rev, []),
                 ('tail', first_rev, [])], 
                tree.branch.get_loom_state().get_threads())
            tree.branch.record_thread('baseline', tree.last_revision())
            self.assertEqual(
                [('baseline', tree.last_revision(), []), 
                 ('tail', first_rev, [])], 
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
        source_threads = source_tree.branch.get_threads(
            source_tree.branch.get_loom_state().get_basis_revision_id())
        if source_threads:
            self.assertEqual(
                source_threads[-1][0],
                target_tree.branch.nick)
        # no threads, nick is irrelevant
        # check that the working threads were created correctly:
        # the same revid for the parents as the created one.
        self.assertEqual(
            [thread + ([thread[1]],) for thread in source_threads],
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
            [('bottom', bottom_rev2, [bottom_rev2]),
             ('top', top_rev1, [top_rev1])],
            threads)
        # check loom tip was pulled
        loom_rev_ids = source.branch.loom_parents()
        for rev_id in loom_rev_ids:
            self.assertTrue(target.repository.has_revision(rev_id))
        self.assertEqual(source.branch.loom_parents(), target.loom_parents())
        
    def test_pull_into_empty_loom(self):
        """Doing a pull into a loom with no loom revisions works."""
        source = self.get_tree_with_loom('source')
        target = source.bzrdir.sprout('target').open_branch()
        source.branch.new_thread('a thread')
        source.branch.nick = 'a thread'
        # put a commit in the thread for source.
        bottom_rev1 = source.commit('commit a thread')
        source.branch.record_loom('commit to loom')
        target.pull(source.branch)
        # check loom threads
        threads = target.get_loom_state().get_threads()
        self.assertEqual(
            [('a thread', bottom_rev1, [bottom_rev1])],
            threads)
        # check loom tip was pulled
        loom_rev_ids = source.branch.loom_parents()
        for rev_id in loom_rev_ids:
            self.assertTrue(target.repository.has_revision(rev_id))
        self.assertEqual(source.branch.loom_parents(), target.loom_parents())

    def test_pull_thread_at_null(self):
        """Doing a pull when the source loom has a thread with no history."""
        source = self.get_tree_with_loom('source')
        target = source.bzrdir.sprout('target').open_branch()
        source.branch.new_thread('a thread')
        source.branch.nick = 'a thread'
        source.branch.record_loom('commit to loom')
        target.pull(source.branch)
        # check loom threads
        threads = target.get_loom_state().get_threads()
        self.assertEqual(
            [('a thread', 'empty:', ['empty:'])],
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
                [('bottom', EMPTY_REVISION, [])],
                tree.branch.get_loom_state().get_threads())
        finally:
            tree.unlock()
        # unlocking should have detected the discrepancy and recorded.
        self.assertEqual(
            [('bottom', bottom_rev1, [])],
            tree.branch.get_loom_state().get_threads())

    def test_trivial_record_loom(self):
        tree = self.get_tree_with_loom()
        # for this test, we want to ensure that we have an empty loom-branch.
        self.assertEqual([], tree.branch.loom_parents())
        # add a thread and record it.
        tree.branch.new_thread('bottom')
        tree.branch.nick = 'bottom'
        rev_id = tree.branch.record_loom('Setup test loom.')
        # after recording, the parents list should have changed.
        self.assertEqual([rev_id], tree.branch.loom_parents())

    def test_revert_loom(self):
        tree = self.get_tree_with_loom()
        # ensure we have some stuff to revert
        # new threads
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        tree.branch.nick = 'bar'
        last_rev = tree.branch.last_revision()
        # and a change to the revision history of this thread
        tree.commit('change bar', allow_pointless=True)
        tree.branch.revert_loom()
        # the threads list should be restored
        self.assertEqual([], tree.branch.get_loom_state().get_threads())
        self.assertEqual(last_rev, tree.branch.last_revision())
        
    def test_revert_loom_changes_current_thread_history(self):
        tree = self.get_tree_with_loom()
        # new threads
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        tree.branch.nick = 'bar'
        # and a change to the revision history of this thread
        tree.commit('change bar', allow_pointless=True)
        # now record
        tree.branch.record_loom('change bar')
        last_rev = tree.branch.last_revision()
        # and a change to the revision history of this thread to revert
        tree.commit('change bar', allow_pointless=True)
        tree.branch.revert_loom()
        # the threads list should be restored
        self.assertEqual(
            [(u'foo', 'empty:', [EMPTY_REVISION]),
             (u'bar', last_rev, [last_rev])],
            tree.branch.get_loom_state().get_threads())
        self.assertEqual(last_rev, tree.branch.last_revision())

    def test_revert_loom_remove_current_thread_mid_loom(self):
        # given the loom Base, => mid, top, with a basis of Base, top, revert
        # of the loom should end up with Base, =>top, including last-revision
        # changes
        tree = self.get_tree_with_loom()
        tree = LoomTreeDecorator(tree)
        # new threads
        tree.branch.new_thread('base')
        tree.branch.new_thread('top')
        tree.branch.nick = 'top'
        # and a change to the revision history of this thread
        tree.tree.commit('change top', allow_pointless=True)
        last_rev = tree.branch.last_revision()
        # now record
        tree.branch.record_loom('change top')
        tree.down_thread()
        tree.branch.new_thread('middle', 'base')
        tree.up_thread()
        self.assertEqual('middle', tree.branch.nick)
        tree.branch.revert_loom()
        # the threads list should be restored
        self.assertEqual(
            [('base', 'empty:', [EMPTY_REVISION]),
             ('top', last_rev, [last_rev])],
            tree.branch.get_loom_state().get_threads())
        self.assertEqual(last_rev, tree.branch.last_revision())

    def test_revert_thread_not_in_basis(self):
        tree = self.get_tree_with_loom()
        # ensure we have some stuff to revert
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        # do a commit, so the last_revision should change.
        tree.branch.nick = 'bar'
        tree.commit('bar-ness', allow_pointless=True)
        tree.branch.revert_thread('bar')
        self.assertEqual(
            [('foo', EMPTY_REVISION, [])],
            tree.branch.get_loom_state().get_threads())
        self.assertEqual(NULL_REVISION, tree.branch.last_revision())

    def test_revert_thread_in_basis(self):
        tree = self.get_tree_with_loom()
        # ensure we have some stuff to revert
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        tree.branch.nick = 'foo'
        # record the loom to put the threads in the basis
        tree.branch.record_loom('record it!')
        # do a commit, so the last_revision should change.
        tree.branch.nick = 'bar'
        tree.commit('bar-ness', allow_pointless=True)
        tree.branch.revert_thread('bar')
        self.assertEqual(
            [('foo', EMPTY_REVISION, [EMPTY_REVISION]),
             ('bar', EMPTY_REVISION, [EMPTY_REVISION]),
            ],
            tree.branch.get_loom_state().get_threads())
        self.assertTrue(NULL_REVISION, tree.branch.last_revision())

    def test_remove_thread(self):
        tree = self.get_tree_with_loom()
        tree.branch.new_thread('bar')
        tree.branch.new_thread('foo')
        tree.branch.nick = 'bar'
        tree.branch.remove_thread('foo')
        state = tree.branch.get_loom_state()
        self.assertEqual([('bar', 'empty:', [])], state.get_threads())

    def test_get_threads_none(self):
        tree = self.get_tree_with_loom()
        # with no commmits in the loom:
        self.assertEqual([], tree.branch.get_threads(None))
        # and loom history should make no difference:
        tree.branch.new_thread('foo')
        tree.branch.nick = 'foo'
        tree.branch.record_loom('foo')
        self.assertEqual([], tree.branch.get_threads(None))
