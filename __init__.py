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

"""Loom is a bzr plugin which adds new commands to manage a loom of patches.

The commands are:
 * loomify: This converts a branch into a loom enabled branch. As a result
   of this, the branch format is converted and you need to have the loom
   plugin installed to use it after that. The current branch nickname becomes
   the base thread in the loom.

 * create-thread: This adds a new thread to the loom with the supplied name
   and positions the branch on the new thrad.

 * show-loom: Shows the threads in the loom. It currently does not show the
   # of commits in each thread, but it is planned to do that in the future.

 * down-thread: Move the branch down a thread. After doing this commits and 
   merges in this branch will affect the newly selected thread.

 * up-thread: Move the branch up a thread. This will merge in all the changes
   from the current thread that are not yet integrated into the new thread into
   it and leave you ready to commit them.

"""


import bzrlib.commands

import branch
import commands


for command in [
    'create_thread',
    'down_thread',
    'loomify',
    'record',
    'show_loom',
    'up_thread',
    ]:
    bzrlib.commands.register_command(
        getattr(commands, 'cmd_' + command))


def test_suite():
    import bzrlib.plugins.loom.tests
    return bzrlib.plugins.loom.tests.test_suite()
