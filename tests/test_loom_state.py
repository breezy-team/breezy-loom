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


"""Tests of the Loom current-state object."""


from cStringIO import StringIO

import bzrlib
import bzrlib.errors as errors
import bzrlib.osutils
import bzrlib.plugins.loom.loom_state as loom_state
from bzrlib.plugins.loom.tree import LoomTreeDecorator
import bzrlib.revision
from bzrlib.tests import TestCase


class TestLoomState(TestCase):

    def test_constructor(self):
        state = loom_state.LoomState()
        # the default object must have no parents and no threads.
        self.assertEqual([], state.get_parents())
        self.assertEqual([], state.get_threads())
        self.assertEqual([], state.get_basis_threads())

    def test_set_get_threads(self):
        state = loom_state.LoomState()
        sample_threads = [('foo', 'bar'), (u'g\xbe', 'bar')]
        state.set_threads(sample_threads)
        self.assertEqual([], state.get_parents())
        self.assertEqual([], state.get_basis_threads())
        self.assertEqual(sample_threads, state.get_threads())
        sample_threads.append('foo')
        self.assertNotEqual(sample_threads, state.get_threads())

    def test_set_get_parents(self):
        state = loom_state.LoomState()
        sample_threads = [('foo', 'bar')]
        state.set_threads(sample_threads)
        # can set parents to nothing with no side effects
        state.set_parents([])
        self.assertEqual([], state.get_parents())
        self.assertEqual([], state.get_basis_threads())
        self.assertEqual(sample_threads, state.get_threads())
        # can set a single parent with no threads
        state.set_parents([('foo', [])])
        self.assertEqual(['foo'], state.get_parents())
        self.assertEqual([], state.get_basis_threads())
        self.assertEqual(sample_threads, state.get_threads())
        # can set a single parent with threads
        state.set_parents([('bar', [('name', 'rev')])])
        self.assertEqual(['bar'], state.get_parents())
        self.assertEqual([('name', 'rev')], state.get_basis_threads())
        self.assertEqual(sample_threads, state.get_threads())
        # can set multiple parents
        state.set_parents(
            [('bar', [('name', 'rev')]),
             (' am', [('zaphod', 'wasapreachere')]),
             ])
        self.assertEqual(['bar', ' am'], state.get_parents())
        self.assertEqual([('name', 'rev')], state.get_basis_threads())
        self.assertEqual(sample_threads, state.get_threads())
