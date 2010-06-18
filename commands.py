# Loom, a plugin for bzr to assist in developing focused patches.
# Copyright (C) 2006, 2008 Canonical Limited.
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

from bzrlib import bzrdir, directory_service, workingtree
import bzrlib.commands
import bzrlib.branch
from bzrlib import errors
from bzrlib.lazy_import import lazy_import
import bzrlib.merge
from bzrlib.option import Option
import bzrlib.revision
import bzrlib.trace
import bzrlib.transport

import formats

lazy_import(globals(), """
import branch
from tree import LoomTreeDecorator
""")


class cmd_loomify(bzrlib.commands.Command):
    """Add a loom to this branch.

    This creates a loom in your branch, which will alter the behaviour of
    bzr for a number of commands to manage a group of patches being evolved
    in parallel.

    You must have a branch nickname explicitly set to use this command, as the
    branch nickname becomes the 'base thread' of the loom.  You can specify
    the branch nick with the --base option.
    """

    takes_args = ['location?']
    takes_options = [Option('base', type=str,
                            help='The name to use for the base thread.')]

    def run(self, location='.', base=None):
        (target, path) = bzrlib.branch.Branch.open_containing(location)
        target.lock_write()
        try:
            if base is not None:
                target.nick = base
            elif not target.get_config().has_explicit_nickname():
                raise errors.BzrCommandError(
                    'You must specify --base or have a branch nickname set to'
                    ' loomify a branch')
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
        branch.require_loom_branch(tree.branch)
        tree.lock_write()
        try:
            current_thread = tree.branch.nick
            state = tree.branch.get_loom_state()
            threads = state.get_threads()
            new_thread = state.get_new_thread_after_deleting(current_thread)
            if new_thread is None:
                raise branch.CannotCombineOnLastThread
            bzrlib.trace.note("Combining thread '%s' into '%s'",
                current_thread, new_thread)
            LoomTreeDecorator(tree).down_thread(new_thread)
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
        branch.create_thread(loom, thread)


class cmd_show_loom(bzrlib.commands.Command):
    """Show the threads in this loom.

    Output the threads in this loom with the newest thread at the top and
    the base thread at the bottom. A => marker indicates the thread that
    'commit' will commit to.
    """

    takes_args = ['location?']

    def run(self, location='.'):
        (loom, path) = bzrlib.branch.Branch.open_containing(location)
        branch.require_loom_branch(loom)
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


class cmd_status(bzrlib.builtins.cmd_status):
    """Show status of a loom."""

    _original_command = None

    def run(self, show_ids=False, file_list=None, revision=None, short=False,
            versioned=False, no_pending=False, verbose=None):
        if file_list is None:
            path = '.'
        else:
            path = file_list[0]
        (loom, _) = bzrlib.branch.Branch.open_containing(path)
        formats.require_loom_branch(loom)
        loom.lock_read()
        try:
            print 'Current thread: %s' % loom.nick
        finally:
            loom.unlock()

    def run_argv_aliases(self, argv, alias_argv=None):
        """Decorate bzr's cmd_status to show status for looms as well."""
        self._original_command().run_argv_aliases(argv, alias_argv)
        try:
            super(cmd_status, self).run_argv_aliases(list(argv), alias_argv)
        except formats.NotALoom:
            pass


