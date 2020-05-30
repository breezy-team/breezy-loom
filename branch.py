# Loom, a plugin for bzr to assist in developing focused patches.
# Copyright (C) 2006 - 2008 Canonical Limited.
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

"""The Loom Branch format.

A Loom branch extends the behaviour of various methods to manage and propogate
the Loom specific data. In the future it would be nice to have this data 
registered with a normal bzr branch. That said, the branch format should still
be specific to loom, to ensure people have the loom plugin when working on a 
loom branch.
"""

from __future__ import absolute_import

from io import BytesIO

import breezy.branch
from breezy import (
    commit as _mod_commit,
    controldir,
    errors,
    symbol_versioning,
    trace,
    ui,
    urlutils,
    )
from breezy.bzr import (
    branch as _mod_bzrbranch,
    bzrdir,
    fetch as _mod_fetch,
    inventory as _mod_inventory,
    inventorytree as _mod_inventorytree,
    remote,
    )
from breezy.revision import is_null, NULL_REVISION

from breezy.plugins.loom import (
    loom_io,
    loom_state,
    require_loom_branch,
    NotALoom,
    )


EMPTY_REVISION = b'empty:'


from breezy.bzr.fullhistory import BzrBranch5, BzrBranchFormat5


def create_thread(loom, thread_name):
    """Create a thread in the branch loom called thread."""
    require_loom_branch(loom)
    with loom.lock_write():
        loom.new_thread(thread_name, loom.nick)
        loom._set_nick(thread_name)


class AlreadyLoom(errors.BzrError):

    _fmt = """Loom %(loom)s is already a loom."""

    def __init__(self, loom):
        errors.BzrError.__init__(self)
        self.loom = loom


def loomify(branch):
    """Convert branch to a loom.

    If branch is a BzrBranch5 branch, it will become a LoomBranch.
    """
    with branch.lock_write():
        try:
            require_loom_branch(branch)
        except NotALoom:
            pass
        else:
            raise AlreadyLoom(branch)
        try:
            format = {
                BzrBranchFormat5: BzrBranchLoomFormat1,
                _mod_bzrbranch.BzrBranchFormat6: BzrBranchLoomFormat6,
                _mod_bzrbranch.BzrBranchFormat7: BzrBranchLoomFormat7,
            }[branch._format.__class__]()
        except KeyError:
            raise UnsupportedBranchFormat(branch._format)
        format.take_over(branch)



class LoomThreadError(errors.BzrError):
    """Base class for Loom-Thread errors."""

    def __init__(self, branch, thread):
        errors.BzrError.__init__(self)
        self.branch = branch
        self.thread = thread


class UnrecordedRevision(errors.BzrError):

    _fmt = """The revision %(revision_id)s is not recorded in the loom %(branch)s."""

    def __init__(self, branch, revision_id):
        errors.BzrError.__init__(self)
        self.branch = branch
        self.revision_id = revision_id


class UnsupportedBranchFormat(errors.BzrError):

    _fmt = """The branch format %(format)s is not supported by loomify."""

    def __init__(self, format):
        self.format = format


class DuplicateThreadName(LoomThreadError):

    _fmt = """The thread %(thread)s already exists in branch %(branch)s."""


class UnchangedThreadRevision(LoomThreadError):

    _fmt = """No new commits to record on thread %(thread)s."""


class NoSuchThread(LoomThreadError):

    _fmt = """No such thread '%(thread)s'."""


class NoLowerThread(errors.BzrError):

    _fmt = """No lower thread exists."""


class CannotCombineOnLastThread(NoLowerThread):

    _fmt = """Cannot combine threads on the bottom thread."""


class LoomMetaTree(_mod_inventorytree.InventoryTree):
    """A 'tree' object that is used to commit the loom meta branch."""

    def __init__(self, loom_meta_ie, loom_stream, loom_sha1):
        """Create a Loom Meta Tree.

        :param loom_content_lines: the unicode content to be used for the loom.
        """
        self._inventory = _mod_inventory.Inventory()
        self._inventory.add(loom_meta_ie)
        self._loom_stream = loom_stream
        self._loom_sha1 = loom_sha1
    
    def get_file(self, path, file_id=None):
        """Get the content of file_id from this tree.

        As usual this must be for the single existing file 'loom'.
        """
        return self._loom_stream

    def get_file_with_stat(self, path, file_id=None):
        return (self.get_file(path, file_id), None)

    def get_file_sha1(self, path, file_id=None, stat_value=None):
        """Get the sha1 for a file. 

        This tree only has one file, so it MUST be present!
        """
        assert path == 'loom'
        assert file_id is None or file_id == b'loom_meta_tree'
        return self._loom_sha1

    def is_executable(self, path, file_id=None):
        """get the executable status for file_id.
        
        Nothing in a LoomMetaTree is executable.
        """
        return False

    def _comparison_data(self, entry, path):
        if entry is None:
            return None, False, None
        return entry.kind, entry.executable, None


