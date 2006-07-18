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


"""Tests of the Loom parse and serialise routines."""


from cStringIO import StringIO

import bzrlib
import bzrlib.errors as errors
import bzrlib.osutils
import bzrlib.plugins.loom.loom_io as loom_io
import bzrlib.plugins.loom.loom_state as loom_state
from bzrlib.plugins.loom.tree import LoomTreeDecorator
import bzrlib.revision
from bzrlib.tests import TestCase


class TestLoomIO(TestCase):

    def test_writer_constructors(self):
        writer = loom_io.LoomWriter()
        state = loom_state.LoomState()
        writer = loom_io.LoomStateWriter(state)

    def assertWritesThreadsCorrectly(self, expected_stream, threads):
        """Write threads through a LoomWriter and check the output and sha1."""
        writer = loom_io.LoomWriter()
        stream = StringIO()
        expected_sha1 = bzrlib.osutils.sha_strings([expected_stream])
        self.assertEqual(expected_sha1, writer.write_threads(threads, stream))
        self.assertEqual(expected_stream, stream.getvalue())

    def test_write_empty_threads(self):
        self.assertWritesThreadsCorrectly('Loom meta 1\n', [])

    def test_write_threads(self):
        self.assertWritesThreadsCorrectly(
            'Loom meta 1\n'
            'null: baseline\n'
            'asdasdasdxxxrr not the baseline\n',
            [('baseline', bzrlib.revision.NULL_REVISION),
             ('not the baseline', 'asdasdasdxxxrr')],
            )

    def test_write_unicode_threads(self):
        self.assertWritesThreadsCorrectly(
            'Loom meta 1\n'
            'null: base\xc3\x9eline\n'
            'asd\xc3\xadasdasdxxxrr not the baseline\n',
            [(u'base\xdeline', bzrlib.revision.NULL_REVISION),
             ('not the baseline', u'asd\xedasdasdxxxrr')],
            )

    def assertWritesStateCorrectly(self, expected_stream, state):
        """Write state to a stream and check it against expected_stream."""
        writer = loom_io.LoomStateWriter(state)
        stream = StringIO()
        writer.write(stream)
        self.assertEqual(expected_stream, stream.getvalue())

    def test_write_empty_state(self):
        state = loom_state.LoomState()
        self.assertWritesStateCorrectly(
            loom_io._CURRENT_LOOM_FORMAT_STRING + '\n\n',
            state)

    def test_write_state_with_parent(self):
        state = loom_state.LoomState()
        state.set_parents(['1'])
        self.assertWritesStateCorrectly(
            loom_io._CURRENT_LOOM_FORMAT_STRING + '\n'
            '1\n',
            state)

    def test_write_state_with_parents(self):
        state = loom_state.LoomState()
        state.set_parents(['1', u'2\xeb'])
        self.assertWritesStateCorrectly(
            loom_io._CURRENT_LOOM_FORMAT_STRING + '\n'
            '1 2\xc3\xab\n',
            state)

    def test_write_state_with_threads(self):
        state = loom_state.LoomState()
        state.set_threads(
            [('base ', 'baserev', []),
             (u'\xedtop', u'\xe9toprev', []),
             ])
        self.assertWritesStateCorrectly(
            loom_io._CURRENT_LOOM_FORMAT_STRING + '\n'
            '\n'
            ' : baserev base \n'
            ' : \xc3\xa9toprev \xc3\xadtop\n',
            state)
        
    def test_write_state_with_threads_and_parents(self):
        state = loom_state.LoomState()
        state.set_threads(
            [('base ', 'baserev', [None, None]),
             (u'\xedtop', u'\xe9toprev', [None, None]),
             ])
        state.set_parents(['1', u'2\xeb'])
        self.assertWritesStateCorrectly(
            loom_io._CURRENT_LOOM_FORMAT_STRING + '\n'
            '1 2\xc3\xab\n'
            '   : baserev base \n'
            '   : \xc3\xa9toprev \xc3\xadtop\n',
            state)

    def assertReadState(self, parents, threads, state_stream):
        """Check that the state in stream can be read correctly."""
        state_reader = loom_io.LoomStateReader(state_stream)
        self.assertEqual(parents, state_reader.read_parents())
        self.assertEqual(threads, state_reader.read_thread_details())

    def test_read_state_empty(self):
        state_stream = StringIO(loom_io._CURRENT_LOOM_FORMAT_STRING + '\n\n')
        self.assertReadState([], [], state_stream)

    def test_read_state_no_parents_threads(self):
        state_stream = StringIO(
            loom_io._CURRENT_LOOM_FORMAT_STRING + '\n'
            '\n'
            ' : baserev base \n'
            ' : \xc3\xa9toprev \xc3\xadtop\n') # yes this is utf8
        self.assertReadState(
            [], 
            [('base ', 'baserev', []),
             (u'\xedtop', u'\xe9toprev', []),
             ],
            state_stream)
        
    def test_read_state_parents(self):
        state_stream = StringIO(
            loom_io._CURRENT_LOOM_FORMAT_STRING + '\n'
            '1 2\xc3\xab\n')
        self.assertReadState(
            ['1', u'2\xeb'],
            [],
            state_stream)

    def test_read_state_parents_threads(self):
        state_stream = StringIO(
            loom_io._CURRENT_LOOM_FORMAT_STRING + '\n'
            '1 2\xc3\xab\n'
            '   : baserev base \n'
            '   : \xc3\xa9toprev \xc3\xadtop\n') # yes this is utf8
        self.assertReadState(
            ['1', u'2\xeb'],
            [('base ', 'baserev', [None, None]),
             (u'\xedtop', u'\xe9toprev', [None, None]),
             ],
            state_stream)
