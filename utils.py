"""Common utility functions for the project."""

import sys
import time
from datetime import timedelta

BANNER = """

             ('-.-.           {title}
              ('(_.( )
               _   `_`
            __|_|__|_|_
          _|___________|__
         | o o o o o o o /
\033[94m~ ~ ~ ~ ~ ~ ~ ~ ~ ~~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~\033[0m
"""


def configure_output():
    """Make stdout and stderr safe for the banner and status symbols.

    A Windows console defaults to a legacy code page that cannot encode them, which
    would otherwise end the run with a UnicodeEncodeError.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding='utf-8', errors='replace')
        except (AttributeError, ValueError, OSError):
            pass


def print_intro(title: str = 'Data Quality Metrics'):
    """Print a nice intro to the program's output.

    Args:
        title (str, optional): headline shown in the banner. Set it with the
            configuration file's "title".
    """
    print(BANNER.format(title=title))


def time_from_start(start: int):
    """
    Returns the time elapsed since the start of the program in a human-readable format.
    """
    return timedelta(seconds=time.time() - start)