class LoomSupport(object):
    """Loom specific logic called into from Branch."""

    def _adjust_nick_after_changing_threads(self, threads, current_index):
        """Adjust the branch nick when we may have removed a current thread.

        :param threads: The current threads.
        :param position: The position in the old threads self.nick had.
        """
        threads_dict = dict(thread[0:2] for thread in threads)
        if self.nick not in threads_dict:
            if not len(threads):
                # all threads gone
                # revert to being a normal branch: revert to an empty revision
                # history.
                self.generate_revision_history(breezy.revision.NULL_REVISION)
                return
            # TODO, calculate the offset of removed threads.
            # i.e. if there are ten threads removed, and current_index is 5, 
            # if 4 of the ten removed were 2,3,4,5, then the new index should
            # be 2.
            if len(threads) <= current_index:
                # removed the end
                # take the new end thread
                self._set_nick(threads[-1][0])
                new_rev = threads[-1][1]
                if new_rev == EMPTY_REVISION:
                    new_rev = breezy.revision.NULL_REVISION
                self.generate_revision_history(new_rev)
                return
            # non-end thread removed.
            self._set_nick(threads[current_index][0])
            new_rev = threads[current_index][1]
            if new_rev == EMPTY_REVISION:
                new_rev = breezy.revision.NULL_REVISION
            self.generate_revision_history(new_rev)
        elif self.last_revision() != threads_dict[self.nick]:
            new_rev = threads_dict[self.nick]
            if new_rev == EMPTY_REVISION:
                new_rev = breezy.revision.NULL_REVISION
            self.generate_revision_history(new_rev)

    def bind(self, other):
        """Bind the local branch the other branch.

        :param other: The branch to bind to
        :type other: Branch
        """
        # Looms are not currently bindable.
        raise errors.UpgradeRequired(self.base)

    def clone(self, to_controldir, revision_id=None, repository_policy=None, name=None,
              tag_selector=None):
        """Clone the branch into to_controldir.
        
        This differs from the base clone by cloning the loom, setting the
        current nick to the top of the loom, not honouring any branch format
        selection on the target controldir, and ensuring that the format of
        the created branch is stacking compatible.
        """
        # If the target is a stackable repository, force-upgrade the
        # output loom format
        if (isinstance(to_controldir, bzrdir.BzrDirMeta1) and
            to_controldir._format.repository_format.supports_external_lookups):
            format = BzrBranchLoomFormat7()
        else:
            format = self._format
        result = format.initialize(to_controldir, name=name)
        if repository_policy is not None:
            repository_policy.configure_branch(result)
        with self.lock_read():
            breezy.branch.InterBranch.get(self, result).copy_content_into(
                revision_id=revision_id, tag_selector=tag_selector)
            return result

    def _get_checkout_format(self, lightweight=False):
        """Checking out a Loom gets a regular branch for now.
        
        This is a short term measure to get to an all-tests passing status.
        """
        format = self.repository.controldir.checkout_metadir()
        format.set_branch_format(breezy.branch.BzrBranchFormat6())
        return format

    def get_loom_state(self):
        """Get the current loom state object."""
        # TODO: cache the loom state during the transaction lifetime.
        current_content = self._transport.get('last-loom')
        reader = loom_io.LoomStateReader(current_content)
        state = loom_state.LoomState(reader)
        return state
    
    def get_old_bound_location(self):
        """Return the URL of the branch we used to be bound to."""
        # No binding for looms yet.
        raise errors.UpgradeRequired(self.base)

    def get_threads(self, rev_id):
        """Return the threads from a loom revision.

        :param rev_id: A specific loom revision to retrieve.
        :return: a list of threads. e.g. [('threadname', 'last_revision')]
        """
        if rev_id is None:
            symbol_versioning.warn('NULL_REVISION should be used for the null'
                ' revision instead of None, as of bzr 0.90.',
                DeprecationWarning, stacklevel=2)
        if is_null(rev_id):
            return []
        content = self._loom_content(rev_id)
        return self._parse_loom(content)

    def export_threads(self, root_transport):
        """Export the threads in this loom as branches.

        :param root_transport: Transport for the directory to place branches
            under.  Defaults to branch root transport.
        """
        threads = self.get_loom_state().get_threads()
        for thread_name, thread_revision, _parents in threads:
            thread_transport = root_transport.clone(thread_name)
            user_location = urlutils.unescape_for_display(
                thread_transport.base, 'utf-8')
            try:
                control_dir = controldir.ControlDir.open(thread_transport.base,
                    possible_transports=[thread_transport])
                tree, branch = control_dir._get_tree_branch()
            except errors.NotBranchError:
                trace.note('Creating branch at %s' % user_location)
                branch = controldir.ControlDir.create_branch_convenience(
                    thread_transport.base,
                    possible_transports=[thread_transport])
                tree, branch = branch.controldir.open_tree_or_branch(
                    thread_transport.base)
            else:
                if thread_revision == branch.last_revision():
                    trace.note('Skipping up-to-date branch at %s'
                                      % user_location)
                    continue
                else:
                    trace.note('Updating branch at %s' % user_location)
            if tree is not None:
                tree.pull(self, stop_revision=thread_revision)
            else:
                branch.pull(self, stop_revision=thread_revision)

    def _loom_content(self, rev_id):
        """Return the raw formatted content of a loom as a series of lines.

        :param rev_id: A specific loom revision to retrieve.

        Currently the disk format is:
        ----
        Loom meta 1
        revisionid threadname_in_utf8
        ----
        if revisionid is empty:, this is a new, empty branch.
        """
        tree = self.repository.revision_tree(rev_id)
        with tree.get_file('loom') as f:
            lines = f.read().split(b'\n')
        assert lines[0] == b'Loom meta 1'
        return lines[1:-1]

    def loom_parents(self):
        """Return the current parents to use in the next commit."""
        return self.get_loom_state().get_parents()

    def new_thread(self, thread_name, after_thread=None):
        """Add a new thread to this branch called 'thread_name'."""
        state = self.get_loom_state()
        threads = state.get_threads()
        if thread_name in state.get_threads_dict():
            raise DuplicateThreadName(self, thread_name)
        assert after_thread is None or after_thread in state.get_threads_dict()
        if after_thread is None:
            insertion_point = len(threads)
        else:
            insertion_point = state.thread_index(after_thread) + 1
        if insertion_point == 0:
            revision_for_thread = self.last_revision()
        else:
            revision_for_thread = threads[insertion_point - 1][1]
        if is_null(revision_for_thread):
            revision_for_thread = EMPTY_REVISION
        threads.insert(
            insertion_point,
            (thread_name,
             revision_for_thread,
             [None] * len(state.get_parents())
             )
            )
        state.set_threads(threads)
        self._set_last_loom(state)

    def _parse_loom(self, content):
        """Parse the body of a loom file."""
        result = []
        for line in content:
            rev_id, name = line.split(b' ', 1)
            result.append((name.decode('utf-8'), rev_id))
        return result

    def _loom_get_nick(self):
        return self._get_nick(local=True)

    def _rename_thread(self, nick):
        """Rename the current thread to nick."""
        state = self.get_loom_state()
        threads = state.get_threads()
        if not len(threads):
            # No threads at all - probably a default initialised loom in the
            # test suite.
            return  self._set_nick(nick)
        current_index = state.thread_index(self.nick)
        threads[current_index] = (nick,) + threads[current_index][1:]
        state.set_threads(threads)
        self._set_last_loom(state)
        # Preserve default behavior: set the branch nick
        self._set_nick(nick)

    nick = property(_loom_get_nick, _rename_thread)

    def heads_to_fetch(self):
        """See Branch.heads_to_fetch."""
        # The base implementation returns ([tip], tags)
        must_fetch, should_fetch = super(LoomSupport, self).heads_to_fetch()
        # Add each thread's content to must_fetch
        must_fetch.update(
            thread_rev for thread_name, thread_rev, thread_parents in
            self.get_loom_state().get_threads())
        must_fetch.discard(EMPTY_REVISION)
        must_fetch.discard(breezy.revision.NULL_REVISION)
        return must_fetch, should_fetch

    def push(self, target, overwrite=False, stop_revision=None, lossy=False,
        _override_hook_source_branch=None):
        # Not ideal, but see the issues raised on bazaar@lists.canonical.com
        # about the push api needing work.
        with self.lock_read():
            if not isinstance(target, LoomSupport):
                return super(LoomSupport, self).push(target, overwrite,
                    stop_revision, lossy=lossy, _override_hook_source_branch=None)
            if lossy:
                raise errors.LossyPushToSameVCS(self, target)
            return _Pusher(self, target).transfer(overwrite, stop_revision,
                                                  run_hooks=True)

    def record_loom(self, commit_message):
        """Perform a 'commit' to the loom branch.

        :param commit_message: The commit message to use when committing.
        """
        with self.lock_write():
            state = self.get_loom_state()
            parents = state.get_parents()
            old_threads = self.get_threads(state.get_basis_revision_id())
            threads = state.get_threads()
            # check the semantic value, not the serialised value for equality.
            if old_threads == threads:
                raise _mod_commit.PointlessCommit
            builder = self.get_commit_builder(parents)
            loom_ie = _mod_inventory.make_entry(
                'file', 'loom', _mod_inventory.ROOT_ID, b'loom_meta_tree')
            writer = loom_io.LoomWriter()
            loom_stream = BytesIO()
            new_threads = [thread[0:2] for thread in threads]
            loom_sha1 = writer.write_threads(new_threads, loom_stream)
            loom_stream.seek(0)
            loom_tree = LoomMetaTree(loom_ie, loom_stream, loom_sha1)
            try:
                basis_revid = parents[0]
            except IndexError:
                basis_revid = breezy.revision.NULL_REVISION
            for unused in builder.record_iter_changes(
                loom_tree, basis_revid,
                loom_tree.iter_changes(self.repository.revision_tree(basis_revid))):
                pass
            builder.finish_inventory()
            rev_id = builder.commit(commit_message)
            state.set_parents([rev_id])
            state.set_threads((thread + ([thread[1]],) for thread in new_threads))
            self._set_last_loom(state)
            return rev_id
    
    def record_thread(self, thread_name, revision_id):
        """Record an updated version of an existing thread.

        :param thread_name: the thread to record.
        :param revision_id: the revision it is now at. This should be a child
        of the next lower thread.
        """
        with self.lock_write():
            state = self.get_loom_state()
            threads = state.get_threads()
            assert thread_name in state.get_threads_dict()
            if is_null(revision_id):
                revision_id = EMPTY_REVISION
            for position, (name, rev, parents) in enumerate(threads):
                if name == thread_name:
                    if revision_id == rev:
                        raise UnchangedThreadRevision(self, thread_name)
                    threads[position] = (name, revision_id, parents)
            state.set_threads(threads)
            self._set_last_loom(state)

    def remove_thread(self, thread_name):
        """Remove thread from the current loom.

        :param thread_name: The thread to remove.
        """
        with self.lock_write():
            state = self.get_loom_state()
            threads = state.get_threads()
            current_index = state.thread_index(thread_name)
            del threads[current_index]
            state.set_threads(threads)
            self._set_last_loom(state)

    def revert_loom(self):
        """Revert the loom to be the same as the basis loom."""
        with self.lock_write():
            state = self.get_loom_state()
            # get the current position
            position = state.thread_index(self.nick)
            # reset the current threads
            basis_threads = self.get_threads(state.get_basis_revision_id())
            state.set_threads(
                (thread + ([thread[1]],) for thread in basis_threads)
                )
            basis_rev_id = state.get_basis_revision_id()
            # reset the parents list to just the basis.
            if basis_rev_id is not None:
                state.set_parents([basis_rev_id])
            self._adjust_nick_after_changing_threads(state.get_threads(), position)
            self._set_last_loom(state)

    def revert_thread(self, thread):
        """Revert a single thread.
        
        :param thread: the thread to restore to its state in
            the basis. If it was not present in the basis it 
            will be removed from the current loom.
        """
        with self.lock_write():
            state = self.get_loom_state()
            parents = state.get_parents()
            threads = state.get_threads()
            position = state.thread_index(thread)
            basis_threads = self.get_threads(state.get_basis_revision_id())
            if thread in dict(basis_threads):
                basis_rev = dict(basis_threads)[thread]
                threads[position] = (thread, basis_rev, threads[position][2])
            else:
                del threads[position]
            state.set_threads(threads)
            self._set_last_loom(state)
            # adjust the nickname to be valid
            self._adjust_nick_after_changing_threads(threads, position)

    def _set_last_loom(self, state):
        """Record state to the last-loom control file."""
        stream = BytesIO()
        writer = loom_io.LoomStateWriter(state)
        writer.write(stream)
        stream.seek(0)
        self._transport.put_file('last-loom', stream)

    def unlock(self):
        """Unlock the loom after a lock.

        If at the end of the lock, the current revision in the branch is not
        recorded correctly in the loom, an automatic record is attempted.
        """
        if (self.control_files._lock_count==1 and
            self.control_files._lock_mode=='w'):
            # about to release the lock
            state = self.get_loom_state()
            threads = state.get_threads()
            if len(threads):
                # looms are enabled:
                lastrev = self.last_revision()
                if is_null(lastrev):
                    lastrev = EMPTY_REVISION
                if dict(state.get_threads_dict())[self.nick][0] != lastrev:
                    self.record_thread(self.nick, lastrev)
        super(LoomSupport, self).unlock()


