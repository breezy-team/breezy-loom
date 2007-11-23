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


"""UI tests for loom."""

import os

import bzrlib
from bzrlib.plugins.loom.branch import EMPTY_REVISION
from bzrlib.plugins.loom.tree import LoomTreeDecorator
from bzrlib.plugins.loom.tests import TestCaseWithLoom
from bzrlib.revision import NULL_REVISION


class TestsWithLooms(TestCaseWithLoom):
    """A base class with useful helpers for loom blackbox tests."""

    def get_vendor_loom(self, path='.'):
        """Make a loom with a vendor thread.
        
        This returns a loom with a vendor thread, which has the current 
        commit recorded in it, but nothing in the basis loom - its
        empty.
        """
        tree = self.make_branch_and_tree(path)
        tree.branch.nick = 'vendor'
        tree.commit('first release')
        self.run_bzr(['loomify', path])
        return tree.bzrdir.open_workingtree()
    

class TestLoomify(TestCaseWithLoom):

    def test_loomify_new_branch(self):
        b = self.make_branch('.')
        out, err = self.run_bzr(['loomify'], retcode=3)
        self.assertEqual('', out)
        self.assertEqual(
            'bzr: ERROR: You must have a branch nickname set to loomify a branch\n', 
            err)
        
    def test_loomify_new_branch_with_nick(self):
        b = self.make_branch('.')
        b.nick = 'base'
        out, err = self.run_bzr(['loomify'])
        # a loomed branch opens with a unique format
        b = bzrlib.branch.Branch.open('.')
        self.assertIsInstance(b, bzrlib.plugins.loom.branch.LoomSupport)
        threads = b.get_loom_state().get_threads()
        self.assertEqual(
            [('base', EMPTY_REVISION, [])],
            threads)

    def test_loomify_path(self):
        b = self.make_branch('foo')
        b.nick = 'base'
        out, err = self.run_bzr(['loomify', 'foo'])
        # a loomed branch opens with a unique format
        b = bzrlib.branch.Branch.open('foo')
        self.assertIsInstance(b, bzrlib.plugins.loom.branch.LoomSupport)
        threads = b.get_loom_state().get_threads()
        self.assertEqual(
            [('base', EMPTY_REVISION, [])],
            threads)


class TestCreate(TestsWithLooms):
    
    def test_create_no_changes(self):
        tree = self.get_vendor_loom()
        out, err = self.run_bzr(['create-thread', 'debian'])
        self.assertEqual('', out)
        self.assertEqual('', err)
        revid = tree.last_revision()
        self.assertEqual(
            [('vendor', revid, []),
             ('debian', revid, [])],
            tree.branch.get_loom_state().get_threads())
        self.assertEqual('debian', tree.branch.nick)

    def test_create_not_end(self):
        tree = self.get_vendor_loom()
        tree.branch.new_thread('debian')
        # now we are at vendor, with debian after, so if we add
        # feature-foo we should get:
        # vendor - feature-foo - debian
        out, err = self.run_bzr(['create-thread', 'feature-foo'])
        self.assertEqual('', out)
        self.assertEqual('', err)
        revid = tree.last_revision()
        self.assertEqual(
            [('vendor', revid, []),
             ('feature-foo', revid, []),
             ('debian', revid, [])],
            tree.branch.get_loom_state().get_threads())
        self.assertEqual('feature-foo', tree.branch.nick)


class TestShow(TestsWithLooms):
    
    def test_show_loom(self):
        """Show the threads in the loom."""
        tree = self.get_vendor_loom()
        self.assertShowLoom(['vendor'], 'vendor')
        tree.branch.new_thread('debian')
        self.assertShowLoom(['vendor', 'debian'], 'vendor')
        tree.branch.nick = 'debian'
        self.assertShowLoom(['vendor', 'debian'], 'debian')
        tree.branch.new_thread('patch A', 'vendor')
        self.assertShowLoom(['vendor', 'patch A', 'debian'], 'debian')
        tree.branch.nick = 'patch A'
        self.assertShowLoom(['vendor', 'patch A', 'debian'], 'patch A')

    def test_show_loom_with_location(self):
        """Should be able to provide an explicit location to show."""
        tree = self.get_vendor_loom('subtree')
        self.assertShowLoom(['vendor'], 'vendor', 'subtree')

    def assertShowLoom(self, threads, selected_thread, location=None):
        """Check expected show-loom output."""
        if location:
            out, err = self.run_bzr(['show-loom', location])
        else:
            out, err = self.run_bzr(['show-loom'])
        # threads are in oldest-last order.
        expected_out = ''
        for thread in reversed(threads):
            if thread == selected_thread:
                expected_out += '=>'
            else:
                expected_out += '  '
            expected_out += thread
            expected_out += '\n'
        self.assertEqual(expected_out, out)
        self.assertEqual('', err)


