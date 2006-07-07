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
from bzrlib.plugins.loom.tree import LoomTreeDecorator
import bzrlib.revision
from bzrlib.tests import TestCase


class TestLoomIO(TestCase):

    def test_writer_constructors(self):
        writer = loom_io.LoomWriter()

    def assertWritesCorrectly(self, expected_stream, threads):
        """Write threads through a LoomWriter and check the output and sha1."""
        writer = loom_io.LoomWriter()
        stream = StringIO()
        expected_sha1 = bzrlib.osutils.sha_strings([expected_stream])
        self.assertEqual(expected_sha1, writer.write_threads(threads, stream))
        self.assertEqual(expected_stream, stream.getvalue())

    def test_write_empty_threads(self):
        self.assertWritesCorrectly('Loom meta 1\n', [])

    def test_write_threads(self):
        self.assertWritesCorrectly(
            'Loom meta 1\n'
            'null: baseline\n'
            'asdasdasdxxxrr not the baseline\n',
            [('baseline', bzrlib.revision.NULL_REVISION),
             ('not the baseline', 'asdasdasdxxxrr')],
            )

    def test_write_unicode_threads(self):
        self.assertWritesCorrectly(
            'Loom meta 1\n'
            'null: base\xc3\x9eline\n'
            'asd\xc3\xadasdasdxxxrr not the baseline\n',
            [(u'base\xdeline', bzrlib.revision.NULL_REVISION),
             ('not the baseline', u'asd\xedasdasdxxxrr')],
            )