class _Puller(object):
    # XXX: Move into InterLoomBranch.

    def __init__(self, source, target):
        self.target = target
        self.source = source
        # If _Puller has been created, we need real branch objects.
        self.real_target = self.unwrap_branch(target)
        self.real_source = self.unwrap_branch(source)

    def unwrap_branch(self, branch):
        if isinstance(branch, remote.RemoteBranch):
            branch._ensure_real()
            return branch._real_branch
        return branch

    def prepare_result(self, _override_hook_target):
        result = self.make_result()
        result.source_branch = self.source
        result.target_branch = _override_hook_target
        if result.target_branch is None:
            result.target_branch = self.target
        # cannot bind currently
        result.local_branch = None
        result.master_branch = self.target
        result.old_revno, result.old_revid = self.target.last_revision_info()
        return result

    def finish_result(self, result):
        result.new_revno, result.new_revid = self.target.last_revision_info()

    def do_hooks(self, result, run_hooks):
        self.finish_result(result)
        # get the final result object details
        if run_hooks:
            for hook in self.post_hooks():
                hook(result)
        return result

    @staticmethod
    def make_result():
        return breezy.branch.PullResult()

    @staticmethod
    def post_hooks():
        return breezy.branch.Branch.hooks['post_pull']

    def plain_transfer(self, result, run_hooks, stop_revision, overwrite):
        # no thread commits ever
        # just pull the main branch.
        new_rev = stop_revision
        if new_rev is None:
            new_rev = self.source.last_revision()
        if new_rev == EMPTY_REVISION:
            new_rev = breezy.revision.NULL_REVISION
        fetch_spec = self.build_fetch_spec(stop_revision)
        self.target.repository.fetch(self.source.repository,
            fetch_spec=fetch_spec)
        self.target.generate_revision_history(new_rev, self.target.last_revision(),
            self.source)
        tag_ret = self.source.tags.merge_to(self.target.tags)
        if isinstance(tag_ret, tuple):
            result.tag_updates, result.tag_conflicts = tag_ret
        else:
            result.tag_conflicts = tag_ret
        # get the final result object details
        self.do_hooks(result, run_hooks)
        return result

    def build_fetch_spec(self, stop_revision):
        factory = _mod_fetch.FetchSpecFactory()
        factory.source_branch = self.source
        factory.source_repo = self.source.repository
        factory.source_branch_stop_revision_id = stop_revision
        factory.target_repo = self.target.repository
        factory.target_repo_kind = _mod_fetch.TargetRepoKinds.PREEXISTING
        return factory.make_fetch_spec()

    def transfer(self, overwrite, stop_revision, run_hooks=True,
        possible_transports=None, _override_hook_target=None, local=False):
        """Implementation of push and pull"""
        if local:
            raise errors.LocalRequiresBoundBranch()
        # pull the loom, and position our
        pb = ui.ui_factory.nested_progress_bar()
        try:
            result = self.prepare_result(_override_hook_target)
            with self.target.lock_write(), self.source.lock_read():
                source_state = self.real_source.get_loom_state()
                source_parents = source_state.get_parents()
                if not source_parents:
                    return self.plain_transfer(result, run_hooks,
                                               stop_revision, overwrite)
                # pulling a loom
                # the first parent is the 'tip' revision.
                my_state = self.target.get_loom_state()
                source_loom_rev = source_state.get_parents()[0]
                if not overwrite:
                    # is the loom compatible?
                    if len(my_state.get_parents()) > 0:
                        graph = self.source.repository.get_graph()
                        if not graph.is_ancestor(my_state.get_parents()[0],
                                source_loom_rev):
                            raise errors.DivergedBranches(
                                self.target, self.source)
                # fetch the loom content
                self.target.repository.fetch(self.source.repository,
                    revision_id=source_loom_rev)
                # get the threads for the new basis
                threads = self.target.get_threads(
                    source_state.get_basis_revision_id())
                # stopping at from our repository.
                revisions = [rev for name,rev in threads]
                # fetch content for all threads and tags.
                fetch_spec = self.build_fetch_spec(stop_revision)
                self.target.repository.fetch(self.source.repository,
                    fetch_spec=fetch_spec)
                # set our work threads to match (this is where we lose data if
                # there are local mods)
                my_state.set_threads(
                    (thread + ([thread[1]],) for thread in threads)
                    )
                # and the new parent data
                my_state.set_parents([source_loom_rev])
                # and save the state.
                self.target._set_last_loom(my_state)
                # set the branch nick.
                self.target._set_nick(threads[-1][0])
                # and position the branch on the top loom
                new_rev = threads[-1][1]
                if new_rev == EMPTY_REVISION:
                    new_rev = breezy.revision.NULL_REVISION
                self.target.generate_revision_history(new_rev)
                # merge tags
                tag_ret = self.source.tags.merge_to(self.target.tags)
                if isinstance(tag_ret, tuple):
                    result.tag_updates, tag_conflicts = tag_ret
                else:
                    result.tag_conflicts = tag_ret
                self.do_hooks(result, run_hooks)
                return result
        finally:
            pb.finished()