class TestRecord(TestsWithLooms):

    def test_record_no_change(self):
        """If there are no changes record should error."""
        tree = self.get_tree_with_loom()
        out, err = self.run_bzr(['record', 'Try to commit.'], retcode=3)
        self.assertEqual('', out)
        self.assertEqual(
            'bzr: ERROR: No changes to commit\n', err)

    def test_record_new_thread(self):
        """Adding a new thread is enough to allow recording."""
        tree = self.get_vendor_loom()
        tree.branch.new_thread('feature')
        tree.branch.nick = 'feature'
        out, err = self.run_bzr(['record', 'add feature branch.'])
        self.assertEqual('Loom recorded.\n', out)
        self.assertEqual('', err)


class TestDown(TestsWithLooms):

    def test_down_thread_from_bottom(self):
        tree = self.get_vendor_loom()
        out, err = self.run_bzr(['down-thread'], retcode=3)
        self.assertEqual('', out)
        self.assertEqual('bzr: ERROR: Cannot move down from the lowest thread.\n', err)
        
    def test_down_thread_same_revision(self):
        """moving down when the revision is unchanged should work."""
        tree = self.get_vendor_loom()
        tree.branch.new_thread('patch')
        tree.branch.nick = 'patch'
        rev = tree.last_revision()
        out, err = self.run_bzr(['down-thread'])
        self.assertEqual('', out)
        self.assertEqual("Moved to thread 'vendor'.\n", err)
        self.assertEqual('vendor', tree.branch.nick)
        self.assertEqual(rev, tree.last_revision())
        
    def test_down_thread_removes_changes(self):
        tree = self.get_vendor_loom()
        tree.branch.new_thread('patch')
        tree.branch.nick = 'patch'
        rev = tree.last_revision()
        self.build_tree(['afile'])
        tree.add('afile')
        tree.commit('add a file')
        out, err = self.run_bzr(['down-thread'])
        self.assertEqual('', out)
        self.assertEqual(
            "All changes applied successfully.\n"
            "Moved to thread 'vendor'.\n",
            err)
        self.assertEqual('vendor', tree.branch.nick)
        # the tree needs to be updated.
        self.assertEqual(rev, tree.last_revision())
        # the branch needs to be updated.
        self.assertEqual(rev, tree.branch.last_revision())
        self.assertFalse(tree.has_filename('afile'))

    def test_down_thread_switches_history_ok(self):
        """Do a down thread when the lower patch is not in the r-h of the old."""
        tree = self.get_vendor_loom()
        tree.branch.new_thread('patch')
        tree.branch.nick = 'vendor'
        # do a null change in vendor - a new release.
        vendor_release = tree.commit('new vendor release.', allow_pointless=True)
        # pop up, then down
        self.run_bzr(['up-thread'])
        self.run_bzr(['revert'])
        out, err = self.run_bzr(['down-thread'])
        self.assertEqual('', out)
        self.assertEqual(
            'All changes applied successfully.\n'
            "Moved to thread 'vendor'.\n",
            err)
        self.assertEqual('vendor', tree.branch.nick)
        # the tree needs to be updated.
        self.assertEqual(vendor_release, tree.last_revision())
        # the branch needs to be updated.
        self.assertEqual(vendor_release, tree.branch.last_revision())
        # diff should return 0 - no uncomitted changes.
        self.run_bzr(['diff'])
        self.assertEqual([vendor_release], tree.get_parent_ids())


