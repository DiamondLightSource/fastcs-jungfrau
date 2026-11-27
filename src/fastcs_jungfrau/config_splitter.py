"""
Split an slsDetectorPackage config file into detector and receiver commands.

Loading a config file with ``Jungfrau.config`` executes it line by line and
aborts at the first failure. If ``slsReceiver`` is not running, the
``rx_hostname`` line fails and every line after it is silently skipped, leaving
the detector partially configured.

Splitting the file lets the detector-only commands be applied unconditionally,
while the receiver-dependent commands can be applied (and retried) separately.
"""

from pathlib import Path

# Commands, other than those starting with 'rx_', that require a connection
# to the receiver
RECEIVER_COMMANDS = frozenset(
    {
        "fpath",
        "fname",
        "findex",
        "fwrite",
        "foverwrite",
        "fformat",
        "fmaster",
    }
)

# Commands that only need the receiver when their value is 'auto', as the
# address is then fetched from the receiver
RECEIVER_AUTO_COMMANDS = frozenset({"udp_dstip", "udp_dstip2"})


def _command_name(token: str) -> str:
    """Strip any module/detector index prefix, e.g. ``0:rx_tcpport``"""
    return token.split(":")[-1]


def is_receiver_line(line: str) -> bool:
    tokens = line.split()
    command = _command_name(tokens[0])
    if command.startswith("rx_") or command in RECEIVER_COMMANDS:
        return True
    if command in RECEIVER_AUTO_COMMANDS:
        return len(tokens) > 1 and tokens[1] == "auto"
    return False


def split_config(config_path: str | Path) -> tuple[list[str], list[str]]:
    """Split a config file into detector lines and receiver lines.

    Comments and blank lines are dropped. Relative order is preserved within
    each list.

    Returns:
        A tuple of (detector_lines, receiver_lines)
    """
    detector_lines: list[str] = []
    receiver_lines: list[str] = []
    for raw_line in Path(config_path).read_text().splitlines():
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if is_receiver_line(line):
            receiver_lines.append(line)
        else:
            detector_lines.append(line)
    return detector_lines, receiver_lines
