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

"""Loom specific revision-specifiers."""


from bzrlib.plugins.loom.branch import NoLowerThread
from bzrlib.revisionspec import SPEC_TYPES, RevisionSpec, RevisionInfo


class RevisionSpecThread(RevisionSpec):
    """The thread: revision specifier."""

    help_txt = """Selects the tip of a revision from a loom.

    Selects the tip of a thread in a loom.  

    Examples::

      thread:                   -> return the tip of the next lower thread.
      thread:foo                -> return the tip of the thread named 'foo'

    see also: loom
    """

    prefix = 'thread:'

    def _match_on(self, branch, revs):
        # '' -> next lower
        # foo -> named
        branch.lock_read()
        try:
            state = branch.get_loom_state()
            threads = state.get_threads()
            if len(self.spec):
                index = state.thread_index(self.spec)
            else:
                current_thread = branch.nick
                index = state.thread_index(current_thread) - 1
                if index < 0:
                    raise NoLowerThread()
            return RevisionInfo(branch, None, threads[index][1])
        finally:
            branch.unlock()


SPEC_TYPES.append(RevisionSpecThread)
