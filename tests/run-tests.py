#!/usr/bin/env python3

"""Unit tests for python_cli_utils."""

import contextlib
import dataclasses
import io
import re
import sys
import typing
import unittest
import unittest.mock

import choices_prompt


whitespace = re.compile(r"\s+")


def fake_flush_input(*_args: typing.Any, **_kwargs: typing.Any) -> None:
    """
    Fake implementation for `choices_prompt.flush_input` that does nothing.
    """


def read_contents(f: typing.TextIO) -> str:
    """Returns the full contents of a `TextIO` stream."""
    f.seek(0)
    return f.read()


@dataclasses.dataclass
class MockedIO:
    """
    Data class returned by `mock_io` that stores mocked versions of
    `sys.stdout` and `sys.stderr`.
    """
    stdout: typing.TextIO
    stderr: typing.TextIO


@contextlib.contextmanager
def mock_io(*, input: str = "") -> typing.Iterator[MockedIO]:  # pylint: disable=redefined-builtin
    """
    Context manager that sets up mocked versions of `sys.stdin` (with the
    specified input), `sys.stdout`, and `sys.stderr`.
    """
    with unittest.mock.patch("sys.stdin",
                             new_callable=io.StringIO) as mock_stdin, \
         unittest.mock.patch("sys.stdout",
                             new_callable=io.StringIO) as mock_stdout, \
         unittest.mock.patch("sys.stderr",
                             new_callable=io.StringIO) as mock_stderr, \
         unittest.mock.patch("choices_prompt.flush_input", fake_flush_input):

        if input:
            mock_stdin.write(input)
            mock_stdin.seek(0)

        yield MockedIO(stdout=mock_stdout, stderr=mock_stderr)


def expect_test_choices(
    test_case: unittest.TestCase,
    prompt: str,
    choices: typing.Union[typing.Collection[str],
                          typing.Collection[typing.Sequence[str]]],
    *,
    default: typing.Optional[str] = None,
    input: str = "",  # pylint: disable=redefined-builtin
    expected_response: typing.Optional[str],
    expected_stdout: typing.Optional[str] = None,
    expected_stderr: str = "",
) -> None:
    """
    Verifies the typical behavior of `choices_prompt.choices_prompt`, setting
    up necessary mocks.
    """
    response: typing.Optional[str] = None

    if expected_stdout is None:
        expected_stdout = prompt

    with mock_io(input=input) as mocked_io:
        response = choices_prompt.choices_prompt(prompt=prompt,
                                                 choices=choices,
                                                 default=default)
        if response is None:
            expected_stdout += "\n"

    test_case.assertEqual(response, expected_response)

    test_case.assertEqual(read_contents(mocked_io.stdout), expected_stdout)
    test_case.assertEqual(read_contents(mocked_io.stderr), expected_stderr)


