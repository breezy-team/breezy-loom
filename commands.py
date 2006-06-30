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

"""Loom commands."""

import bzrlib.commands
import bzrlib.branch
import bzrlib.errors
import bzrlib.merge
import bzrlib.revision
import bzrlib.trace

import branch


class cmd_loomify(bzrlib.commands.Command):
    """Add a loom to this branch.

    This creates a loom in your branch, which will alter the behaviour of
    bzr for a number of commands to manage a group of patches being evolved
    in parallel.

    You must have a branch nickname explicitly set to use this command, as the
    branch nickname becomes the 'base branch' of the loom.
    """

    takes_args = ['location?']

    def run(self, location='.'):
        (target, path) = bzrlib.branch.Branch.open_containing(location)
        target.lock_write()
        try:
            if not target.has_explicit_nick():
                raise bzrlib.errors.BzrCommandError(
                    'You must have a branch nickname set to loomify a branch')
            branch.BzrBranchLoomFormat1().take_over(target)
            loom = target.bzrdir.open_branch()
        finally:
            target.unlock()
        # requires a new lock as its a new instance, XXX: teach bzrdir about
        # format changes ?
        loom.new_thread(loom.nick)

        
class cmd_create_thread(bzrlib.commands.Command):
    """Add a thread to this loom.

    This creates a new thread in this loom and moves the branch onto that
    thread.

    The thread-name must be a valid branch 'nickname', and must not be the name
    of an existing thread in your loom.
    """

    takes_args = ['thread']

    def run(self, thread):
        (loom, path) = bzrlib.branch.Branch.open_containing('.')
        loom.lock_write()
        try:
            loom.new_thread(thread, loom.nick)
            loom.nick = thread
        finally:
            loom.unlock()

            
class cmd_show_loom(bzrlib.commands.Command):
    """Show the threads in this loom.

    Output the threads in this loom with the newest thread at the top and
    the base thread at the bottom. A => marker indicates the thread that
    'commit' will commit to.
    """

    takes_args = ['location?']

    def run(self, location='.'):
        (loom, path) = bzrlib.branch.Branch.open_containing(location)
        loom.lock_read()
        try:
            threads = loom.get_threads()
            nick = loom.nick
            for thread, revid in reversed(threads):
                if thread == nick:
                    symbol = '=>'
                else:
                    symbol = '  '
                print "%s%s" % (symbol, thread)
        finally:
            loom.unlock()


class cmd_record(bzrlib.commands.Command):
    """Record the current last-revision of this tree into the current thread."""

    def run(self):
        (tree, path) = bzrlib.workingtree.WorkingTree.open_containing('.')
        tree.lock_write()
        try:
            thread = tree.branch.nick
            tree.branch.record_thread(thread, tree.last_revision())
        finally:
            tree.unlock()


class cmd_down_thread(bzrlib.commands.Command):
    """Move the branch down a thread in the loom.
    
    This removes the changes introduced by the current thread from the branch
    and sets the branch to be the next thread down.
    """

    def run(self):
        (tree, path) = bzrlib.workingtree.WorkingTree.open_containing('.')
        tree.lock_write()
        try:
            if tree.last_revision() != tree.branch.last_revision():
                raise BzrCommandError('cannot switch threads with an out of '
                    'date tree. Please run bzr update.')
            current_revision = tree.last_revision()
            threadname = tree.branch.nick
            threads = tree.branch.get_threads()
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
            tree.branch.nick = new_thread_name
            if new_thread_rev == old_thread_rev:
                # done
                return 0
            basis_tree = tree.branch.repository.revision_tree(old_thread_rev)
            to_tree = tree.branch.repository.revision_tree(new_thread_rev)
            result = bzrlib.merge.merge_inner(tree.branch,
                to_tree,
                basis_tree,
                this_tree=tree)
            tree.branch.generate_revision_history(new_thread_rev)
            tree.set_last_revision(new_thread_rev)
            return result
        finally:
            tree.unlock()


class cmd_up_thread(bzrlib.commands.Command):
    """Move the branch up a thread in the loom.
    
    This merges the changes done in this thread but not incorporated into
    the next thread up into the next thread up and switches your tree to be
    that thread.
    """

    def run(self):
        (tree, path) = bzrlib.workingtree.WorkingTree.open_containing('.')
        tree.lock_write()
        try:
            if tree.last_revision() != tree.branch.last_revision():
                raise BzrCommandError('cannot switch threads with an out of '
                    'date tree. Please run bzr update.')
            # set it up:
            current_revision = tree.last_revision()
            threadname = tree.branch.nick
            threads = tree.branch.get_threads()
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
            tree.branch.nick = new_thread_name
            # special case no-change condition.
            if new_thread_rev == old_thread_rev:
                # done
                return 0
            result = 0
            try:
                base_rev_id = bzrlib.revision.common_ancestor(
                    new_thread_rev,
                    old_thread_rev,
                    tree.branch.repository)
            except errors.NoCommonAncestor:
                raise BzrCommandError('corrupt loom: thread %s has no common'
                    ' ancestor with thread %s' % (new_thread_name, threadname))
                base_rev_id = None
            # change the branch
            tree.branch.generate_revision_history(new_thread_rev)
            # change the tree
            tree.set_last_revision(new_thread_rev)
            # record the merge:
            tree.add_pending_merge(old_thread_rev)
            # now merge the tree up into the new patch:
            base_tree = tree.branch.repository.revision_tree(base_rev_id)
            other_tree = tree.branch.repository.revision_tree(new_thread_rev)
            result += bzrlib.merge.merge_inner(tree.branch,
                other_tree,
                base_tree,
                this_tree=tree)
            bzrlib.trace.note('Moved to thread %s.' % new_thread_name)
            if result != 0:
                return 1
            else:
                return 0
        finally:
            tree.unlock()
