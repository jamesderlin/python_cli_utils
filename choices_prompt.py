# choices_prompt
#
# Copyright (C) 2020-2021 James D. Lin <jamesdlin@berkeley.edu>
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


def flush_input() -> None:
    """Clears pending input from `sys.stdin`."""
    internal_helper = getattr(flush_input, "internal_helper", None)
    if internal_helper is not None:
        internal_helper()
        return

    import importlib  # pylint: disable=import-outside-toplevel

    # For POSIX systems.
    try:
        termios: typing.Any = importlib.import_module("termios")
    except ModuleNotFoundError:
        pass
    else:
        def _internal_helper() -> None:
            termios.tcflush(sys.stdin, termios.TCIFLUSH)

        flush_input.internal_helper = _internal_helper  # type: ignore
        _internal_helper()
        return

    # For Windows systems.
    try:
        msvcrt: typing.Any = importlib.import_module("msvcrt")
    except ModuleNotFoundError:
        pass
    else:
        def _internal_helper() -> None:
            while msvcrt.kbhit():
                msvcrt.getch()

        flush_input.internal_helper = _internal_helper  # type: ignore
        _internal_helper()
        return


def choices_prompt(
    prompt: str,
    choices: typing.Union[typing.Collection[str],
                          typing.Collection[typing.Sequence[str]]],
    *,
    default: typing.Optional[str] = None,
    invalid_handler: typing.Optional[typing.Callable[[str], str]] = None,
    file: typing.Optional[typing.TextIO] = None,
) -> typing.Optional[str]:
    """
    Prompts the user to choose from a fixed list of choices.

    `prompt` specifies the string to print when prompting for input.

    `choices` must be an iterable where each element is either a single string
    or a tuple of strings.  Each tuple consists of acceptable inputs for a
    single choice.

    Returns a string indicating the selected choice.  If the choice corresponds
    to a tuple, the first element of the chosen tuple is considered canonical
    and will be returned.

    Returns `None` if the user enters EOF to exit the prompt or if `choices` is
    empty.

    Choice selection is case-insensitive but case-preserving.  That is, an
    available choice of `"Yes"` will match against input of `"YES"`, and
    `"Yes"` will be returned.  Leading and trailing whitespace is ignored.

    `default` specifies the default value to return if the user accepts the
    prompt with empty input (an empty string or a string consisting entirely of
    whitespace). `default` must be either be `None` or a string in `choices`.
    If `None`, the user will be required to provide valid, non-empty input (or
    enter EOF) to exit the prompt.

    If the user enters an invalid choice, `invalid_handler` will be called with
    the invalid input and should return an appropriate error message.  If
    `invalid_handler` is `None`, a default error message will be generated.
    `invalid_handler` can be used to provide more details about what legal
    inputs are.

    `file` specifies the output stream to print to.  If not specified, defaults
    to `sys.stdout`.

    Example:
    ```python
    response = choices_prompt("Continue? (y/N) ",
                              (("y", "yes"), ("n", "no")),
                              default="n")
    if response is None:
        raise AbortError(cancelled=True)
    if response == "y":
        # ...
    else:
        assert response == "n"
        # ...
    ```
    """
    def normalize_choice_str(s: str) -> str:
        """
        Helper function to transform a choice string to a standard
        representation for easier comparison later.
        """
        assert isinstance(s, str)
        return s.strip().casefold()

    if not choices:
        return None

    # Transform top-level elements that are single strings to be one-element
    # tuples.
    choices = [(choice,) if isinstance(choice, str) else choice
               for choice in choices]

    choices_table = {
        normalize_choice_str(choice_str): choice_tuple[0]
        for choice_tuple in choices
        for choice_str in choice_tuple
    }

    if default is not None:
        default = normalize_choice_str(default)
        assert default in choices_table

    def default_invalid_handler(response: str) -> str:
        return f"\"{response}\" is not a valid choice."

    invalid_handler = invalid_handler or default_invalid_handler
    file = file or sys.stdout

    while True:
        try:
            # Answering prompts with already-buffered input (particularly with
            # empty lines) is potentially dangerous, so disallow it.
            flush_input()
            try:
                # `input` always writes to `sys.stdout`; temporarily redirect
                # its output.
                old_stdout = sys.stdout
                sys.stdout = file
                raw_response = input(prompt)
            finally:
                sys.stdout = old_stdout

            normalized_response = normalize_choice_str(raw_response)
        except EOFError:
            print(file=file)
            return None

        if not normalized_response:
            if default is None:
                continue
            return choices_table[default]

        try:
            return choices_table[normalized_response]
        except KeyError:
            print(invalid_handler(raw_response), file=file)

        print(file=file)


def numbered_choices_prompt(
    choices: typing.Collection[str],
    *,
    default_index: typing.Optional[int] = None,
    preamble: str = "",
    prompt: typing.Optional[str] = None,
    item_formatter: typing.Optional[typing.Callable[[str], str]] = None,
    file: typing.Optional[typing.TextIO] = None,
) -> typing.Optional[int]:
    """
    Prompts the user to choose from a potentially variable list of choices.
    `numbered_choices_prompt` is more suitable than `choices_prompt` for cases
    where the choices are not known until runtime.

    Returns the (zero-based) index of the selected choice.  If there is only
    one choice, returns 0 without prompting.

    Returns `None` if the user cancels, quits the prompt, or if `choices` is
    empty.

    `default_index` specifies the (zero-based) index of the choice to use as
    the default if the user accepts the prompt with empty input (an empty
    string or a string consisting entirely of whitespace).

    `prompt` specifies the string to print whenever the user is prompted for
    input.  If `None`, a default prompt strng will be generated automatically.

    `preamble` specifies a string to print before the list of choices is
    printed. `preamble` and the list of choices are printed before the initial
    prompt and whenever the user explicitly requests them by entering `"help"`.

    `file` specifies the output stream to print to.  If not specified, defaults
    to `sys.stdout`.
    """
    if not choices:
        return None

    max_choice = len(choices)
    if max_choice == 1:
        # If there's only one choice, don't bother prompting.
        return 0

    assert (default_index is None) or (0 <= default_index < max_choice)

    def identity(x: typing.Any) -> typing.Any:
        return x

    item_formatter = item_formatter or identity
    file = file or sys.stdout

    instructions = "\n".join([
        *((preamble,) if preamble else ()),
        *(item_formatter(f"  {i}: {choice}")
          for (i, choice) in enumerate(choices, 1)),
    ])

    print(instructions, file=file)

    default_hint = "" if default_index is None else f"[{default_index + 1}] "
    default_prompt = (f"[1, 2]: {default_hint}" if max_choice == 2 else
                      f"[1..{max_choice}]: {default_hint}")
    prompt = f"{prompt} {default_prompt}" if prompt else default_prompt

    allowed_inputs = \
        ([typing.cast(typing.Sequence[str], (str(i + 1),))
         for i in range(max_choice)]
         + [("?", "h", "help"), ("q", "quit")])

    def invalid_handler(response: str) -> str:
        return (f"\"{response}\" is not a valid choice.\n"
                f"The entered choice must be between 1 and {max_choice}, "
                f"inclusive.\n"
                f"Enter \"help\" to show the choices again or \"quit\" to "
                f"quit.")

    while True:
        response = choices_prompt(
            prompt,
            allowed_inputs,
            default=None if default_index is None else str(default_index + 1),
            file=file,
            invalid_handler=invalid_handler)
        if response is None or response == "q":
            return None

        if response == "?":
            print(file=file)
            print(instructions, file=file)
            continue

        choice = int(response)
        assert 1 <= choice <= max_choice
        return choice - 1
