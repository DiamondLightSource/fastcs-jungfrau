from dataclasses import dataclass
from typing import Any

from fastcs.attributes import AttributeIO, AttributeIORef, AttrRW, AttrW
from fastcs.datatypes import DType_T
from fastcs.logging import bind_logger
from slsdet import Jungfrau

logger = bind_logger(__name__)


@dataclass
class PedestalParamAttributeIORef(AttributeIORef):
    pass


class PedestalParamAttributeIO(AttributeIO[DType_T, PedestalParamAttributeIORef]):
    def __init__(self, detector: Jungfrau, pedestal_mode: AttrRW):
        self.detector = detector
        self.pedestal_mode = pedestal_mode
        super().__init__()

    async def send(self, attr: AttrW[DType_T, PedestalParamAttributeIORef], value: Any):
        # Update the GUI
        if isinstance(attr, AttrRW):
            await attr.update(value)
        # Trigger a put of the current pedestal mode so that the frames and
        # loops parameters are updated even if the mode is currently enabled
        await self.pedestal_mode.put(self.pedestal_mode.get())