class _Pusher(_Puller):

    @staticmethod
    def make_result():
        return breezy.branch.BranchPushResult()

    @staticmethod
    def post_hooks():
        return breezy.branch.Branch.hooks['post_push']


class LoomBranch(LoomSupport, BzrBranch5):
    """The Loom branch.
    
    A mixin is used as the easiest migration path to support branch6. A
    delegated object may well be cleaner.
    """


class LoomBranch6(LoomSupport, _mod_bzrbranch.BzrBranch6):
    """Branch6 Loom branch.

    A mixin is used as the easiest migration path to support branch6. A
    delegated object may well be cleaner.
    """


class LoomBranch7(LoomSupport, _mod_bzrbranch.BzrBranch7):
    """Branch6 Loom branch.

    A mixin is used as the easiest migration path to support branch7.
    A rewrite would be preferable, but a stackable loom format is needed
    quickly.
    """


class LoomFormatMixin(object):
    """Support code for Loom formats."""
    # A mixin is not ideal because it is tricky to test, but it seems to be the
    # best solution for now.

    def initialize(self, a_controldir, name=None, repository=None,
                   append_revisions_only=None):
        """Create a branch of this format in a_controldir."""
        super(LoomFormatMixin, self).initialize(a_controldir, name=name,
                repository=repository,
                append_revisions_only=append_revisions_only)

        branch_transport = a_controldir.get_branch_transport(self)
        files = []
        state = loom_state.LoomState()
        writer = loom_io.LoomStateWriter(state)
        state_stream = BytesIO()
        writer.write(state_stream)
        state_stream.seek(0)
        files.append(('last-loom', state_stream))
        control_files = breezy.lockable_files.LockableFiles(
            branch_transport, 'lock', breezy.lockdir.LockDir)
        control_files.lock_write()
        try:
            for filename, stream in files:
                branch_transport.put_file(filename, stream)
        finally:
            control_files.unlock()
        return self.open(a_controldir, _found=True, name=name)

    def open(self, a_controldir, name=None, _found=False, ignore_fallbacks=False,
            found_repository=None, possible_transports=None):
        """Return the branch object for a_controldir

        _found is a private parameter, do not use it. It is used to indicate
               if format probing has already be done.

        :param name: The 'colocated branches' name for the branch to open.
        """
        if name is None:
            name = a_controldir._get_selected_branch()
        if not _found:
            format = breezy.branch.BranchFormat.find_format(a_controldir, name=name)
            assert format.__class__ == self.__class__
        transport = a_controldir.get_branch_transport(None, name=name)
        control_files = breezy.lockable_files.LockableFiles(
            transport, 'lock', breezy.lockdir.LockDir)
        if found_repository is None:
            found_repository = a_controldir.find_repository()
        return self._branch_class()(_format=self,
                          _control_files=control_files,
                          a_controldir=a_controldir,
                          _repository=found_repository,
                          ignore_fallbacks=ignore_fallbacks,
                          name=name)

    def take_over(self, branch):
        """Take an existing breezy branch over into Loom format.

        This currently cannot convert branches to Loom format unless they are
        in Branch 5 format.

        The conversion takes effect when the branch is next opened.
        """
        assert branch._format.__class__ is self._parent_classs
        branch._transport.put_bytes('format', self.get_format_string())
        state = loom_state.LoomState()
        writer = loom_io.LoomStateWriter(state)
        state_stream = BytesIO()
        writer.write(state_stream)
        state_stream.seek(0)
        branch._transport.put_file('last-loom', state_stream)



