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

from __future__ import absolute_import

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


Loom also adds new revision specifiers 'thread:' and 'below:'. You can use these
to diff against threads in the current Loom. For instance, 'bzr diff -r
thread:' will show you the different between the thread below yours, and your
thread. See ``bzr help revisionspec`` for the detailed help on these two
revision specifiers.
"""

from bzrlib.plugins.loom.version import (
    bzr_plugin_version as version_info,
    bzr_minimum_version,
    )

import bzrlib
import bzrlib.api

bzrlib.api.require_api(bzrlib, bzr_minimum_version)

import bzrlib.builtins
import bzrlib.commands

from bzrlib.plugins.loom import (
    commands,
    formats,
    )


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

# XXX: bzr fix needed: for switch, we have to register directly, not
# lazily, because register_lazy does not stack in the same way register_command
# does.
if not hasattr(bzrlib.builtins, "cmd_switch"):
    # provide a switch command (allows 
    bzrlib.commands.register_command(getattr(commands, 'cmd_switch'))
else:
    commands.cmd_switch._original_command = bzrlib.commands.register_command(
        getattr(commands, 'cmd_switch'), True)

from bzrlib.hooks import install_lazy_named_hook
def show_loom_summary(params):
    branch = getattr(params.new_tree, "branch", None)
    if branch is None:
        # Not a working tree, ignore
        return
    try:
        formats.require_loom_branch(branch)
    except formats.NotALoom:
        return
    params.to_file.write('Current thread: %s\n' % branch.nick)

install_lazy_named_hook('bzrlib.status', 'hooks', 'post_status',
    show_loom_summary, 'loom status')

from bzrlib.revisionspec import revspec_registry
revspec_registry.register_lazy('thread:', 'bzrlib.plugins.loom.revspec',
                               'RevisionSpecThread')
revspec_registry.register_lazy('below:', 'bzrlib.plugins.loom.revspec',
                               'RevisionSpecBelow')

#register loom formats
formats.register_formats()

def test_suite():
    import bzrlib.plugins.loom.tests
    return bzrlib.plugins.loom.tests.test_suite()
