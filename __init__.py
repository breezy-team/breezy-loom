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

"""Loom is a bzr plugin which adds new commands to manage a loom of patches.

Loom adds the following new commands:
 * loomify: This converts a branch into a loom enabled branch. As a result
   of this, the branch format is converted and you need to have the loom
   plugin installed to use it after that. The current branch nickname becomes
   the base thread in the loom.

 * create-thread: This adds a new thread to the loom with the supplied name
   and positions the branch on the new thread.

 * record: Perform a commit of the loom - record the current stack of patches
   into history, allowing it to be pushed, pulled and merged.

 * revert-loom: Revert all change in the current stack of patches to the last
   recorded one.

 * show-loom: Shows the threads in the loom. It currently does not show the
   # of commits in each thread, but it is planned to do that in the future.

 * down-thread: Move the branch down a thread. After doing this commits and 
   merges in this branch will affect the newly selected thread.

 * up-thread: Move the branch up a thread. This will merge in all the changes
   from the current thread that are not yet integrated into the new thread into
   it and leave you ready to commit them.

 * combine-thread: Combine the current thread with the thread below it. If
   It is the last thread, this will currently refuse to operate, but in the
   future will just turn the loom into a normal branch again. Use this command
   to remove a thread which has been merged into upstream. 


Loom also adds a new revision specifier 'thread:'. You can use this to diff
against threads in the current Loom. For instance, 'bzr diff -r thread:' will
show you the different between the thread below yours, and your thread.
"""

version_info = (2, 1, 1, 'dev', 0)

import bzrlib.builtins
import bzrlib.commands
import bzrlib.revisionspec

import commands
import formats


for command in [
    'combine_thread',
    'create_thread',
    'down_thread',
    'export_loom',
    'loomify',
    'record',
    'revert_loom',
    'show_loom',
    'up_thread',
    ]:
    bzrlib.commands.plugin_cmds.register_lazy('cmd_' + command, [],
        'bzrlib.plugins.loom.commands')

# XXX: bzr fix needed: for status and switch, we have to register directly, not
# lazily, because register_lazy does not stack in the same way register_command
# does.
if not hasattr(bzrlib.builtins, "cmd_switch"):
    # provide a switch command (allows 
    bzrlib.commands.register_command(getattr(commands, 'cmd_switch'))
else:
    commands.cmd_switch._original_command = bzrlib.commands.register_command(
        getattr(commands, 'cmd_switch'), True)

commands.cmd_status._original_command = bzrlib.commands.register_command(
    commands.cmd_status, True)

revspec_registry = getattr(bzrlib.revisionspec, 'revspec_registry', None)
if revspec_registry is not None:
    revspec_registry.register_lazy('thread:', 'bzrlib.plugins.loom.revspec',
                                   'RevisionSpecThread')
else:
    import revspec
    bzrlib.revisionspec.SPEC_TYPES.append(revspec.RevisionSpecThread)

#register loom formats
formats.register_formats()

def test_suite():
    import bzrlib.plugins.loom.tests
    return bzrlib.plugins.loom.tests.test_suite()