class BzrBranchLoomFormat1(LoomFormatMixin, BzrBranchFormat5):
    """Loom's first format.

    This format is an extension to BzrBranchFormat5 with the following changes:
     - a loom-revision file.

     The loom-revision file has a revision id in it which points into the loom
     data branch in the repository.

    This format is new in the loom plugin.
    """

    def _branch_class(self):
        return LoomBranch

    _parent_classs = BzrBranchFormat5

    @classmethod
    def get_format_string(cls):
        """See BranchFormat.get_format_string()."""
        return b"Bazaar-NG Loom branch format 1\n"

    def get_format_description(self):
        """See BranchFormat.get_format_description()."""
        return "Loom branch format 1"
        
    def __str__(self):
        return "Bazaar-NG Loom format 1"


class BzrBranchLoomFormat6(LoomFormatMixin, _mod_bzrbranch.BzrBranchFormat6):
    """Loom's second edition - based on bzr's Branch6.

    This format is an extension to BzrBranchFormat6 with the following changes:
     - a last-loom file.

     The last-loom file has a revision id in it which points into the loom
     data branch in the repository.

    This format is new in the loom plugin.
    """

    def _branch_class(self):
        return LoomBranch6

    _parent_classs = _mod_bzrbranch.BzrBranchFormat6

    @classmethod
    def get_format_string(cls):
        """See BranchFormat.get_format_string()."""
        return b"Bazaar-NG Loom branch format 6\n"

    def get_format_description(self):
        """See BranchFormat.get_format_description()."""
        return "Loom branch format 6"

    def __str__(self):
        return "bzr loom format 6 (based on bzr branch format 6)\n"


