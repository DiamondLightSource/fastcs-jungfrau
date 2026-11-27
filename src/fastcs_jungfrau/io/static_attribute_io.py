"""
AttributeIO for detector configuration values that are expected to remain
static for the lifetime of the IOC.

Attributes using this IO are read once during IOC startup via
``update_period=ONCE`` and then cached in FastCS. They are not polled
thereafter because the detector is not expected to change them while
running.

Typical examples include:

- firmwareversion
- detectorserverversion
- hardwareversion
- kernelversion
- clientversion
- rx_version

This reduces unnecessary detector traffic compared to periodically
polling static configuration information.
"""

from dataclasses import KW_ONLY, dataclass

from fastcs import ONCE
from fastcs.attributes import AttributeIO, AttributeIORef, AttrR
from fastcs.datatypes import DType_T
from fastcs.logging import logger
from slsdet import Jungfrau


@dataclass
class JungfrauStaticIORef(AttributeIORef):
    register: str
    _: KW_ONLY
    update_period: float | None = ONCE


class JungfrauStaticIO(AttributeIO[DType_T, JungfrauStaticIORef]):
    def __init__(self, detector: Jungfrau):
        self.detector = detector
        super().__init__()

    async def update(self, attr: AttrR[DType_T, JungfrauStaticIORef]):
        # These are read once at startup, where an exception would stop FastCS.
        # A failure (e.g. rx_version with no receiver running) is logged and the
        # attribute is left at its default value
        try:
            value = getattr(self.detector, attr.io_ref.register)
        except RuntimeError as error:
            logger.warning(
                "Failed to read static value",
                attribute=attr.name,
                register=attr.io_ref.register,
                error=str(error),
            )
            return
        await attr.update(value)
