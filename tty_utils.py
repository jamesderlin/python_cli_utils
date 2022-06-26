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

import contextlib
import math
import os
import shutil
import subprocess
import sys
import typing


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


__current_paged_output_proc: typing.Optional[subprocess.Popen] = None


@contextlib.contextmanager
def paged_output(
    pager: typing.Optional[str] = None,
) -> typing.Generator[typing.IO[typing.Any], None, None]:
    """
    Context manager that spawns the user's pager.  Writes to the yielded stream
    will be sent through the pager.

    Does nothing if `sys.stdout` is not a TTY.

    If no pager is explicitly specified, the pager is determined from the
    `PAGER` environment variable.  If `PAGER` is not specified, defaults to
    `less` and then to `more` from the executable search path.

    Examples:
    ```python
    with paged_output() as out:
        for i in range(100):
            print(i, file=out)
        out.flush()

        subprocess.run(command, stdout=out)

    # Or combine with `contextlib.redirect_stdout`:
    with paged_output() as paged:
        with contextlib.redirect_stdout(paged):
            for i in range(100):
                print(i)
            sys.stdout.flush()

            # Spawned processes will use the original `stdout`, not the current
            # stream referred to by `sys.stdout`, so it still must be specified
            # explicitly.
            subprocess.run(command, stdout=sys.stdout)
    ```
    """
    # Paging is appropriate only for interactive terminals.
    if not sys.stdout.isatty():
        yield sys.stdout
        return

    # Don't spawn multiple pager processes if we're already within a
    # `pager_output` context.
    global __current_paged_output_proc
    if __current_paged_output_proc is not None:
        assert __current_paged_output_proc.stdin is not None
        yield __current_paged_output_proc.stdin
        return

    pager = (pager
             or os.environ.get("PAGER")
             or shutil.which("less")
             or shutil.which("more"))
    if not pager:
        yield sys.stdout
        return

    with subprocess.Popen((pager,),
                          stdin=subprocess.PIPE,
                          universal_newlines=True) as proc:
        __current_paged_output_proc = proc
        assert proc.stdin is not None
        try:
            yield proc.stdin
        finally:
            __current_paged_output_proc = None
