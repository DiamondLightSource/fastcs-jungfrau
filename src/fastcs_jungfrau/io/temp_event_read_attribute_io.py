from dataclasses import dataclass

from fastcs.attributes import AttributeIO, AttributeIORef, AttrR
from fastcs.datatypes import DType_T
from fastcs.logging import bind_logger
from slsdet import Jungfrau

logger = bind_logger(__name__)


@dataclass
class TempEventReadAttributeIORef(AttributeIORef):
    update_period: float | None = 1.0


class TempEventReadAttributeIO(AttributeIO[DType_T, TempEventReadAttributeIORef]):
    def __init__(self, detector: Jungfrau):
        self.detector = detector

        super().__init__()

    async def update(self, attr: AttrR[DType_T, TempEventReadAttributeIORef]):
        temp_event = self.detector.temp_event
        await attr.update(temp_event)
