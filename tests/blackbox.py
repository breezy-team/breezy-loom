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


"""UI tests for loom."""


import bzrlib
from bzrlib.tests import TestCaseWithTransport


class TestLoomify(TestCaseWithTransport):

    def test_loomify_new_branch(self):
        b = self.make_branch('.')
        out, err = self.run_bzr('loomify', retcode=3)
        self.assertEqual('', out)
        self.assertEqual(
            'bzr: ERROR: You must have a branch nickname set to loomify a branch\n', 
            err)
        
    def test_loomify_new_branch_with_nick(self):
        b = self.make_branch('.')
        b.nick = 'base'
        out, err = self.run_bzr('loomify')
        # a loomed branch opens with a unique format
        b = bzrlib.branch.Branch.open('.')
        self.assertIsInstance(b, bzrlib.plugins.loom.branch.LoomBranch)
        threads = b.get_threads()
        self.assertEqual(
            [('base', bzrlib.revision.NULL_REVISION)], 
            threads)
