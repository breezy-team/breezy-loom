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

"""The Loom Tree support routines.

LoomTreeDecorator decorates any tree which has a loomed branch to give it
loom-aware functionality.
"""

__all__ = ['LoomTreeDecorator']


from bzrlib.decorators import needs_write_lock
import bzrlib.errors
import bzrlib.revision


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
            raise BzrCommandError('cannot switch threads with an out of '
                'date tree. Please run bzr update.')
        # set it up:
        current_revision = self.tree.last_revision()
        threadname = self.tree.branch.nick
        threads = self.tree.branch.get_threads()
        old_thread_rev = None
        new_thread_name = None
        new_thread_rev = None
        # TODO: Factor this out into a search routine.
        for thread, rev in reversed(threads):
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
        try:
            base_rev_id = bzrlib.revision.common_ancestor(
                new_thread_rev,
                old_thread_rev,
                self.tree.branch.repository)
        except bzrlib.errors.NoCommonAncestor:
            raise BzrCommandError('corrupt loom: thread %s has no common'
                ' ancestor with thread %s' % (new_thread_name, threadname))
            base_rev_id = None
        # change the branch
        self.tree.branch.generate_revision_history(new_thread_rev)
        # change the tree
        self.tree.set_last_revision(new_thread_rev)
        # record the merge:
        self.tree.add_pending_merge(old_thread_rev)
        # now merge the tree up into the new patch:
        base_tree = self.tree.branch.repository.revision_tree(base_rev_id)
        other_tree = self.tree.branch.repository.revision_tree(new_thread_rev)
        result += bzrlib.merge.merge_inner(self.tree.branch,
            other_tree,
            base_tree,
            this_tree=self.tree)
        bzrlib.trace.note('Moved to thread %s.' % new_thread_name)
        if result != 0:
            return 1
        else:
            return 0

    @needs_write_lock
    def down_thread(self):
        """Move one thread down in the loom."""
        if self.tree.last_revision() != self.tree.branch.last_revision():
            raise BzrCommandError('cannot switch threads with an out of '
                'date tree. Please run bzr update.')
        current_revision = self.tree.last_revision()
        threadname = self.tree.branch.nick
        threads = self.tree.branch.get_threads()
        old_thread_rev = None
        new_thread_name = None
        new_thread_rev = None
        for thread, rev in threads:
            if thread == threadname:
                # found the current thread.
                old_thread_rev = rev
                break
            new_thread_name = thread
            new_thread_rev = rev   
        if new_thread_rev is None:
            raise bzrlib.errors.BzrCommandError(
                'Cannot move down from the lowest thread.')
        self.tree.branch.nick = new_thread_name
        if new_thread_rev == old_thread_rev:
            # done
            return 0
        basis_tree = self.tree.branch.repository.revision_tree(old_thread_rev)
        to_tree = self.tree.branch.repository.revision_tree(new_thread_rev)
        result = bzrlib.merge.merge_inner(self.tree.branch,
            to_tree,
            basis_tree,
            this_tree=self.tree)
        self.tree.branch.generate_revision_history(new_thread_rev)
        self.tree.set_last_revision(new_thread_rev)
        return result
        
    def lock_write(self):
        self.tree.lock_write()

    def unlock(self):
        self.tree.unlock()
