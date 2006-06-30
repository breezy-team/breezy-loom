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

"""The Loom Branch format.

A Loom branch extends the behaviour of various methods to manage and propogate
the Loom specific data. In the future it would be nice to have this data 
registered with a normal bzr branch. That said, the branch format should still
be specific to loom, to ensure people have the loom plugin when working on a 
loom branch.
"""

from StringIO import StringIO

import bzrlib.branch
from bzrlib.decorators import needs_read_lock
import bzrlib.errors
import bzrlib.osutils
import bzrlib.ui


class LoomThreadError(bzrlib.errors.BzrNewError):
    """Base class for Loom-Thread errors."""

    def __init__(self, branch, thread):
        bzrlib.errors.BzrNewError.__init__(self)
        self.branch = branch
        self.thread = thread


class UnrecordedRevision(bzrlib.errors.BzrNewError):
    """The revision %(revision_id)s is not recorded in the loom %(branch)s."""

    def __init__(self, branch, revision_id):
        bzrlib.errors.BzrNewError.__init__(self)
        self.branch = branch
        self.revision_id = revision_id


class DuplicateThreadName(LoomThreadError):
    """The thread %(thread)s already exists in branch %(branch)s."""


class UnchangedThreadRevision(LoomThreadError):
    """No new commits to record on thread %(thread)s."""


class LoomMetaTree(bzrlib.tree.Tree):
    """A 'tree' object that is used to commit the loom meta branch."""

    def __init__(self, loom_meta_ie, loom_content_lines):
        """Create a Loom Meta Tree.

        :param loom_content_lines: the unicode content to be used for the loom.
        """
        self._inventory = bzrlib.inventory.Inventory()
        self.inventory.add(loom_meta_ie)
        self.loom_content_lines = ['Loom meta 1\n'] + [
            line.encode('utf8') for line in loom_content_lines]
    
    def get_file(self, file_id):
        """Get the content of file_id from this tree.

        As usual this must be for the single existing file 'loom'.
        """
        return StringIO(''.join(self.loom_content_lines))
    
    def get_file_sha1(self, file_id, path):
        """Get the sha1 for a file. 

        This tree only has one file, so it MUST be present!
        """
        assert path == 'loom'
        assert file_id == 'loom_meta_tree'
        return bzrlib.osutils.sha_strings(self.loom_content_lines)

    def is_executable(self, file_id, path):
        """get the executable status for file_id.
        
        Nothing in a LoomMetaTree is executable.
        """
        return False


