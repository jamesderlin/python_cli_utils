#!/usr/bin/env python3

"""Unit tests for python_cli_utils."""

import contextlib
import dataclasses
import io
import re
import typing
import unittest
import unittest.mock

import choices_prompt


whitespace = re.compile(r"\s+")


def collapse_whitespace(s: str) -> str:
    """
    Returns a copy of the given string with each sequence of consecutive
    whitespace replaced with a single string.
    """
    return re.sub(whitespace, " ", s)


def assert_strings_equal_ignoring_whitespace(
    test_case: unittest.TestCase,
    s1: str,
    s2: str,
) -> None:
    """Tests that two strings are equal, ignoring whitespace differences."""
    test_case.assertEqual(collapse_whitespace(s1).strip(),
                          collapse_whitespace(s2).strip())


def assert_has_keywords(
    test_case: unittest.TestCase,
    case_sensitive: typing.Optional[typing.List[str]] = None,
    case_insensitive: typing.Optional[typing.List[str]] = None,
) -> typing.Callable[[str], None]:
    """
    Returns a function that, called with an input string, runs
    `unittest.TestCase` assertions that the string includes all of the
    specified keywords.
    """
    def helper(text: str) -> None:
        for keyword in case_sensitive or []:
            test_case.assertIn(keyword, text)

        lower_text = text.lower()
        for keyword in case_insensitive or []:
            test_case.assertIn(keyword.lower(), lower_text)
    return helper


def fake_flush_input(*_args: typing.Any, **_kwargs: typing.Any) -> None:
    """
    Fake implementation for `choices_prompt.flush_input` that does nothing.
    """


@dataclasses.dataclass
class MockedIO:
    """
    Data class returned by `mock_io` that stores mocked versions of
    `sys.stdout` and `sys.stderr`.
    """
    stdout: typing.TextIO
    stderr: typing.TextIO


@contextlib.contextmanager
def mock_io(input: str = "") -> typing.Iterator[MockedIO]:  # pylint: disable=redefined-builtin
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
    expected_tries: int = 1,
    stderr_assert: typing.Optional[typing.Callable[[str], None]] = None,
) -> None:
    """
    Verifies the typical behavior of `choices_prompt.choices_prompt`, setting
    up necessary mocks.
    """
    response: typing.Optional[str] = None
    expect_trailing_newline = False
    with mock_io(input) as mocked_io:
        response = choices_prompt.choices_prompt(prompt=prompt,
                                                 choices=choices,
                                                 default=default)
        if response is None:
            expect_trailing_newline = True

    test_case.assertEqual(response, expected_response)
    mocked_io.stdout.seek(0)

    stdout = mocked_io.stdout.read()
    if expect_trailing_newline:
        test_case.assertTrue(stdout.endswith("\n"))
    assert_strings_equal_ignoring_whitespace(test_case,
                                             stdout,
                                             prompt * expected_tries)

    if stderr_assert:
        mocked_io.stderr.seek(0)
        stderr_assert(mocked_io.stderr.read())


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

    def test_no_default(self) -> None:
        """
        Tests that the prompt is repeated if an empty line is entered with no
        default.
        """
        expect_test_choices(
            self,
            "Test message? ",
            ("Foo", "Bar", "Baz"),
            input="\n\n",
            expected_tries=3,
            expected_response=None,
        )

    def test_eof(self) -> None:
        """Tests that `EOFError` is raised if there is no input."""
        expect_test_choices(self,
                            "Test message? ",
                            ("Foo", "Bar", "Baz"),
                            input="",
                            expected_response=None)

    def test_invalid(self) -> None:
        """
        Tests that the prompt is repeated with an appropriate error message if
        invalid input is entered.
        """
        expect_test_choices(
            self,
            "Test message? ",
            ("Foo", "Bar", "Baz"),
            input="qux",
            expected_tries=2,
            expected_response=None,
            stderr_assert=assert_has_keywords(
                self,
                case_sensitive=["qux"],
                case_insensitive=["not a valid"],
            ),
        )

        expect_test_choices(
            self,
            "Test message? ",
            ("Foo", "Bar", "Baz"),
            input="FooBarBaz",
            expected_tries=2,
            expected_response=None,
            stderr_assert=assert_has_keywords(
                self,
                case_sensitive=["FooBarBaz"],
                case_insensitive=["not a valid"],
            ),
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
            self.assertEqual(response, None)
            self.assertFalse(mocked_io.stdout.read())
            self.assertFalse(mocked_io.stderr.read())


if __name__ == "__main__":
    unittest.main()