class TestUp(TestsWithLooms):

    def test_up_thread_from_top(self):
        tree = self.get_vendor_loom()
        out, err = self.run_bzr(['up-thread'], retcode=3)
        self.assertEqual('', out)
        self.assertEqual(
            'bzr: ERROR: Cannot move up from the highest thread.\n', err)
        
    def test_up_thread_same_revision(self):
        """moving up when the revision is unchanged should work."""
        tree = self.get_vendor_loom()
        tree.branch.new_thread('patch')
        tree.branch.nick = 'vendor'
        rev = tree.last_revision()
        out, err = self.run_bzr(['up-thread'])
        self.assertEqual('', out)
        self.assertEqual('', err)
        self.assertEqual('patch', tree.branch.nick)
        self.assertEqual(rev, tree.last_revision())
        
    def test_up_thread_preserves_changes(self):
        tree = self.get_vendor_loom()
        tree.branch.new_thread('patch')
        tree.branch.nick = 'vendor'
        patch_rev = tree.last_revision()
        # add a change in vendor - a new release.
        self.build_tree(['afile'])
        tree.add('afile')
        vendor_release = tree.commit('new vendor release adds a file.')
        out, err = self.run_bzr(['up-thread'])
        self.assertEqual('', out)
        self.assertEqual(
            "All changes applied successfully.\n"
            "Moved to thread 'patch'.\n", err)
        self.assertEqual('patch', tree.branch.nick)
        # the tree needs to be updated.
        self.assertEqual(patch_rev, tree.last_revision())
        # the branch needs to be updated.
        self.assertEqual(patch_rev, tree.branch.last_revision())
        self.assertTrue(tree.has_filename('afile'))
        # diff should return 1 now as we have uncommitted changes.
        self.run_bzr(['diff'], retcode=1)
        self.assertEqual([patch_rev, vendor_release], tree.get_parent_ids())

    def test_up_thread_gets_conflicts(self):
        """Do a change in both the baseline and the next patch up."""
        tree = self.get_vendor_loom()
        tree.branch.new_thread('patch')
        tree.branch.nick = 'patch'
        # add a change in patch - a new release.
        self.build_tree(['afile'])
        tree.add('afile')
        patch_rev = tree.commit('add afile as a patch')
        # add a change in vendor - a new release.
        self.run_bzr(['down-thread'])
        self.build_tree(['afile'])
        tree.add('afile')
        vendor_release = tree.commit('new vendor release adds a file.')
        # we want conflicts.
        out, err = self.run_bzr(['up-thread'], retcode=1)
        self.assertEqual('', out)
        self.assertEqual(
            'Conflict adding file afile.  Moved existing file to afile.moved.\n'
            '1 conflicts encountered.\n'
            "Moved to thread 'patch'.\n", err)
        self.assertEqual('patch', tree.branch.nick)
        # the tree needs to be updated.
        self.assertEqual(patch_rev, tree.last_revision())
        # the branch needs to be updated.
        self.assertEqual(patch_rev, tree.branch.last_revision())
        self.assertTrue(tree.has_filename('afile'))
        # diff should return 1 now as we have uncommitted changes.
        self.run_bzr(['diff'], retcode=1)
        self.assertEqual([patch_rev, vendor_release], tree.get_parent_ids())


class TestPush(TestsWithLooms):

    def test_push(self):
        """Integration smoke test for bzr push of a loom."""
        tree = self.get_vendor_loom('source')
        tree.branch.record_loom('commit loom.')
        os.chdir('source')
        out, err = self.run_bzr(['push', '../target'])
        os.chdir('..')
        self.assertEqual('', out)
        self.assertEqual('Created new branch.\n', err)
        # lower level tests check behaviours, just check show-loom as a smoke
        # test.
        out, err = self.run_bzr(['show-loom', 'target'])
        self.assertEqual('=>vendor\n', out)
        self.assertEqual('', err)


class TestBranch(TestsWithLooms):

    def test_branch(self):
        """Integration smoke test for bzr branch of a loom."""
        tree = self.get_vendor_loom('source')
        tree.branch.record_loom('commit loom.')
        out, err = self.run_bzr(['branch', 'source', 'target'])
        self.assertEqual('', out)
        self.assertEqual('Branched 1 revision(s).\n', err)
        # lower level tests check behaviours, just check show-loom as a smoke
        # test.
        out, err = self.run_bzr(['show-loom', 'target'])
        self.assertEqual('=>vendor\n', out)
        self.assertEqual('', err)


class TestPull(TestsWithLooms):

    def test_pull(self):
        """Integration smoke test for bzr pull loom to loom."""
        tree = self.get_vendor_loom('source')
        tree.branch.record_loom('commit loom.')
        tree.bzrdir.sprout('target')
        tree.commit('change the source', allow_pointless=True)
        tree.branch.new_thread('foo')
        LoomTreeDecorator(tree).up_thread()
        tree.branch.record_loom('commit loom again.')
        os.chdir('target')
        try:
            out, err = self.run_bzr(['pull'])
        finally:
            os.chdir('..')
        self.assertStartsWith(out, 'Using saved location:')
        self.assertEndsWith(out, 'Now on revision 2.\n')
        self.assertEqual(
            'All changes applied successfully.\n',
            err)
        # lower level tests check behaviours, just check show-loom as a smoke
        # test.
        out, err = self.run_bzr(['show-loom', 'target'])
        self.assertEqual('=>foo\n  vendor\n', out)
        self.assertEqual('', err)


