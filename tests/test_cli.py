import subprocess
import sys

from fastcs_jungfrau import __version__


def test_cli_version():
    cmd = [sys.executable, "-m", "fastcs_jungfrau", "--version"]
    assert subprocess.check_output(cmd).decode().strip() == __version__