class LoomBranch(bzrlib.branch.BzrBranch5):
    """The Loom branch."""

    @needs_read_lock
    def clone(self, to_bzrdir, revision_id=None):
        """Clone the branch into to_bzrdir.
        
        This differs from the base clone by cloning the loom.
        """
        result = self._format.initialize(to_bzrdir)
        self.copy_content_into(result, revision_id=revision_id)
        return  result

    @needs_read_lock
    def copy_content_into(self, destination, revision_id=None):
        # XXX: hint for bzrlib - break this into two routines, one for
        # copying the last-rev pointer, one for copying parent etc.
        # XXX: possibly we should use revision_id to determine what the
        # loom looked like when it was committed, rather than taking a
        # revision id in the loom branch. This suggests recording the 
        # loom revision when writing a commit to a warp, which would mean
        # that commit() could not do record() - we would have to record 
        # a loom revision that was not yet created.
        source_nick = self.nick
        threads = self.get_threads()
        parents = self.loom_parents()
        new_history = self.revision_history()
        if revision_id is not None:
            if threads:
                # revision_id should be in the loom, or its an error 
                found_threads = [thread for thread, rev in threads 
                    if rev == revision_id]
                if not found_threads:
                    raise UnrecordedRevision(self, revision_id)
            else:
                # no threads yet, be a normal branch
                try:
                    new_history = new_history[:new_history.index(revision_id) + 1]
                except ValueError:
                    rev = self.repository.get_revision(revision_id)
                    new_history = rev.get_history(self.repository)[1:]
                
            # pull in the warp, which was skipped during the initial pull
            # because the front end does not know what to pull.
            # nb: this is mega huge hacky. THINK. RBC 2006062
            nested = bzrlib.ui.ui_factory.nested_progress_bar()
            try:
                if parents:
                    destination.repository.fetch(self.repository,
                        revision_id=parents[0])
            finally:
                nested.finished()
        if threads:
            new_tip = dict(threads)[source_nick]
            destination.generate_revision_history(new_tip)
        else:
            # no threads yet, be a normal branch.
            destination.set_revision_history(new_history)
        if parents:
            destination._set_last_loom(parents[0])
        else:
            destination._set_last_loom('')
        parent = self.get_parent()
        if parent:
            destination.set_parent(parent)
        if self.get_config().has_explicit_nickname():
            destination.nick = source_nick
    
    def get_threads(self):
        """Return the current threads in this loom.

        :return: a list of threads. e.g. [('threadname', 'last_revision')]
        """
        content = self._loom_content()
        result = []
        for line in content:
            rev_id, name = line.split(' ', 1)
            # name contains the trailing \n
            result.append((name[:-1], rev_id))
        return result

    def _loom_content(self):
        """Return the raw formatted content of a loom as a series of lines.

        Currently the disk format is:
        ----
        Loom meta 1
        revisionid threadname_inu_tf8
        ----
        if revisionid is null:, this is a new, empty branch.
        """
        parents = self.loom_parents()
        if not parents:
            return []
        tree = self.repository.revision_tree(parents[0])
        lines = tree.get_file('loom_meta_tree').readlines()
        assert lines[0] == 'Loom meta 1\n'
        return lines[1:]

    def loom_parents(self):
        """Return the current parents to use in the next commit."""
        parent_content = self.control_files.get_utf8('last-loom')
        lines = parent_content.read().split('\n')
        return [line for line in lines if line]

    def new_thread(self, thread_name, after_thread=None):
        """Add a new thread to this branch called 'thread_name'."""
        threads = self.get_threads()
        if thread_name in dict(threads):
            raise DuplicateThreadName(self, thread_name)
        assert after_thread is None or after_thread in dict(threads)
        if after_thread is None:
            insertion_point = len(threads)
        else:
            thread_names = [name for name, rev in threads]
            insertion_point = thread_names.index(after_thread) + 1
        if insertion_point == 0:
            revision_for_thread = self.last_revision()
        else:
            revision_for_thread = threads[insertion_point - 1][1]
        content = self._loom_content()
        if revision_for_thread is None:
            revision_for_thread = bzrlib.revision.NULL_REVISION
        content.insert(
            insertion_point, "%s %s\n" % (revision_for_thread, thread_name))
        return self._record_loom(content, 'new thread: %s' % thread_name)

    def _record_loom(self, content, message):
        """Record the loom 'content'.

        :param content: the loom file as a sequence of lines. Each line should
        be a unicode string or a plain ascii string.
        """
        builder = self.get_commit_builder(self.loom_parents())
        loom_ie = bzrlib.inventory.make_entry(
            'file', 'loom', bzrlib.inventory.ROOT_ID, 'loom_meta_tree')
        loom_tree = LoomMetaTree(loom_ie, content)
        builder.record_entry_contents(
            loom_ie, self.loom_parents(), 'loom', loom_tree)
        builder.finish_inventory()
        rev_id = builder.commit(message)
        self._set_last_loom(rev_id)
        return rev_id

    def record_thread(self, thread_name, revision_id):
        """Record an updated version of an existing thread.

        :param thread_name: the thread to record.
        :param revision_id: the revision it is now at. This should be a child
        of the next lower thread.
        """
        threads = self.get_threads()
        assert thread_name in dict(threads)
        content = []
        if revision_id is None:
            revision_id = bzrlib.revision.NULL_REVISION
        for name, rev in threads:
            if name == thread_name:
                if revision_id == rev:
                    raise UnchangedThreadRevision(self, thread_name)
                rev = revision_id
            content.append("%s %s\n" % (rev, name))
        return self._record_loom(content, 'update thread %s' % thread_name)

    def _set_last_loom(self, rev_id):
        """Set the last loom revision in this branch to rev_id."""
        self.control_files.put_utf8('last-loom', rev_id)


class BzrBranchLoomFormat1(bzrlib.branch.BzrBranchFormat5):
    """Loom's first format.

    This format is an extension to BzrBranchFormat5 with the following changes:
     - a loom-revision file.

     The loom-revision file has a revision id in it which points into the loom
     data branch in the repository.

    This format is new in the loom plugin.
    """

    def get_format_string(self):
        """See BranchFormat.get_format_string()."""
        return "Bazaar-NG Loom branch format 1\n"

    def get_format_description(self):
        """See BranchFormat.get_format_description()."""
        return "Loom branch format 1"
        
    def initialize(self, a_bzrdir):
        """Create a branch of this format in a_bzrdir."""
        super(BzrBranchLoomFormat1, self).initialize(a_bzrdir)
        branch_transport = a_bzrdir.get_branch_transport(self)
        # TODO set this here.
        utf8_files = [('last-loom', ''),
                      ]
        control_files = bzrlib.lockable_files.LockableFiles(
            branch_transport, 'lock', bzrlib.lockdir.LockDir)
        control_files.lock_write()
        try:
            for file, content in utf8_files:
                control_files.put_utf8(file, content)
        finally:
            control_files.unlock()
        return self.open(a_bzrdir, _found=True, )

    def open(self, a_bzrdir, _found=False):
        """Return the branch object for a_bzrdir

        _found is a private parameter, do not use it. It is used to indicate
               if format probing has already be done.
        """
        if not _found:
            format = BranchFormat.find_format(a_bzrdir)
            assert format.__class__ == self.__class__
        transport = a_bzrdir.get_branch_transport(None)
        control_files = bzrlib.lockable_files.LockableFiles(
            transport, 'lock', bzrlib.lockdir.LockDir)
        return LoomBranch(_format=self,
                          _control_files=control_files,
                          a_bzrdir=a_bzrdir,
                          _repository=a_bzrdir.find_repository())

    def __str__(self):
        return "Bazaar-NG Loom format 1"

    def take_over(self, branch):
        """Take an existing bzrlib branch over into Loom format.

        This currently cannot convert branches to Loom format unless they are
        in Branch 5 format.

        The conversion takes effect when the branch is next opened.
        """
        assert branch._format.__class__ is bzrlib.branch.BzrBranchFormat5
        branch.control_files.put_utf8('format', self.get_format_string())
        branch.control_files.put_utf8('last-loom', '')


bzrlib.branch.BranchFormat.register_format(BzrBranchLoomFormat1())
