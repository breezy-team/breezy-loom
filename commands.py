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

"""Loom commands."""

from bzrlib import workingtree
import bzrlib.commands
import bzrlib.branch
import bzrlib.errors
import bzrlib.merge
from bzrlib.option import Option
import bzrlib.revision
import bzrlib.trace

import branch
from tree import LoomTreeDecorator


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
            if not target.get_config().has_explicit_nickname():
                raise bzrlib.errors.BzrCommandError(
                    'You must have a branch nickname set to loomify a branch')
            branch.loomify(target)
            loom = target.bzrdir.open_branch()
        finally:
            target.unlock()
        # requires a new lock as its a new instance, XXX: teach bzrdir about
        # format changes ?
        loom.new_thread(loom.nick)


class cmd_combine_thread(bzrlib.commands.Command):
    """Combine the current thread with the thread below it.
    
    This will currently refuse to operate on the last thread, but in the future
    will just turn the loom into a normal branch again.
    
    Use combine-thread to remove a thread which has been merged into upstream.

    In precise terms this will:
     * Remove the entry from the loom for the current thread.
     * Change threads to the thread below.
    """

    def run(self):
        (tree, path) = workingtree.WorkingTree.open_containing('.')
        tree.lock_write()
        try:
            current_thread = tree.branch.nick
            state = tree.branch.get_loom_state()
            threads = state.get_threads()
            if len(threads) < 2 or threads[0][0] == current_thread:
                raise branch.CannotCombineOnLastThread
            current_index = tree.branch._thread_index(threads, current_thread)
            new_thread = threads[current_index - 1][0]
            bzrlib.trace.note("Combining thread '%s' into '%s'",
                current_thread, new_thread)
            LoomTreeDecorator(tree).down_thread()
            tree.branch.remove_thread(current_thread)
        finally:
            tree.unlock()


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
            threads = loom.get_loom_state().get_threads()
            nick = loom.nick
            for thread, revid, parents in reversed(threads):
                if thread == nick:
                    symbol = '=>'
                else:
                    symbol = '  '
                print "%s%s" % (symbol, thread)
        finally:
            loom.unlock()


class cmd_record(bzrlib.commands.Command):
    """Record the current last-revision of this tree into the current thread."""

    takes_args = ['message']

    def run(self, message):
        (abranch, path) = bzrlib.branch.Branch.open_containing('.')
        abranch.record_loom(message)
        print "Loom recorded."


class cmd_revert_loom(bzrlib.commands.Command):
    """Revert part of all of a loom.
    
    This will update the current loom to be the same as the basis when --all
    is supplied. If no parameters or options are supplied then nothing will
    happen. If a thread is named, then only that thread is reverted to its
    state in the last committed loom.
    """

    takes_args = ['thread?']
    takes_options = [Option('all', 
                        help='Revert all threads.'),
                     ]

    def run(self, thread=None, all=None):
        if thread is None and all is None:
            bzrlib.trace.note('Please see revert-loom -h.')
            return
        (tree, path) = workingtree.WorkingTree.open_containing('.')
        tree = LoomTreeDecorator(tree)
        if all:
            tree.revert_loom()
            bzrlib.trace.note('All threads reverted.')
        else:
            tree.revert_loom(thread)
            bzrlib.trace.note("thread '%s' reverted.", thread)


class cmd_down_thread(bzrlib.commands.Command):
    """Move the branch down a thread in the loom.
    
    This removes the changes introduced by the current thread from the branch
    and sets the branch to be the next thread down.
    """

    takes_args = ['thread?']

    def run(self, thread=None):
        (tree, path) = workingtree.WorkingTree.open_containing('.')
        tree = LoomTreeDecorator(tree)
        return tree.down_thread(thread)


class cmd_up_thread(bzrlib.commands.Command):
    """Move the branch up a thread in the loom.
    
    This merges the changes done in this thread but not incorporated into
    the next thread up into the next thread up and switches your tree to be
    that thread.
    """

    def run(self):
        (tree, path) = workingtree.WorkingTree.open_containing('.')
        tree = LoomTreeDecorator(tree)
        return tree.up_thread()
