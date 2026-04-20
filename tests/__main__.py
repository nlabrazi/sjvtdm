from __future__ import annotations

import os
import re
import sys
import time
import unittest
from pathlib import Path
from unittest.result import TestResult


ROOT_DIR = Path(__file__).resolve().parent.parent
TESTS_DIR = ROOT_DIR / "tests"

if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))


USE_COLOR = sys.stdout.isatty() and os.getenv("NO_COLOR") is None
if os.getenv("FORCE_COLOR") or os.getenv("CLICOLOR_FORCE"):
    USE_COLOR = os.getenv("NO_COLOR") is None

RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
RED = "\033[31m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
BLUE = "\033[34m"
MAGENTA = "\033[35m"
CYAN = "\033[36m"
WHITE = "\033[37m"

STATUS_COLORS = {
    "PASS": GREEN,
    "FAIL": RED,
    "ERROR": MAGENTA,
    "SKIP": YELLOW,
    "XFAIL": BLUE,
    "XPASS": MAGENTA,
}

ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


def colorize(text: str, *styles: str) -> str:
    if not USE_COLOR or not styles:
        return text
    return f"{''.join(styles)}{text}{RESET}"


def visible_len(text: str) -> int:
    return len(ANSI_RE.sub("", text))


def ljust_visible(text: str, width: int) -> str:
    return text + (" " * max(0, width - visible_len(text)))


def render_summary_panel(status: str, rows: list[tuple[str, str]]) -> str:
    border_color = GREEN if status == "SUCCESS" else RED
    title = f"Test Run {status}"
    label_width = max(len(label) for label, _value in rows)
    value_width = max(len(value) for _label, value in rows)
    inner_width = max(len(title) + 6, label_width + value_width + 8)
    title_padding = max(2, inner_width - len(title) - 2)
    title_left = title_padding // 2
    title_right = title_padding - title_left

    top = (
        colorize("╭", border_color)
        + colorize("─" * title_left, border_color)
        + " "
        + colorize(title, BOLD, border_color)
        + " "
        + colorize("─" * title_right, border_color)
        + colorize("╮", border_color)
    )

    middle = [colorize("│", border_color) + (" " * inner_width) + colorize("│", border_color)]
    for label, value in rows:
        rendered_value = value
        if label == "Passed":
            rendered_value = colorize(value, BOLD, GREEN)
        elif label in {"Failed", "Errors"}:
            rendered_value = colorize(value, BOLD, RED)
        elif label == "Skipped":
            rendered_value = colorize(value, BOLD, YELLOW)
        elif label == "Expected Failures":
            rendered_value = colorize(value, BOLD, BLUE)
        elif label == "Unexpected Successes":
            rendered_value = colorize(value, BOLD, MAGENTA)
        elif label == "Total":
            rendered_value = colorize(value, BOLD, WHITE)
        elif label == "Duration":
            rendered_value = colorize(value, BOLD, WHITE)

        line = "  " + colorize(label.ljust(label_width), WHITE) + " " * 4 + rendered_value.rjust(
            value_width + max(0, visible_len(rendered_value) - len(value))
        )
        middle.append(
            colorize("│", border_color)
            + ljust_visible(line, inner_width)
            + colorize("│", border_color)
        )
    middle.append(colorize("│", border_color) + (" " * inner_width) + colorize("│", border_color))

    bottom = colorize("╰", border_color) + colorize("─" * inner_width, border_color) + colorize("╯", border_color)
    return "\n".join([top, *middle, bottom])


class RichTextTestResult(unittest.TextTestResult):
    def __init__(self, stream, descriptions, verbosity):
        super().__init__(stream, descriptions, verbosity)
        self.successes = 0
        self._started_at: dict[unittest.case.TestCase, float] = {}

    def getDescription(self, test):
        return test.id()

    def startTest(self, test):
        self._started_at[test] = time.perf_counter()
        TestResult.startTest(self, test)

    def stopTest(self, test):
        self._started_at.pop(test, None)
        TestResult.stopTest(self, test)

    def _elapsed(self, test) -> float:
        started_at = self._started_at.get(test, time.perf_counter())
        return time.perf_counter() - started_at

    def _write_line(self, status: str, test, details: str = ""):
        suffix = f" {colorize(details, DIM, STATUS_COLORS.get(status, WHITE))}" if details else ""
        colored_status = colorize(status, BOLD, STATUS_COLORS.get(status, ""))
        test_name = colorize(test.id(), WHITE)
        self.stream.write(f"{colored_status} {test_name}{suffix}\n")

    def addSuccess(self, test):
        TestResult.addSuccess(self, test)
        self.successes += 1
        self._write_line("PASS", test)

    def addFailure(self, test, err):
        TestResult.addFailure(self, test, err)
        self._write_line("FAIL", test, self._exc_info_to_string(err, test).splitlines()[-1])

    def addError(self, test, err):
        TestResult.addError(self, test, err)
        self._write_line("ERROR", test, self._exc_info_to_string(err, test).splitlines()[-1])

    def addSkip(self, test, reason):
        TestResult.addSkip(self, test, reason)
        self._write_line("SKIP", test, reason)

    def addExpectedFailure(self, test, err):
        TestResult.addExpectedFailure(self, test, err)
        self._write_line("XFAIL", test)

    def addUnexpectedSuccess(self, test):
        TestResult.addUnexpectedSuccess(self, test)
        self._write_line("XPASS", test)

    def printErrors(self):
        return


def main() -> int:
    loader = unittest.defaultTestLoader
    suite = loader.discover(start_dir=str(TESTS_DIR), pattern="test_*.py", top_level_dir=str(ROOT_DIR))

    started_at = time.perf_counter()
    result = RichTextTestResult(stream=sys.stdout, descriptions=False, verbosity=0)
    result.failfast = False
    result.buffer = False
    result.tb_locals = False

    result.startTestRun()
    try:
        suite(result)
    finally:
        result.stopTestRun()

    duration = time.perf_counter() - started_at

    status = "SUCCESS" if result.wasSuccessful() else "FAILED"
    summary_rows = [
        ("Passed", str(result.successes)),
        ("Failed", str(len(result.failures))),
        ("Errors", str(len(result.errors))),
        ("Skipped", str(len(result.skipped))),
        ("Expected Failures", str(len(result.expectedFailures))),
        ("Unexpected Successes", str(len(result.unexpectedSuccesses))),
        ("Total", str(result.testsRun)),
        ("Duration", f"{duration:.3f}s"),
    ]
    print()
    print(render_summary_panel(status, summary_rows))
    return 0 if result.wasSuccessful() else 1


if __name__ == "__main__":
    raise SystemExit(main())
