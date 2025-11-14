from dataclasses import dataclass
from typing import Any

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import AttrRW, AttrW
from fastcs.datatypes import T
from slsdet import Jungfrau


@dataclass
class PedestalParamAttributeIORef(AttributeIORef):
    pass


class PedestalParamAttributeIO(AttributeIO[T, PedestalParamAttributeIORef]):
    def __init__(self, detector: Jungfrau, pedestal_mode: AttrRW):
        self.detector = detector
        self.pedestal_mode = pedestal_mode
        super().__init__()

    async def send(self, attr: AttrW, value: Any):
        # Update the GUI
        if isinstance(attr, AttrRW):
            await attr.update(value)
        # Trigger a put of the current pedestal mode so that the frames and
        # loops parameters are updated even if the mode is currently enabled
        pedestal_mode_state = self.pedestal_mode.get()
        await self.detector.pedestalmode_state.put(pedestal_mode_state)
