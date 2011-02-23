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

"""Format information about formats for Loom.

This is split out from the implementation of the formats to permit lazy
loading without requiring the implementation code to be cryptic.
"""

__all__ = [
    'NotALoom',
    'register_formats',
    'require_loom_branch',
    ]

from bzrlib.lazy_import import lazy_import
import bzrlib.errors

lazy_import(globals(), """
from bzrlib import branch as _mod_branch
""")


_LOOM_FORMATS = {
    "Bazaar-NG Loom branch format 1\n": "BzrBranchLoomFormat1",
    "Bazaar-NG Loom branch format 6\n": "BzrBranchLoomFormat6",
    "Bazaar-NG Loom branch format 7\n": "BzrBranchLoomFormat7",
    }

def register_formats():
    if getattr(_mod_branch, 'MetaDirBranchFormatFactory', None):
        branch_formats = [_mod_branch.MetaDirBranchFormatFactory(format_string,
            "bzrlib.plugins.loom.branch", format_class) for 
            (format_string, format_class) in _LOOM_FORMATS.iteritems()]
    else:
        # Compat for folk not running bleeding edge. Like me as I commit this.
        import branch
        branch_formats = [
            branch.BzrBranchLoomFormat1(),
            branch.BzrBranchLoomFormat6(),
            branch.BzrBranchLoomFormat7(),
            ]
    try:
        format_registry = getattr(_mod_branch, 'format_registry')
        register = format_registry.register
    except AttributeError: # bzr < 2.4
        register = _mod_branch.BranchFormat.register_format

    map(register, branch_formats)


def require_loom_branch(branch):
    """Return None if branch is already loomified, or raise NotALoom."""
    if branch._format.network_name() not in _LOOM_FORMATS:
        raise NotALoom(branch)


# TODO: define errors without importing all errors.
class NotALoom(bzrlib.errors.BzrError):

    _fmt = ("The branch %(branch)s is not a loom. "
        "You can use 'bzr loomify' to make it into a loom.")

    def __init__(self, branch):
        bzrlib.errors.BzrError.__init__(self)
        self.branch = branch
