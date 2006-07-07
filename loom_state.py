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


"""The current-loom state object."""


class LoomState(object):
    """The LoomState represents the content of the current-loom branch file.
    
    It is planned to not need access to repository data - it will be driven
    by the LoomBranch and have data fed into it.
    """

    def __init__(self):
        self._parents = []
        self._parent_threads = []
        self._threads = []

    def get_basis_threads(self):
        """Get the basis threads for the this state."""
        if not self._parent_threads:
            return []
        else:
            return self._parent_threads[0]
        
    def get_parents(self):
        """Get the list of loom revisions that are parents to this state."""
        return self._parents

    def get_threads(self):
        """Get the threads for the current state."""
        return self._threads

    def set_parents(self, parent_list):
        """Set the parents of this state to parent_list.

        :param parent_list: A list of (parent_id, threads) tuples.
        """
        self._parents = []
        self._parent_threads = []
        for parent, parent_threads in parent_list:
            self._parents.append(parent)
            self._parent_threads.append(parent_threads)

    def set_threads(self, threads):
        """Set the current threads to threads.

        :param threads: A list of (name, revid) pairs that make up the threads.
            If the list is altered after calling set_threads, there is no 
            effect on the LoomState.
        """
        self._threads = list(threads)
