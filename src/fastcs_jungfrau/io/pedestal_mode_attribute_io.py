import enum
from dataclasses import dataclass
from typing import Any

from fastcs.attributes import AttributeIO, AttributeIORef, AttrR, AttrRW, AttrW
from fastcs.datatypes import DType_T
from fastcs.logging import logger
from slsdet import Jungfrau, pedestalParameters


class OnOffEnum(enum.IntEnum):
    Off = 0
    On = 1


@dataclass
class PedestalModeAttributeIORef(AttributeIORef):
    update_period: float | None = 0.2


class PedestalModeAttributeIO(AttributeIO[DType_T, PedestalModeAttributeIORef]):
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
        logger.info(
            "send",
            frames_id=id(self.pedestal_frames),
            frames=self.pedestal_frames.get(),
            loops_id=id(self.pedestal_loops),
            loops=self.pedestal_loops.get(),
        )

        pedestal_params.enable = value
        # Update the receiver before the detector. If the receiver is unavailable
        # this raises before the detector is touched, so the detector is never put
        # into pedestal mode without the receiver's frame header saying so
        try:
            if value:
                self.detector.rx_jsonpara["pedestal"] = "true"
                self.detector.rx_jsonpara["pedestal_frames"] = pedestal_params.frames
                self.detector.rx_jsonpara["pedestal_loops"] = pedestal_params.loops
            else:
                self.detector.rx_jsonpara["pedestal"] = ""
                self.detector.rx_jsonpara["pedestal_frames"] = ""
                self.detector.rx_jsonpara["pedestal_loops"] = ""
        except RuntimeError as error:
            raise RuntimeError(
                "Cannot set pedestal mode: Failed to update receiver. "
                "Is slsReceiver running and connected?"
            ) from error
        self.detector.pedestalmode = pedestal_params
