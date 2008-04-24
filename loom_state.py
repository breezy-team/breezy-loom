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


"""The current-loom state object."""

from bzrlib.revision import NULL_REVISION


class LoomState(object):
    """The LoomState represents the content of the current-loom branch file.
    
    It is planned to not need access to repository data - it will be driven
    by the LoomBranch and have data fed into it.
    """

    def __init__(self, reader=None):
        """Create a loom state object.

        :param reader: If not None, this should be a LoomStateReader from
            which this LoomState is meant to retrieve its current data.
        """
        self._parents = []
        self._threads = []
        if reader is not None:
            # perhaps this should be lazy evaluated at some point?
            self._parents = reader.read_parents()
            for thread in reader.read_thread_details():
                self._threads.append(thread)

    def get_basis_revision_id(self):
        """Get the revision id for the basis revision.

        None is return if there is no basis revision.
        """
        if not self._parents:
            return NULL_REVISION
        else:
            return self._parents[0]
 
    def get_parents(self):
        """Get the list of loom revisions that are parents to this state."""
        return self._parents

    def get_threads(self):
        """Get the threads for the current state."""
        return list(self._threads)

    def get_threads_dict(self):
        """Get the threads as a dict. 

        This loses ordering, but is useful for quickly locating the details on 
        a given thread.
        """
        return dict((thread[0], thread[1:]) for thread in self._threads)

    def thread_index(self, thread):
        """Find the index of thread in threads."""
        # Avoid circular import
        from bzrlib.plugins.loom.branch import NoSuchThread
        thread_names = [name for name, rev, parents in self._threads]
        try:
            return thread_names.index(thread)
        except ValueError:
            raise NoSuchThread(self, thread)

    def get_previous_thread(self, current_thread):
        current_index = self.thread_index(current_thread)
        if current_index == 0:
            return None
        return self._threads[current_index - 1][0]

    def set_parents(self, parent_list):
        """Set the parents of this state to parent_list.

        :param parent_list: A list of (parent_id, threads) tuples.
        """
        self._parents = list(parent_list)

    def set_threads(self, threads):
        """Set the current threads to threads.

        :param threads: A list of (name, revid) pairs that make up the threads.
            If the list is altered after calling set_threads, there is no 
            effect on the LoomState.
        """
        self._threads = list(threads)
