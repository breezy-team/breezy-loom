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

"""The Loom Tree support routines.

LoomTreeDecorator decorates any tree which has a loomed branch to give it
loom-aware functionality.
"""

__all__ = ['LoomTreeDecorator']


from bzrlib.decorators import needs_write_lock
import bzrlib.errors
import bzrlib.revision

from branch import EMPTY_REVISION


class LoomTreeDecorator(object):
    """Adapt any tree with a loomed branch to give it loom-aware methods.

    Currently this does not implemeny the Tree protocol itself. The decorated
    tree is available for use via the decorator.

    Useful attributes:
    tree: The decorated tree.
    branch: The branch of the decorated tree.
    """

    def __init__(self, a_tree):
        """Decorate a_tree with loom aware methods."""
        self.tree = a_tree
        self.branch = self.tree.branch

    @needs_write_lock
    def up_thread(self):
        """Move one thread up in the loom."""
        if self.tree.last_revision() != self.tree.branch.last_revision():
            raise bzrlib.errors.BzrCommandError('cannot switch threads with an'
            'out of date tree. Please run bzr update.')
        # set it up:
        current_revision = self.tree.last_revision()
        threadname = self.tree.branch.nick
        threads = self.tree.branch.get_loom_state().get_threads()
        old_thread_rev = None
        new_thread_name = None
        new_thread_rev = None
        # TODO: Factor this out into a search routine.
        for thread, rev, parents in reversed(threads):
            if thread == threadname:
                # found the current thread.
                old_thread_rev = rev
                break
            new_thread_name = thread
            new_thread_rev = rev
        if new_thread_rev is None:
            raise bzrlib.errors.BzrCommandError(
                'Cannot move up from the highest thread.')
        # update the branch nick.
        self.tree.branch.nick = new_thread_name
        # special case no-change condition.
        if new_thread_rev == old_thread_rev:
            # done
            return 0
        result = 0
        if new_thread_rev == EMPTY_REVISION:
            new_thread_rev = bzrlib.revision.NULL_REVISION
        if old_thread_rev == EMPTY_REVISION:
            old_thread_rev = bzrlib.revision.NULL_REVISION
        graph = self.tree.branch.repository.get_graph()
        base_rev_id = graph.find_unique_lca(new_thread_rev,
            old_thread_rev)
        if (base_rev_id == bzrlib.revision.NULL_REVISION and
            new_thread_rev != bzrlib.revision.NULL_REVISION):
            raise bzrlib.errors.BzrCommandError('corrupt loom: thread %s has'
                ' no common ancestor with thread %s'
                % (new_thread_name, threadname))
            base_rev_id = None
        # change the branch
        self.tree.branch.generate_revision_history(new_thread_rev)
        # change the tree to the revision of the new thread.
        self.tree.set_last_revision(new_thread_rev)
        # record the merge if:
        # the old thread is not NULL (we have something to record)
        # and the new thread is either empty/null OR the old thread is
        #    not merged into it.
        if (old_thread_rev not in 
                (EMPTY_REVISION, bzrlib.revision.NULL_REVISION)
            and (new_thread_rev in 
                    (EMPTY_REVISION, bzrlib.revision.NULL_REVISION)
                or old_thread_rev not in
                    self.tree.branch.repository.get_ancestry(new_thread_rev))):
            self.tree.add_pending_merge(old_thread_rev)
        # now merge the tree up into the new patch:
        base_tree = self.tree.branch.repository.revision_tree(base_rev_id)
        other_tree = self.tree.branch.repository.revision_tree(new_thread_rev)
        result += bzrlib.merge.merge_inner(self.tree.branch,
            other_tree,
            base_tree,
            this_tree=self.tree)
        bzrlib.trace.note("Moved to thread '%s'." % new_thread_name)
        if result != 0:
            return 1
        else:
            return 0

    @needs_write_lock
    def down_thread(self, name=None):
        """Move to a thread down in the loom.
        
        :param name: If None, use the next lower thread; otherwise the nae of
            the thread to move to.
        """
        if self.tree.last_revision() != self.tree.branch.last_revision():
            raise bzrlib.errors.BzrCommandError('cannot switch threads with an'
                ' out of date tree. Please run bzr update.')
        current_revision = self.tree.last_revision()
        threadname = self.tree.branch.nick
        threads = self.tree.branch.get_loom_state().get_threads()
        old_thread_index = self.tree.branch._thread_index(threads, threadname)
        old_thread_rev = threads[old_thread_index][1]
        if name is None:
            if old_thread_index == 0:
                raise bzrlib.errors.BzrCommandError(
                    'Cannot move down from the lowest thread.')
            new_thread_name, new_thread_rev, _ = threads[old_thread_index - 1]
        else:
            new_thread_name = name
            index = self.tree.branch._thread_index(threads, name)
            new_thread_rev = threads[index][1]
        assert new_thread_rev is not None
        self.tree.branch.nick = new_thread_name
        if new_thread_rev == old_thread_rev:
            # fast path no-op changes
            bzrlib.trace.note("Moved to thread '%s'." % new_thread_name)
            return 0
        if new_thread_rev == EMPTY_REVISION:
            new_thread_rev = bzrlib.revision.NULL_REVISION
        if old_thread_rev == EMPTY_REVISION:
            old_thread_rev = bzrlib.revision.NULL_REVISION
        basis_tree = self.tree.branch.repository.revision_tree(old_thread_rev)
        to_tree = self.tree.branch.repository.revision_tree(new_thread_rev)
        result = bzrlib.merge.merge_inner(self.tree.branch,
            to_tree,
            basis_tree,
            this_tree=self.tree)
        self.tree.branch.generate_revision_history(new_thread_rev)
        self.tree.set_last_revision(new_thread_rev)
        bzrlib.trace.note("Moved to thread '%s'." % new_thread_name)
        return result
        
    def lock_write(self):
        self.tree.lock_write()

    @needs_write_lock
    def revert_loom(self, thread=None):
        """Revert the loom. This function takes care of tree state for revert.

        If the current loom is not altered, the tree is not altered. If it is
        then the tree will be altered as 'most' appropriate.

        :param thread: Only revert a single thread.
        """
        if self.tree.last_revision() != self.tree.branch.last_revision():
            raise bzrlib.errors.BzrCommandError('cannot switch threads with an'
                ' out of date tree. Please run bzr update.')
        current_thread = self.branch.nick
        last_rev = self.tree.last_revision()
        state = self.branch.get_loom_state()
        old_threads = state.get_threads()
        current_thread_rev = self.branch.last_revision()
        if thread is None:
            self.branch.revert_loom()
        else:
            self.branch.revert_thread(thread)
        state = self.branch.get_loom_state()
        threads = state.get_threads()
        threads_dict = state.get_threads_dict()
        # TODO find the next up thread if needed
        if not threads_dict:
            # last thread nuked
            to_rev = bzrlib.revision.NULL_REVISION
        elif current_thread != self.branch.nick:
            # thread change occured
            to_rev = threads_dict[self.branch.nick][0]
        else:
            # same thread tweaked
            if last_rev == threads_dict[current_thread][0]:
                return
            to_rev = threads_dict[current_thread]
        if current_thread_rev == EMPTY_REVISION:
            current_thread_rev = bzrlib.revision.NULL_REVISION
        if to_rev == EMPTY_REVISION:
            to_rev = bzrlib.revision.NULL_REVISION
        # the thread changed, do a merge to match.
        basis_tree = self.tree.branch.repository.revision_tree(current_thread_rev)
        to_tree = self.tree.branch.repository.revision_tree(to_rev)
        result = bzrlib.merge.merge_inner(self.tree.branch,
            to_tree,
            basis_tree,
            this_tree=self.tree)
        self.tree.set_last_revision(to_rev)

    def unlock(self):
        self.tree.unlock()