class TestChoicesPrompt(unittest.TestCase):
    """Tests `choices_prompt.choices_prompt`."""
    def test_basic_input(self) -> None:
        """Tests that entered choices are returned."""
        expect_test_choices(self,
                            "Test message? ",
                            ("Foo", "Bar", "Baz"),
                            input="Foo\n",
                            expected_response="Foo")
        expect_test_choices(self,
                            "Test message? ",
                            ("Foo", "Bar", "Baz"),
                            input="Bar\n",
                            expected_response="Bar")
        expect_test_choices(self,
                            "Test message? ",
                            ("Foo", "Bar", "Baz"),
                            input="Baz\n",
                            expected_response="Baz")

    def test_case_insensitivity(self) -> None:
        """Tests that entered choices are matched case-insensitively."""
        expect_test_choices(self,
                            "Test message? ",
                            ("Foo", "Bar", "Baz"),
                            input="foo\n",
                            expected_response="Foo")
        expect_test_choices(self,
                            "Test message? ",
                            ("Foo", "Bar", "Baz"),
                            input="FOO\n",
                            expected_response="Foo")

    def test_whitespace_input(self) -> None:
        """
        Tests that leading and trailing whitespace is ignored from choices.
        """
        expect_test_choices(self,
                            "Test message? ",
                            ("Foo", "Bar", "Baz"),
                            input=" foo \n",
                            expected_response="Foo")
        expect_test_choices(self,
                            "Test message? ",
                            (" Foo ", "Bar", "Baz"),
                            input="foo\n",
                            expected_response=" Foo ")

    def test_canonical_responses(self) -> None:
        """Tests that the canonical response is returned."""
        expect_test_choices(self,
                            "Test message? ",
                            (("f", "Foo"), ("Bar",), ("Baz",)),
                            input="Foo\n",
                            expected_response="f")
        expect_test_choices(self,
                            "Test message? ",
                            (("f", "Foo"), ("Bar",), ("Baz",)),
                            input="f\n",
                            expected_response="f")
        expect_test_choices(self,
                            "Test message? ",
                            (("f", "Foo"), ("Bar",), ("Baz",)),
                            input="foo\n",
                            expected_response="f")

    def test_default_input(self) -> None:
        """
        Tests that the default choice is returned if an empty line is entered.
        """
        expect_test_choices(self,
                            "Test message? ",
                            ("Foo", "Bar", "Baz"),
                            default="Foo",
                            input="\n",
                            expected_response="Foo")
        expect_test_choices(self,
                            "Test message? ",
                            ("Foo", "Bar", "Baz"),
                            default="Foo",
                            input=" \n",
                            expected_response="Foo")
        expect_test_choices(self,
                            "Test message? ",
                            ("Foo", "Bar", "Baz"),
                            default="foo",
                            input="\n",
                            expected_response="Foo")

    def test_no_default(self) -> None:
        """
        Tests that the prompt is repeated if an empty line is entered with no
        default.
        """
        prompt = "Test message? "
        expect_test_choices(
            self,
            prompt,
            ("Foo", "Bar", "Baz"),
            input="\n\n",
            expected_stdout=prompt * 3,
            expected_response=None,
        )

    def test_eof(self) -> None:
        """Tests that `None` is returned if there is no input."""
        expect_test_choices(self,
                            "Test message? ",
                            ("Foo", "Bar", "Baz"),
                            input="",
                            expected_response=None)

    def test_invalid_input(self) -> None:
        """
        Tests that the prompt is repeated with an appropriate error message if
        invalid input is entered.
        """
        expect_test_choices(
            self,
            "Test message? ",
            ("Foo", "Bar", "Baz"),
            input="qux",
            expected_stdout="Test message? "
                            "\"qux\" is not a valid choice.\n"
                            "\n"
                            "Test message? ",
            expected_response=None,
        )

        expect_test_choices(
            self,
            "Test message? ",
            (("f", "Foo"), ("Bar",), ("Baz",)),
            input="fo",
            expected_stdout="Test message? "
                            "\"fo\" is not a valid choice.\n"
                            "\n"
                            "Test message? ",
            expected_response=None,
        )

    def test_invalid_default(self) -> None:
        """Tests that the default value must match one of the choices."""
        with mock_io():
            self.assertRaises(AssertionError,
                              choices_prompt.choices_prompt,
                              prompt="Test message? ",
                              choices=("Foo", "Bar", "Baz"),
                              default="qux")

    def test_no_choices(self) -> None:
        """
        Tests that no prompt is printed and `None` is returned if choices is
        empty.
        """
        with mock_io() as mocked_io:
            response = choices_prompt.choices_prompt("Test message? ", ())
            self.assertIs(response, None)
            self.assertFalse(read_contents(mocked_io.stdout))
            self.assertFalse(read_contents(mocked_io.stderr))


