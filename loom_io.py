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


"""Routines for reading and writing Looms in streams."""


import bzrlib.osutils


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
