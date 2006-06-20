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

import branch


class cmd_loomify(bzrlib.commands.Command):
    """Add a loom to this branch.

    This creates a loom in your branch, which will alter the behaviour of
    bzr for a number of commands to manage a group of patches being evolved
    in parallel.

    You must have a branch nickname explicitly set to use this command, as the
    branch nickname becomes the 'base branch' of the loom.
    """

    def run(self):
        (target, path) = bzrlib.branch.Branch.open_containing('.')
        target.lock_write()
        try:
            cfg = target.tree_config()
            nick = cfg.get_option("nickname")
            if nick is None:
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

    def run(self):
        (loom, path) = bzrlib.branch.Branch.open_containing('.')
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
    """Move the branch down a thread in the loom."""

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
            tree.set_last_revision(new_thread_rev)
            tree.branch.generate_revision_history(new_thread_rev)
            return result
        finally:
            tree.unlock()
