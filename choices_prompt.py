# choices_prompt
#
# Copyright (C) 2020 James D. Lin <jameslin@cal.berkeley.edu>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
Utility functions to facilitate prompting the user with a list of choices.
"""

import readline  # pylint: disable=unused-import  # noqa: F401  # Imported for side-effect.
import sys


class AbortError(Exception):
    """
    A simple exception class to abort program execution.

    If `cancelled` is True, no error message should be printed.
    """
    def __init__(self, message=None, cancelled=False, exit_code=1):
        super().__init__(message or ("Cancelled."
                                     if cancelled
                                     else "Unknown error"))
        assert exit_code != 0
        self.cancelled = cancelled
        self.exit_code = exit_code


def prompt(message, choices, default=None):
    """
    Prompts the user to choose from a list of choices.  Accepts any user input
    that unambiguously matches the start of one of the choices.  Matches are
    case-insensitive.

    Returns the selected choice.

    Raises an `AbortError` if the user cancels the prompt by sending EOF.
    """
    assert choices
    assert not default or default in choices
    choices = [(choice.strip().lower(), choice) for choice in choices]

    while True:
        try:
            response = input(message)
            response = (response.strip().lower(), response)
        except EOFError:
            print()
            raise AbortError(cancelled=True) from None

        if not response[0]:
            if default:
                return default
            continue

        selected_choices = []
        for choice in choices:
            if choice[0].startswith(response[0]):
                selected_choices.append(choice)

        if not selected_choices:
            print(f"Invalid choice: {response[1]}", file=sys.stderr)
        elif len(selected_choices) == 1:
            return selected_choices[0][1]
        else:
            print(f"Ambiguous choice: {response[1]}", file=sys.stderr)
