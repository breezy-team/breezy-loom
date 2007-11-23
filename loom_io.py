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


"""Routines for reading and writing Looms in streams."""


import bzrlib.osutils


# The current format marker for serialised loom state.
# This belongs in a format object at some point.
_CURRENT_LOOM_FORMAT_STRING = "Loom current 1"

# the current loom format :
# first line is the format signature
# second line is the list of parents
# third line and beyond are the current threads.
# each thread line has one field for current status
# one field for each parent
# one field for the current revision id
# and then the rest of the line for the thread name.


class LoomWriter(object):
    """LoomWriter objects are used to serialise looms."""

    def write_threads(self, threads, stream):
        """Write threads to stream with a format header."""
        thread_content = 'Loom meta 1\n'
        for thread, rev_id in threads:
            thread_content += '%s %s\n' % (rev_id, thread)
        thread_content = thread_content.encode('utf8')
        stream.write(thread_content)
        return bzrlib.osutils.sha_strings([thread_content])


class LoomStateWriter(object):
    """LoomStateWriter objects are used to write out LoomState objects."""

    def __init__(self, state):
        """Initialise a LoomStateWriter with a state object.

        :param state: The LoomState object to be written out.
        """
        self._state = state

    def write(self, stream):
        """Write the state object to stream."""
        lines = [_CURRENT_LOOM_FORMAT_STRING + '\n']
        lines.append(' '.join(self._state.get_parents()) + '\n')
        # Note that we could possibly optimise our unicode handling here.
        for thread, rev_id, parents in self._state.get_threads():
            assert len(parents) == len(self._state.get_parents())
            # leading space for conflict status
            line = " "
            for parent in parents:
                if parent is not None:
                    line += "%s " % parent.decode('utf8')
                else:
                    line += " "
            line += ": "
            lines.append('%s%s %s\n' % (line, rev_id.decode('utf8'), thread))
        stream.write(''.join(lines).encode('utf8'))


class LoomStateReader(object):
    """LoomStateReaders are used to pull LoomState objects into memory."""

    def __init__(self, stream):
        """Initialise a LoomStateReader with a serialised loom-state stream.

        :param stream: The stream that contains a loom-state object. This 
            should allow relative seeking.
        """
        self._stream = stream
        self._content = None

    def _read(self):
        """Read the entire stream into memory.

        This is just a first approximation - eventually partial reads
        are desirable.
        """
        if self._content is None:
            # Names are unicode,revids are utf8 - it's arguable whether decode
            # all and encode revids, or vice verca is better.
            self._content = self._stream.read().decode('utf8').split('\n')
            # this is where detection of different formats should go.
            # we probably want either a  factory for readers, or a strategy
            # for the reader that is looked up on this format string.
            # either way, its in the future.
            assert self._content[0] == _CURRENT_LOOM_FORMAT_STRING 

    def read_parents(self):
        """Read the parents field from the stream.
        
        :return: a list of parent revision ids.
        """
        self._read()
        return self._content[1].encode('utf8').split()

    def read_thread_details(self):
        """Read the details for the threads.

        :return: a list of thread details. Each thread detail is a 3-tuple
            containing the thread name, the current thread revision, and a
            list of parent thread revisions, in the same order and length
            as the list returned by read_parents. In the parent thread 
            revision list, None means 'no present in the parent', and 
            'null:' means 'present but had no commits'.
        """
        result = []
        parent_count = len(self.read_parents())
        split_count = parent_count + 2
        # skip the format and parent lines, and the trailing \n line.
        for line in self._content[2:-1]:
            conflict_status, line = line.split(' ', 1)
            parents = []
            parent = ""
            while True:
                parent, line = line.split(' ', 1)
                if parent == ':':
                    break
                elif parent == '':
                    parents.append(None)
                else:
                    parents.append(parent.encode('utf8'))
            rev_id, name = line.split(' ', 1)
            result.append((name, rev_id.encode('utf8'), parents))
        return result
