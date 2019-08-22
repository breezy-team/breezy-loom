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

from breezy.plugins.loom.version import (
    brz_minimum_version,
    )

from breezy import version_info as breezy_version_info

if brz_minimum_version > breezy_version_info:
    raise Exception('Breezy version too old')

from breezy import branch as _mod_branch
import breezy.builtins
import breezy.commands

from breezy.plugins.loom import (
    commands,
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
    breezy.commands.plugin_cmds.register_lazy('cmd_' + command, [],
        'breezy.plugins.loom.commands')

# XXX: bzr fix needed: for switch, we have to register directly, not
# lazily, because register_lazy does not stack in the same way register_command
# does.
if not hasattr(breezy.builtins, "cmd_switch"):
    # provide a switch command (allows 
    breezy.commands.register_command(getattr(commands, 'cmd_switch'))
else:
    commands.cmd_switch._original_command = breezy.commands.register_command(
        getattr(commands, 'cmd_switch'), True)

from breezy.hooks import install_lazy_named_hook
def show_loom_summary(params):
    branch = getattr(params.new_tree, "branch", None)
    if branch is None:
        # Not a working tree, ignore
        return
    try:
        require_loom_branch(branch)
    except NotALoom:
        return
    params.to_file.write('Current thread: %s\n' % branch.nick)

install_lazy_named_hook('breezy.status', 'hooks', 'post_status',
    show_loom_summary, 'loom status')

try:
    from breezy.registry import register_lazy
except ImportError: # bzr < 2.6
    from breezy.revisionspec import revspec_registry
    revspec_registry.register_lazy('thread:', 'breezy.plugins.loom.revspec',
                                   'RevisionSpecThread')
    revspec_registry.register_lazy('below:', 'breezy.plugins.loom.revspec',
                                   'RevisionSpecBelow')
else:
    register_lazy("breezy.revisionspec", "revspec_registry", 'thread:',
            'breezy.plugins.loom.revspec', 'RevisionSpecThread')
    register_lazy("breezy.revisionspec", "revspec_registry", 'below:',
            'breezy.plugins.loom.revspec', 'RevisionSpecBelow')

_LOOM_FORMATS = {
    b"Bazaar-NG Loom branch format 1\n": "BzrBranchLoomFormat1",
    b"Bazaar-NG Loom branch format 6\n": "BzrBranchLoomFormat6",
    b"Bazaar-NG Loom branch format 7\n": "BzrBranchLoomFormat7",
    }


def register_formats():
    for format_string, kls in _LOOM_FORMATS.items():
        _mod_branch.format_registry.register_lazy(format_string,
                "breezy.plugins.loom.branch", kls)


def require_loom_branch(branch):
    """Return None if branch is already loomified, or raise NotALoom."""
    if branch._format.network_name() not in _LOOM_FORMATS:
        raise NotALoom(branch)


# TODO: define errors without importing all errors.
class NotALoom(breezy.errors.BzrError):

    _fmt = ("The branch %(branch)s is not a loom. "
        "You can use 'bzr loomify' to make it into a loom.")

    def __init__(self, branch):
        breezy.errors.BzrError.__init__(self)
        self.branch = branch

#register loom formats
register_formats()

def test_suite():
    import breezy.plugins.loom.tests
    return breezy.plugins.loom.tests.test_suite()