class cmd_switch(bzrlib.builtins.cmd_switch):
    """Set the branch of a checkout and update.
 
    For looms, this is equivalent to 'down-thread' when to_location is the name
    of a thread in the loom.
    For lightweight checkouts, this changes the branch being referenced.
    For heavyweight checkouts, this checks that there are no local commits
    versus the current bound branch, then it makes the local branch a mirror
    of the new location and binds to it.
    
    In both cases, the working tree is updated and uncommitted changes
    are merged. The user can commit or revert these as they desire.

    Pending merges need to be committed or reverted before using switch.
    """

    _original_command = None

    def _get_thread_name(self, loom, to_location):
        """Return the name of the thread pointed to by 'to_location'.

        Most of the time this will be the name of the thread, but if
        'to_location' is 'bottom:' it will be the name of the bottom thread.
        If 'to_location' is 'top:', then it'll be the name of the top thread.
        """
        aliases = {'bottom:': 0, 'top:': -1}
        if to_location in aliases:
            threads = loom.get_loom_state().get_threads()
            thread = threads[aliases[to_location]]
            return thread[0]
        return to_location

    def run(self, to_location=None, force=False, create_branch=False,
            revision=None, directory=None):
        # The top of this is cribbed from bzr; because bzr isn't factored out
        # enough.
        if directory is None:
            directory = u'.'
        control_dir, path = bzrdir.BzrDir.open_containing(directory)
        if to_location is None:
            if revision is None:
                raise errors.BzrCommandError(
                    'You must supply either a revision or a location')
            to_location = '.'
        try:
            from_branch = control_dir.open_branch()
        except errors.NotBranchError:
            from_branch = None
        if create_branch:
            if from_branch is None:
                raise errors.BzrCommandError(
                    'cannot create branch without source branch')
            to_location = directory_service.directories.dereference(
                to_location)
        if from_branch is not None:
            # Note: reopens.
            (tree, path) = workingtree.WorkingTree.open_containing(directory)
            tree = LoomTreeDecorator(tree)
            try:
                if create_branch:
                    return branch.create_thread(tree.branch, to_location)
                thread_name = self._get_thread_name(tree.branch, to_location)
                return tree.down_thread(thread_name)
            except (AttributeError, branch.NoSuchThread, branch.NotALoom):
                # When there is no thread its probably an external branch
                # that we have been given.
                raise errors.MustUseDecorated
        else:
            # switching to a relocated branch
            raise errors.MustUseDecorated

    def run_argv_aliases(self, argv, alias_argv=None):
        """Parse command line and run.
        
        If the command requests it, run the decorated version.
        """
        try:
            super(cmd_switch, self).run_argv_aliases(list(argv), alias_argv)
        except (errors.MustUseDecorated, errors.BzrOptionError):
            if self._original_command is None:
                raise
            self._original_command().run_argv_aliases(argv, alias_argv)


class cmd_record(bzrlib.commands.Command):
    """Record the current last-revision of this tree into the current thread."""

    takes_args = ['message']

    def run(self, message):
        (abranch, path) = bzrlib.branch.Branch.open_containing('.')
        branch.require_loom_branch(abranch)
        abranch.record_loom(message)
        print "Loom recorded."


class cmd_revert_loom(bzrlib.commands.Command):
    """Revert part or all of a loom.
    
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
        branch.require_loom_branch(tree.branch)
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

    Down-thread refuses to operate if there are uncommitted changes, since
    this is typically a mistake.  Switch can be used for this purpose, instead.
    """

    takes_args = ['thread?']
    aliases = ['down']
    _see_also = ['switch', 'up-thread']

    def run(self, thread=None):
        (wt, path) = workingtree.WorkingTree.open_containing('.')
        branch.require_loom_branch(wt.branch)
        tree = LoomTreeDecorator(wt)
        tree.lock_write()
        try:
            basis = wt.basis_tree()
            basis.lock_read()
            try:
                for change in wt.iter_changes(basis):
                    raise errors.BzrCommandError(
                        'Working tree has uncommitted changes.')
            finally:
                basis.unlock()
            return tree.down_thread(thread)
        finally:
            tree.unlock()


class cmd_up_thread(bzrlib.commands.Command):
    """Move the branch up to the top thread in the loom.

    This merges the changes done in this thread but not incorporated into
    the next thread up into the next thread up and switches your tree to be
    that thread.  Unless there are conflicts, or --manual is specified, it
    will then commit and repeat the process.
    """

    takes_args = ['thread?']

    takes_options = ['merge-type', Option('auto',
        help='Deprecated - now the default.'),
        Option('manual', help='Perform commit manually.'),
        ]

    _see_also = ['down-thread', 'switch']

    def run(self, merge_type=None, manual=False, thread=None, auto=None):
        (tree, path) = workingtree.WorkingTree.open_containing('.')
        branch.require_loom_branch(tree.branch)
        tree = LoomTreeDecorator(tree)
        if manual:
            if thread is not None:
                raise errors.BzrCommandError('Specifying a thread does not'
                                             ' work with --manual.')
            return tree.up_thread(merge_type)
        else:
            return tree.up_many(merge_type, thread)


class cmd_export_loom(bzrlib.commands.Command):
    """Export loom threads as a full-fledged branches.

    LOCATION specifies the location to export the threads under.  If it does
    not exist, it will be created.

    In any of the standard config files, "export_loom_root" may be set to
    provide a default location that will be used if no location is supplied.
    """

    takes_args = ['location?']
    _see_also = ['configuration']

    def run(self, location=None):
        root_transport = None
        loom = bzrlib.branch.Branch.open_containing('.')[0]
        if location is None:
            location = loom.get_config().get_user_option('export_loom_root')
        if location is None:
            raise errors.BzrCommandError('No export root known or specified.')
        root_transport = bzrlib.transport.get_transport(location,
            possible_transports=[loom.bzrdir.root_transport])
        root_transport.ensure_base()
        loom.export_threads(root_transport)
