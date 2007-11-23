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

"""Loom specific revision-specifiers."""


from bzrlib.revisionspec import SPEC_TYPES, RevisionSpec, RevisionInfo


class RevisionSpecThread(RevisionSpec):
    """The thread: revision specifier.

    When used just as thread:, the next lower thread from the current thread
    is selected.
    """

    prefix = 'thread:'

    def _match_on(self, branch, revs):
        branch.lock_read()
        try:
            state = branch.get_loom_state()
            threads = state.get_threads()
            current_thread = branch.nick
            index = branch._thread_index(threads, current_thread)
            return RevisionInfo(branch, None, threads[index - 1][1])
        finally:
            branch.unlock()


SPEC_TYPES.append(RevisionSpecThread)