class BzrBranchLoomFormat7(LoomFormatMixin, _mod_bzrbranch.BzrBranchFormat7):
    """Loom's second edition - based on bzr's Branch7.

    This format is an extension to BzrBranchFormat7 with the following changes:
     - a last-loom file.

     The last-loom file has a revision id in it which points into the loom
     data branch in the repository.

    This format is new in the loom plugin.
    """

    def _branch_class(self):
        return LoomBranch7

    _parent_classs = _mod_bzrbranch.BzrBranchFormat7

    @classmethod
    def get_format_string(cls):
        """See BranchFormat.get_format_string()."""
        return b"Bazaar-NG Loom branch format 7\n"

    def get_format_description(self):
        """See BranchFormat.get_format_description()."""
        return "Loom branch format 7"

    def __str__(self):
        return "bzr loom format 7 (based on bzr branch format 7)\n"


# Handle the smart server:

class InterLoomBranch(breezy.branch.GenericInterBranch):

    @classmethod
    def _get_branch_formats_to_test(klass):
        default_format = breezy.branch.format_registry.get_default()
        return [
            (default_format, BzrBranchLoomFormat7()),
            (BzrBranchLoomFormat7(), default_format),
            (BzrBranchLoomFormat7(), BzrBranchLoomFormat7()),
            ]

    def unwrap_branch(self, branch):
        if isinstance(branch, remote.RemoteBranch):
            branch._ensure_real()
            return branch._real_branch
        return branch

    @classmethod
    def is_compatible(klass, source, target):
        # 1st cut: special case and handle all *->Loom and Loom->*
        return klass.branch_is_loom(source) or klass.branch_is_loom(target)

    def get_loom_state(self, branch):
        branch = self.unwrap_branch(branch)
        return branch.get_loom_state()

    def get_threads(self, branch, revision_id):
        branch = self.unwrap_branch(branch)
        return branch.get_threads(revision_id)

    @classmethod
    def branch_is_loom(klass, branch):
        format = klass.unwrap_format(branch._format)
        return isinstance(format, LoomFormatMixin)

    def copy_content_into(self, revision_id=None, tag_selector=None):
        with self.lock_write():
            if not self.__class__.branch_is_loom(self.source):
                # target is loom, but the generic code path works Just Fine for
                # regular to loom copy_content_into.
                return super(InterLoomBranch, self).copy_content_into(
                    revision_id=revision_id, tag_selector=tag_selector)
            # XXX: hint for breezy - break this into two routines, one for
            # copying the last-rev pointer, one for copying parent etc.
            state = self.get_loom_state(self.source)
            parents = state.get_parents()
            if parents:
                loom_tip = parents[0]
            else:
                loom_tip = None
            threads = self.get_threads(self.source, state.get_basis_revision_id())
            if revision_id not in (None, NULL_REVISION):
                if threads:
                    # revision_id should be in the loom, or its an error
                    found_threads = [
                        thread for thread, rev in threads
                        if rev == revision_id]
                    if not found_threads:
                        # the thread we have been asked to set in the remote
                        # side has not been recorded yet, so its data is not
                        # present at this point.
                        raise UnrecordedRevision(self.source, revision_id)

                # pull in the warp, which was skipped during the initial pull
                # because the front end does not know what to pull.
                # nb: this is mega huge hacky. THINK. RBC 2006062
                nested = ui.ui_factory.nested_progress_bar()
                try:
                    if parents:
                        self.target.repository.fetch(self.source.repository,
                            revision_id=parents[0])
                    if threads:
                        for thread, rev_id in reversed(threads):
                            # fetch the loom content for this revision
                            self.target.repository.fetch(self.source.repository,
                                revision_id=rev_id)
                finally:
                    nested.finished()
            state = loom_state.LoomState()
            try:
                require_loom_branch(self.target)
                if threads:
                    last_rev = threads[-1][1]
                    if last_rev == EMPTY_REVISION:
                        last_rev = breezy.revision.NULL_REVISION
                    self.target.generate_revision_history(last_rev)
                    state.set_parents([loom_tip])
                    state.set_threads(
                        (thread + ([thread[1]],) for thread in threads)
                        )
                else:
                    # no threads yet, be a normal branch.
                    self.source._synchronize_history(self.target, revision_id)
                target_loom = self.unwrap_branch(self.target)
                target_loom._set_last_loom(state)
            except NotALoom:
                self.source._synchronize_history(self.target, revision_id)
            try:
                parent = self.source.get_parent()
            except errors.InaccessibleParent as e:
                trace.mutter('parent was not accessible to copy: %s', e)
            else:
                if parent:
                    self.target.set_parent(parent)
            if threads:
                self.target._set_nick(threads[-1][0])
            if self.source._push_should_merge_tags():
                self.source.tags.merge_to(
                    self.target.tags, seletor=tag_selector)

    def pull(self, overwrite=False, stop_revision=None,
             run_hooks=True, possible_transports=None, _override_hook_target=None,
             local=False, tag_selector=None):
        """Perform a pull, reading from self.source and writing to self.target.

        If the source branch is a non-loom branch, the pull is done against the
        current warp. If it is a loom branch, then the pull is done against the
        entire loom and the current thread set to the top thread.
        """
        with self.lock_write():
            # Special code only needed when both source and targets are looms:
            if (self.__class__.branch_is_loom(self.target) and
                self.__class__.branch_is_loom(self.source)):
                return _Puller(self.source, self.target).transfer(overwrite, stop_revision,
                    run_hooks, possible_transports, _override_hook_target, local)
            return super(InterLoomBranch, self).pull(
                overwrite=overwrite, stop_revision=stop_revision,
                possible_transports=possible_transports,
                _override_hook_target=_override_hook_target, local=local,
                run_hooks=run_hooks, tag_selector=tag_selector)


breezy.branch.InterBranch.register_optimiser(InterLoomBranch)