class TestRevert(TestsWithLooms):

    def test_revert_loom(self):
        """bzr revert-loom should give help."""
        tree = self.get_vendor_loom()
        out, err = self.run_bzr(['revert-loom'])
        self.assertEqual('', out)
        self.assertEqual('Please see revert-loom -h.\n', err)

    def test_revert_loom_missing_thread(self):
        """bzr revert-loom missing-thread should give an error."""
        tree = self.get_vendor_loom()
        out, err = self.run_bzr(['revert-loom', 'unknown-thread'], retcode=3)
        self.assertEqual('', out)
        self.assertEqual("bzr: ERROR: No such thread 'unknown-thread'.\n", err)

    def test_revert_loom_all(self):
        """bzr revert-loom --all should restore the state of a loom."""
        tree = self.get_vendor_loom()
        tree.branch.new_thread('foo')
        last_rev = tree.last_revision()
        self.assertNotEqual(NULL_REVISION, last_rev)
        out, err = self.run_bzr(['revert-loom', '--all'])
        self.assertEqual('', out)
        self.assertEqual(
            'All changes applied successfully.\n'
            'All threads reverted.\n',
            err)
        self.assertNotEqual(last_rev, tree.last_revision())
        self.assertEqual(NULL_REVISION, tree.last_revision())
        self.assertEqual([], tree.branch.get_loom_state().get_threads())
        
    def test_revert_thread(self):
        """bzr revert-loom threadname should restore the state of that thread."""
        # we want a loom with > 1 threads, with a change made to a thread we are
        # not in, so we can revert that by name,
        tree = self.get_vendor_loom()
        tree.branch.new_thread('after-vendor')
        tree.branch.nick = 'after-vendor'
        tree.commit('after-vendor commit', allow_pointless=True)
        tree.branch.record_loom('save loom with vendor and after-vendor')
        old_threads = tree.branch.get_loom_state().get_threads()
        tree.commit('after-vendor commit 2', allow_pointless=True)
        LoomTreeDecorator(tree).down_thread()
        last_rev = tree.last_revision()
        self.assertNotEqual(NULL_REVISION, last_rev)
        out, err = self.run_bzr(['revert-loom', 'after-vendor'])
        self.assertEqual('', out)
        self.assertEqual("thread 'after-vendor' reverted.\n", err)
        self.assertEqual(last_rev, tree.last_revision())
        self.assertEqual(old_threads, tree.branch.get_loom_state().get_threads())


class TestCombineThread(TestsWithLooms):
    """Tests for combine-thread."""

    def test_combine_last_thread(self):
        """Doing combine thread on the last thread is an error for now."""
        tree = self.get_vendor_loom()
        out, err = self.run_bzr(['combine-thread'], retcode=3)
        self.assertEqual('', out)
        self.assertEqual('bzr: ERROR: Cannot combine threads on the bottom thread.\n', err)

    def test_combine_last_two_threads(self):
        """Doing a combine on two threads gives you just the bottom one."""
        tree = self.get_vendor_loom()
        tree.branch.new_thread('above-vendor')
        LoomTreeDecorator(tree).up_thread()
        self.build_tree(['file-a'])
        tree.add('file-a')
        top_revid = tree.commit('change the tree')
        # now we have a change between the threads, so merge this into the lower
        # thread to simulate real-world - different rev ids, and the lower
        # thread has merged the upper.
        LoomTreeDecorator(tree).down_thread()
        # ugh, should make merge easier to use.
        self.run_bzr(['merge', '-r', 'revid:%s' % top_revid, '.'])
        vendor_revid = tree.commit('merge in the above-vendor work.')
        LoomTreeDecorator(tree).up_thread()
        out, err = self.run_bzr(['combine-thread'])
        self.assertEqual('', out)
        self.assertEqual(
            "Combining thread 'above-vendor' into 'vendor'\n"
            'All changes applied successfully.\n'
            "Moved to thread 'vendor'.\n",
            err)
        self.assertEqual(vendor_revid, tree.last_revision())
        self.assertEqual('vendor', tree.branch.nick)
