from pathlib import Path

import pytest

from fastcs_jungfrau.config_splitter import is_receiver_line, split_config

CONFIG = """\
# Jungfrau 2 module config
hostname bchip001+bchip002+

udp_dstport 50001
0:udp_srcip 10.0.0.10
1:udp_srcip 10.0.0.11
0:rx_tcpport 1954   # receiver TCP port
1:rx_tcpport 1955
rx_hostname localhost
udp_dstip auto
fpath /tmp/data
fwrite 0
exptime 10us
"""


def test_split_config(tmp_path: Path):
    config_file = tmp_path / "jungfrau.config"
    config_file.write_text(CONFIG)

    detector_lines, receiver_lines = split_config(config_file)

    assert detector_lines == [
        "hostname bchip001+bchip002+",
        "udp_dstport 50001",
        "0:udp_srcip 10.0.0.10",
        "1:udp_srcip 10.0.0.11",
        "exptime 10us",
    ]
    assert receiver_lines == [
        "0:rx_tcpport 1954",
        "1:rx_tcpport 1955",
        "rx_hostname localhost",
        "udp_dstip auto",
        "fpath /tmp/data",
        "fwrite 0",
    ]


@pytest.mark.parametrize(
    "line, expected",
    [
        ("rx_hostname localhost", True),
        ("0:rx_zmqport 30001", True),
        ("fname run", True),
        ("udp_dstip auto", True),
        ("udp_dstip2 auto", True),
        ("udp_dstip 10.0.0.1", False),
        ("udp_dstmac 00:11:22:33:44:55", False),
        ("hostname bchip001", False),
        ("frames 10", False),
    ],
)
def test_is_receiver_line(line: str, expected: bool):
    assert is_receiver_line(line) is expected
