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

from __future__ import absolute_import

from breezy.plugins.loom.branch import NoLowerThread
from breezy.plugins.loom import require_loom_branch
from breezy.revisionspec import RevisionSpec, RevisionInfo


class LoomRevisionSpec(RevisionSpec):
    """A revision spec that needs a loom."""

    def _match_on(self, branch, revs):
         return RevisionInfo(branch, None, self._as_revision_id(branch))

    def _as_revision_id(self, branch):
        require_loom_branch(branch)
        branch.lock_read()
        try:
            state = branch.get_loom_state()
            threads = state.get_threads()
            return self._as_thread_revision_id(branch, state, threads)
        finally:
            branch.unlock()


class RevisionSpecBelow(LoomRevisionSpec):
    """The below: revision specifier."""

    help_txt = """Selects the tip of the thread below a thread from a loom.

    Selects the tip of the thread below a thread in a loom.  

    Examples::

      below:                   -> return the tip of the next lower thread.
      below:foo                -> return the tip of the thread under the one
                                  named 'foo'

    see also: loom, the thread: revision specifier
    """

    prefix = 'below:'

    def _as_thread_revision_id(self, branch, state, threads):
        # '' -> next lower
        # foo -> thread under foo
        if len(self.spec):
            index = state.thread_index(self.spec)
        else:
            current_thread = branch.nick
            index = state.thread_index(current_thread)
        if index < 1:
            raise NoLowerThread()
        return threads[index - 1][1]


class RevisionSpecThread(LoomRevisionSpec):
    """The thread: revision specifier."""

    help_txt = """Selects the tip of a thread from a loom.

    Selects the tip of a thread in a loom.  

    Examples::

      thread:                   -> return the tip of the next lower thread.
      thread:foo                -> return the tip of the thread named 'foo'

    see also: loom, the below: revision specifier
    """

    prefix = 'thread:'

    def _as_thread_revision_id(self, branch, state, threads):
        # '' -> next lower
        # foo -> named
        if len(self.spec):
            index = state.thread_index(self.spec)
        else:
            current_thread = branch.nick
            index = state.thread_index(current_thread) - 1
            if index < 0:
                raise NoLowerThread()
        return threads[index][1]



