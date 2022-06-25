# tty_utils
#
# Copyright (C) 2022 James D. Lin <jamesdlin@berkeley.edu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 2 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Miscellaneous utility functions for interactive terminals.
"""

import math
import os
import shutil
import sys


def terminal_size() -> os.terminal_size:
    """
    Returns the terminal size.

    Returns `(math.inf, math.inf)` if stdout is not a TTY.
    """
    if not sys.stdout.isatty():
        return os.terminal_size((math.inf, math.inf))  # type: ignore
    return shutil.get_terminal_size()


def ellipsize(s: str, width: int) -> str:
    """
    Truncates a string to the specified maximum width (in code points).

    The maximum width includes the added ellipsis if the string is truncated.

    `width` must be a positive integer.

    Unlike `textwrap.shorten`, leaves whitespace alone.
    """
    assert width > 0
    if len(s) <= width:
        return s

    ellipsis = "..."
    if width < len(ellipsis):
        return s[:width]

    s = s[:(width - len(ellipsis))] + ellipsis
    assert len(s) == width
    return s
