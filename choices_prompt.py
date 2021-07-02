# choices_prompt
#
# Copyright (C) 2020-2021 James D. Lin <jameslin@cal.berkeley.edu>
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
Utility functions to facilitate prompting the user with a list of choices.
"""

import readline  # pylint: disable=unused-import  # noqa: F401  # Imported for side-effect.
import sys
import typing


def flush_input():
    """Clears pending input from `sys.stdin`."""
    internal_helper = getattr(flush_input, "internal_helper", None)
    if internal_helper is not None:
        internal_helper()
        return

    import importlib  # pylint: disable=import-outside-toplevel

    # For POSIX systems.
    try:
        termios = importlib.import_module("termios")
    except ModuleNotFoundError:
        pass
    else:
        def _internal_helper():
            termios.tcflush(sys.stdin, termios.TCIFLUSH)

        flush_input.internal_helper = _internal_helper
        _internal_helper()
        return

    # For Windows systems.
    try:
        msvcrt = importlib.import_module("msvcrt")
    except ModuleNotFoundError:
        pass
    else:
        def _internal_helper():
            while msvcrt.kbhit():
                msvcrt.getch()

        flush_input.internal_helper = _internal_helper
        _internal_helper()
        return


def choices_prompt(message: str, choices: typing.Iterable[str], *,
                   default: typing.Optional[str] = None) -> str:
    """
    Prompts the user to choose from a list of choices.  Accepts any user input
    that unambiguously matches the start of one of the choices.  Matches are
    case-insensitive.

    Returns the selected choice.

    Raises an `EOFError` if the user cancels the prompt by sending EOF.
    """
    assert choices
    assert not default or default in choices
    normalized_choices = [(choice.strip().lower(), choice)
                          for choice in choices]
    del choices

    while True:
        try:
            # Answering prompts with already-buffered input (particularly with
            # empty lines) is potentially dangerous, so disallow it.
            flush_input()
            raw_response = input(message)
            normalized_response = raw_response.strip().lower()
        except EOFError:
            print()
            raise

        if not normalized_response:
            if default:
                return default
            continue

        selected_choices: typing.List[typing.Tuple[str, str]] = []
        for choice in normalized_choices:
            if choice[0].startswith(normalized_response):
                selected_choices.append(choice)

        if not selected_choices:
            print(f"Invalid choice: {raw_response}", file=sys.stderr)
        elif len(selected_choices) == 1:
            return selected_choices[0][1]
        else:
            print(f"Ambiguous choice: {raw_response}", file=sys.stderr)
