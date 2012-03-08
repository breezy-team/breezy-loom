# Loom, a plugin for bzr to assist in developing focused patches.
# Copyright (C) 2010 Canonical Limited.
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

"""Versioning information for bzr-loom."""

from __future__ import absolute_import

__all__ = [
    'bzr_plugin_version',
    'bzr_minimum_version',
    'bzr_maximum_version',
    ]

bzr_plugin_version = (2, 3, 0, 'dev', 0)
bzr_minimum_version = (2, 4, 0)
bzr_maximum_version = None
