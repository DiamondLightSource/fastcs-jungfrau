import enum
from dataclasses import dataclass
from typing import Any

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import AttrR, AttrRW, AttrW
from fastcs.datatypes import T
from fastcs.logging import bind_logger
from slsdet import Jungfrau, pedestalParameters

logger = bind_logger(__name__)


class OnOffEnum(enum.IntEnum):
    Off = 0
    On = 1


@dataclass
class PedestalModeAttributeIORef(AttributeIORef):
    update_period: float | None = 0.2


class PedestalModeAttributeIO(AttributeIO[T, PedestalModeAttributeIORef]):
    def __init__(
        self, detector: Jungfrau, pedestal_frames: AttrRW, pedestal_loops: AttrRW
    ):
        self.detector = detector
        self.pedestal_frames = pedestal_frames
        self.pedestal_loops = pedestal_loops
        super().__init__()

    async def update(self, attr: AttrR):
        if self.detector.pedestalmode.enable:
            await attr.update(OnOffEnum.On)
        else:
            await attr.update(OnOffEnum.Off)

    async def send(self, attr: AttrW, value: Any):
        pedestal_params = pedestalParameters()

        pedestal_params.frames = self.pedestal_frames.get()
        pedestal_params.loops = self.pedestal_loops.get()
        pedestal_params.enable = value
        if value:
            self.detector.rx_jsonpara["pedestal"] = "true"
            self.detector.rx_jsonpara["pedestal_frames"] = pedestal_params.frames
            self.detector.rx_jsonpara["pedestal_loops"] = pedestal_params.loops
        else:
            self.detector.rx_jsonpara["pedestal"] = ""
            self.detector.rx_jsonpara["pedestal_frames"] = ""
            self.detector.rx_jsonpara["pedestal_loops"] = ""
        self.detector.pedestalmode = pedestal_params
