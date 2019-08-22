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


"""Tests of the loom Branch related routines."""


import breezy
from breezy.branch import Branch
from breezy.commit import PointlessCommit
import breezy.errors as errors
from breezy.plugins.loom.branch import (
    AlreadyLoom,
    EMPTY_REVISION,
    loomify,
    require_loom_branch,
    NotALoom,
    UnsupportedBranchFormat,
    )
from breezy.plugins.loom.tests import TestCaseWithLoom
from breezy.plugins.loom.tree import LoomTreeDecorator
import breezy.revision
from breezy.revision import NULL_REVISION
from breezy.tests import (
    TestCaseWithTransport,
    test_server,
    )
from breezy.transport import get_transport
from breezy.workingtree import WorkingTree


class TestFormat(TestCaseWithTransport):

    def test_disk_format(self):
        bzrdir = self.make_controldir('.')
        bzrdir.create_repository()
        format = breezy.plugins.loom.branch.BzrBranchLoomFormat1()
        branch = format.initialize(bzrdir)
        self.assertFileEqual('Loom current 1\n\n', '.bzr/branch/last-loom')



class StubFormat(object):

    def network_name(self):
        return "Nothing to see."


class FakeLock(object):

    def __init__(self, unlock):
        self.unlock = unlock

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.unlock()
        return False


class LockableStub(object):

    def __init__(self):
        self._calls = []
        self._format = StubFormat()

    def lock_write(self):
        self._calls.append(("write",))
        return FakeLock(self.unlock)

    def unlock(self):
        self._calls.append(("unlock",))


class TestRequireLoomBranch(TestCaseWithTransport):

    def test_on_non_loom(self):
        branch = self.make_branch('.')
        self.assertRaises(NotALoom, require_loom_branch, branch)

    def works_on_format(self, format):
        branch = self.make_branch('.', format)
        loomify(branch)
        # reopen it
        branch = branch.controldir.open_branch()
        self.assertEqual(None, require_loom_branch(branch))

    def test_works_on_loom1(self):
        self.works_on_format('knit')

    def test_works_on_loom6(self):
        self.works_on_format('pack-0.92')

    def test_works_on_loom7(self):
        self.works_on_format('1.6')

    def test_no_harm_to_looms(self):
        branch = self.make_branch('.')
        loomify(branch)
        branch = branch.controldir.open_branch()
        self.assertRaises(AlreadyLoom, loomify, branch)


class TestLoomify(TestCaseWithTransport):

    def assertConvertedBranchFormat(self, branch, branch_class, format):
        """Assert that branch has been successfully converted to a loom."""
        self.assertFalse(branch.is_locked())
        # a loomed branch opens with a different format
        branch = breezy.branch.Branch.open('.')
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
            breezy.plugins.loom.branch.LoomBranch,
            breezy.plugins.loom.branch.BzrBranchLoomFormat1)

    def test_loomify_branch_format_6(self):
        branch = self.make_branch('.', format='dirstate-tags')
        loomify(branch)
        self.assertConvertedBranchFormat(branch,
            breezy.plugins.loom.branch.LoomBranch6,
            breezy.plugins.loom.branch.BzrBranchLoomFormat6)

    def test_loomify_branch_format_7(self):
        branch = self.make_branch('.', format='1.6')
        loomify(branch)
        self.assertConvertedBranchFormat(branch,
            breezy.plugins.loom.branch.LoomBranch7,
            breezy.plugins.loom.branch.BzrBranchLoomFormat7)