class TestNumberedChoicesPrompt(unittest.TestCase):
    """Tests `choices_prompt.numbered_choices_prompt`."""
    def test_instructions(self) -> None:
        """Tests that instructions and choices are printed."""
        with mock_io(input="1\n") as mocked_io:
            response = choices_prompt.numbered_choices_prompt(
                ("foo", "bar", "baz"),
                preamble="Instructions",
                prompt="Choose wisely",
            )
            self.assertEqual(response, 0)
            self.assertEqual(read_contents(mocked_io.stdout),
                             "Instructions\n"
                             "  1: foo\n"
                             "  2: bar\n"
                             "  3: baz\n"
                             "Choose wisely [1..3]: ")
            self.assertEqual(read_contents(mocked_io.stderr), "")

    def test_default_prompt(self) -> None:
        """Tests the default prompt."""
        with mock_io(input="2\n") as mocked_io:
            response = choices_prompt.numbered_choices_prompt(
                ("foo", "bar", "baz"),
            )
            self.assertEqual(response, 1)
            self.assertEqual(read_contents(mocked_io.stdout),
                             "  1: foo\n"
                             "  2: bar\n"
                             "  3: baz\n"
                             "[1..3]: ")
            self.assertEqual(read_contents(mocked_io.stderr), "")

    def test_no_choices(self) -> None:
        """Tests that nothing is printed if there are no choices."""
        with mock_io() as mocked_io:
            response = choices_prompt.numbered_choices_prompt(())
            self.assertIs(response, None)
            self.assertEqual(read_contents(mocked_io.stdout), "")
            self.assertEqual(read_contents(mocked_io.stderr), "")

    def test_one_choice(self) -> None:
        """
        Tests a single choice is automatically returned with nothing printed.
        """
        with mock_io() as mocked_io:
            response = choices_prompt.numbered_choices_prompt(("foo",))
            self.assertEqual(response, 0)
            self.assertEqual(read_contents(mocked_io.stdout), "")
            self.assertEqual(read_contents(mocked_io.stderr), "")

    def test_default_index(self) -> None:
        """Tests the `default index` parameter."""
        with mock_io(input="\n") as mocked_io:
            response = choices_prompt.numbered_choices_prompt(
                ("foo", "bar", "baz"),
                default_index=0,
            )
            self.assertEqual(response, 0)
            self.assertEqual(read_contents(mocked_io.stdout),
                             "  1: foo\n"
                             "  2: bar\n"
                             "  3: baz\n"
                             "[1..3]: [1] ")
            self.assertEqual(read_contents(mocked_io.stderr), "")

    def test_invalid_input(self) -> None:
        """
        Tests that the prompt is repeated with an appropriate error message if
        invalid input is entered.
        """
        choices = ("foo", "bar", "baz")
        preamble = "Instructions"

        test_input = "0\nx\nhelp\nquit\n"
        expected_output = (
            "Instructions\n"
            "  1: foo\n"
            "  2: bar\n"
            "  3: baz\n"
            "[1..3]: "
            "\"0\" is not a valid choice.\n"
            "The entered choice must be between 1 and 3, inclusive.\n"
            "Enter \"help\" to show the choices again or \"quit\" to quit.\n"
            "\n"
            "[1..3]: "
            "\"x\" is not a valid choice.\n"
            "The entered choice must be between 1 and 3, inclusive.\n"
            "Enter \"help\" to show the choices again or \"quit\" to quit.\n"
            "\n"
            "[1..3]: \n"
            "Instructions\n"
            "  1: foo\n"
            "  2: bar\n"
            "  3: baz\n"
            "[1..3]: "
        )

        with mock_io(input=test_input) as mocked_io:
            response = choices_prompt.numbered_choices_prompt(
                choices,
                preamble=preamble,
            )
            self.assertIs(response, None)
            self.assertEqual(read_contents(mocked_io.stdout), expected_output)
            self.assertEqual(read_contents(mocked_io.stderr), "")

        # Test that all output can be sent to `sys.stderr` instead.
        with mock_io(input=test_input) as mocked_io:
            response = choices_prompt.numbered_choices_prompt(
                choices,
                preamble=preamble,
                file=sys.stderr
            )
            self.assertIs(response, None)
            self.assertEqual(read_contents(mocked_io.stdout), "")
            self.assertEqual(read_contents(mocked_io.stderr), expected_output)


if __name__ == "__main__":
    unittest.main()