class TestLoom(TestCaseWithLoom):

    def make_loom(self, path):
        breezy.plugins.loom.branch.loomify(self.make_branch(path))
        return breezy.branch.Branch.open(path)

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
        self.assertRaises(breezy.plugins.loom.branch.DuplicateThreadName, 
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
        tree.branch._set_nick('middlepoint')
        rev_id2 = tree.commit('middle', allow_pointless=True)
        tree.branch._set_nick('endpoint')
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
        self.assertRaises(PointlessCommit, tree.branch.record_loom, 'foo')

    def test_record_thread(self):
        tree = self.get_tree_with_one_commit()
        tree.branch.new_thread('baseline')
        tree.branch.new_thread('tail')
        tree.branch._set_nick('baseline')
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
        source_tree.branch._set_nick('source')
        target_tree = source_tree.controldir.clone('target').open_workingtree()
        self.assertLoomSproutedOk(source_tree, target_tree)

    def test_sprout_empty_loom(self):
        source_tree = self.get_tree_with_loom('source')
        target_tree = source_tree.controldir.sprout('target').open_workingtree()
        self.assertLoomSproutedOk(source_tree, target_tree)
        
    def test_clone_nonempty_loom_top(self):
        """Cloning a nonempty loom at the top should preserve the loom."""
        source_tree = self.get_tree_with_one_commit('source')
        source_tree.branch.new_thread('bottom')
        source_tree.branch.new_thread('top')
        source_tree.branch._set_nick('top')
        source_tree.commit('phwoar', allow_pointless=True)
        source_tree.branch.record_loom('commit to loom')
        target_tree = source_tree.controldir.clone('target').open_workingtree()
        self.assertLoomSproutedOk(source_tree, target_tree)

    def test_clone_nonempty_loom_bottom(self):
        """Cloning loom should reset the current loom pointer."""
        self.make_and_clone_simple_loom()

    def make_and_clone_simple_loom(self):
        source_tree = self.get_tree_with_one_commit('source')
        source_tree.branch.new_thread('bottom')
        source_tree.branch.new_thread('top')
        source_tree.branch._set_nick('top')
        source_tree.commit('phwoar', allow_pointless=True)
        source_tree.branch.record_loom('commit to loom')
        LoomTreeDecorator(source_tree).down_thread()
        # now clone from the 'default url' - transport_server rather than
        # vfs_server.
        source_branch = Branch.open(self.get_url('source'))
        target_tree = source_branch.controldir.sprout('target').open_workingtree()
        self.assertLoomSproutedOk(source_tree, target_tree)

    def test_sprout_remote_loom(self):
        # RemoteBranch should permit sprouting properly.
        self.transport_server = test_server.SmartTCPServer_for_testing
        self.make_and_clone_simple_loom()

    def test_sprout_nonempty_loom_bottom(self):
        """Sprouting always resets the loom to the top."""
        source_tree = self.get_tree_with_one_commit('source')
        source_tree.branch.new_thread('bottom')
        source_tree.branch.new_thread('top')
        source_tree.branch._set_nick('top')
        source_tree.commit('phwoar', allow_pointless=True)
        source_tree.branch.record_loom('commit to loom')
        LoomTreeDecorator(source_tree).down_thread()
        # now sprout
        target_tree = source_tree.controldir.sprout('target').open_workingtree()
        self.assertLoomSproutedOk(source_tree, target_tree)

    def assertLoomSproutedOk(self, source_tree, target_tree):
        """A sprout resets the loom to the top to ensure up-thread works.
        
        Due to the calls made, this will ensure the loom content has been
        pulled, and that the tree state is correct.
        """
        # the loom pointer has a parent of the source looms tip
        source_tree.lock_write()
        self.addCleanup(source_tree.unlock)
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
            source_tree.branch.last_revision_info(),
            target_tree.branch.last_revision_info())

    def test_pull_loom_at_bottom(self):
        """Pulling from a loom when in the bottom warp pulls all warps."""
        source = self.get_tree_with_loom('source')
        source.branch.new_thread('bottom')
        source.branch.new_thread('top')
        source.branch._set_nick('bottom')
        source.branch.record_loom('commit to loom')
        target = source.controldir.sprout('target').open_branch()
        target._set_nick('top')
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
        self.pull_into_empty_loom()

    def pull_into_empty_loom(self):
        source = self.get_tree_with_loom('source')
        target = source.controldir.sprout('target').open_branch()
        source.branch.new_thread('a thread')
        source.branch._set_nick('a thread')
        # put a commit in the thread for source.
        bottom_rev1 = source.commit('commit a thread')
        source.branch.record_loom('commit to loom')
        # now pull from the 'default url' - transport_server rather than
        # vfs_server - this may be a RemoteBranch.
        source_branch = Branch.open(self.get_url('source'))
        target.pull(source_branch)
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

    def test_pull_remote_loom(self):
        # RemoteBranch should permit sprouting properly.
        self.transport_server = test_server.SmartTCPServer_for_testing
        self.pull_into_empty_loom()

    def test_pull_thread_at_null(self):
        """Doing a pull when the source loom has a thread with no history."""
        source = self.get_tree_with_loom('source')
        target = source.controldir.sprout('target').open_branch()
        source.branch.new_thread('a thread')
        source.branch._set_nick('a thread')
        source.branch.record_loom('commit to loom')
        target.pull(source.branch)
        # check loom threads
        threads = target.get_loom_state().get_threads()
        self.assertEqual(
            [('a thread', b'empty:', [b'empty:'])],
            threads)
        # check loom tip was pulled
        loom_rev_ids = source.branch.loom_parents()
        for rev_id in loom_rev_ids:
            self.assertTrue(target.repository.has_revision(rev_id))
        self.assertEqual(source.branch.loom_parents(), target.loom_parents())

    def test_push_loom_loom(self):
        """Pushing a loom to a loom copies the current loom state."""
        source = self.get_tree_with_loom('source')
        source.branch.new_thread('bottom')
        source.branch.new_thread('top')
        source.branch._set_nick('bottom')
        source.branch.record_loom('commit to loom')
        target = source.controldir.sprout('target').open_branch()
        target._set_nick('top')
        # put a commit in the bottom and top of this loom
        bottom_rev1 = source.commit('commit bottom')
        source_loom_tree = LoomTreeDecorator(source)
        source_loom_tree.up_thread()
        top_rev1 = source.commit('integrate bottom changes.')
        source_loom_tree.down_thread()
        # and now another commit at the bottom
        bottom_rev2 = source.commit('bottom 2', allow_pointless=True)
        source.branch.record_loom('commit to loom again')
        # we now have two commits in the bottom warp, one in the top, and
        # all three should be pulled. We are pushing into a loom which has
        # a different current thread too : that should not affect us.
        source.branch.push(target)
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

    def test_implicit_record(self):
        tree = self.get_tree_with_loom('source')
        tree.branch.new_thread('bottom')
        tree.branch._set_nick('bottom')
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
        tree.branch._set_nick('bottom')
        rev_id = tree.branch.record_loom('Setup test loom.')
        # after recording, the parents list should have changed.
        self.assertEqual([rev_id], tree.branch.loom_parents())

    def test_revert_loom(self):
        tree = self.get_tree_with_loom()
        # ensure we have some stuff to revert
        # new threads
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        tree.branch._set_nick('bar')
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
        tree.branch._set_nick('bar')
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
            [(u'foo', b'empty:', [EMPTY_REVISION]),
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
        tree.branch._set_nick('top')
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
            [('base', b'empty:', [EMPTY_REVISION]),
             ('top', last_rev, [last_rev])],
            tree.branch.get_loom_state().get_threads())
        self.assertEqual(last_rev, tree.branch.last_revision())

    def test_revert_thread_not_in_basis(self):
        tree = self.get_tree_with_loom()
        # ensure we have some stuff to revert
        tree.branch.new_thread('foo')
        tree.branch.new_thread('bar')
        # do a commit, so the last_revision should change.
        tree.branch._set_nick('bar')
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
        tree.branch._set_nick('foo')
        # record the loom to put the threads in the basis
        tree.branch.record_loom('record it!')
        # do a commit, so the last_revision should change.
        tree.branch._set_nick('bar')
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
        tree.branch._set_nick('bar')
        tree.branch.remove_thread('foo')
        state = tree.branch.get_loom_state()
        self.assertEqual([('bar', b'empty:', [])], state.get_threads())

    def test_get_threads_null(self):
        tree = self.get_tree_with_loom()
        # with no commmits in the loom:
        self.assertEqual([], tree.branch.get_threads(NULL_REVISION))
        # and loom history should make no difference:
        tree.branch.new_thread('foo')
        tree.branch._set_nick('foo')
        tree.branch.record_loom('foo')
        self.assertEqual([], tree.branch.get_threads(NULL_REVISION))

    def get_multi_threaded(self):
        tree = self.get_tree_with_loom()
        tree.branch.new_thread('thread1')
        tree.branch._set_nick('thread1')
        tree.commit('thread1', rev_id=b'thread1-id')
        tree.branch.new_thread('thread2', 'thread1')
        tree.branch._set_nick('thread2')
        tree.commit('thread2', rev_id=b'thread2-id')
        return tree

    def test_export_loom_initial(self):
        tree = self.get_multi_threaded()
        root_transport = tree.branch.controldir.root_transport
        tree.branch.export_threads(root_transport)
        thread1 = Branch.open_from_transport(root_transport.clone('thread1'))
        self.assertEqual(b'thread1-id', thread1.last_revision())
        thread2 = Branch.open_from_transport(root_transport.clone('thread2'))
        self.assertEqual(b'thread2-id', thread2.last_revision())

    def test_export_loom_update(self):
        tree = self.get_multi_threaded()
        root_transport = tree.branch.controldir.root_transport
        tree.branch.export_threads(root_transport)
        tree.commit('thread2-2', rev_id=b'thread2-2-id')
        tree.branch.export_threads(root_transport)
        thread1 = Branch.open_from_transport(root_transport.clone('thread1'))
        self.assertEqual(b'thread1-id', thread1.last_revision())
        thread2 = Branch.open_from_transport(root_transport.clone('thread2'))
        self.assertEqual(b'thread2-2-id', thread2.last_revision())

    def test_export_loom_root_transport(self):
        tree = self.get_multi_threaded()
        tree.branch.controldir.root_transport.mkdir('root')
        root_transport = tree.branch.controldir.root_transport.clone('root')
        tree.branch.export_threads(root_transport)
        thread1 = Branch.open_from_transport(root_transport.clone('thread1'))
        thread1 = Branch.open_from_transport(root_transport.clone('thread1'))
        self.assertEqual(b'thread1-id', thread1.last_revision())
        thread2 = Branch.open_from_transport(root_transport.clone('thread2'))
        self.assertEqual(b'thread2-id', thread2.last_revision())

    def test_export_loom_as_tree(self):
        tree = self.get_multi_threaded()
        tree.branch.controldir.root_transport.mkdir('root')
        root_transport = tree.branch.controldir.root_transport.clone('root')
        tree.branch.export_threads(root_transport)
        export_tree = WorkingTree.open(root_transport.local_abspath('thread1'))
        self.assertEqual(b'thread1-id', export_tree.last_revision())

    def test_export_loom_as_branch(self):
        tree = self.get_multi_threaded()
        tree.branch.controldir.root_transport.mkdir('root')
        root_path = tree.branch.controldir.root_transport.local_abspath('root')
        repo = self.make_repository('root', shared=True)
        repo.set_make_working_trees(False)
        root_transport = get_transport('root')
        tree.branch.export_threads(root_transport)
        self.assertRaises(errors.NoWorkingTree, WorkingTree.open,
                          root_transport.local_abspath('thread1'))
        export_branch = Branch.open_from_transport(
            root_transport.clone('thread1'))
        self.assertEqual(b'thread1-id', export_branch.last_revision())

    def test_set_nick_renames_thread(self):
        tree = self.get_tree_with_loom()
        tree.branch.new_thread(tree.branch.nick)
        orig_threads = tree.branch.get_loom_state().get_threads()
        new_thread_name = 'new thread name'
        tree.branch.nick = new_thread_name
        new_threads = tree.branch.get_loom_state().get_threads()
        self.assertNotEqual(orig_threads, new_threads)
        self.assertEqual(new_thread_name, new_threads[0][0])
        self.assertEqual(new_thread_name, tree.branch.nick)
