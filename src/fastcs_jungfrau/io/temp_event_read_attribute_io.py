from dataclasses import dataclass

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import AttrR
from fastcs.datatypes import T
from slsdet import Jungfrau


@dataclass
class TempEventReadAttributeIORef(AttributeIORef):
    pass


class TempEventReadAttributeIO(AttributeIO[T, TempEventReadAttributeIORef]):
    def __init__(self, detector: Jungfrau):
        self.detector = detector

        super().__init__()

    async def update(self, attr: AttrR[T, TempEventReadAttributeIORef]):
        temp_event = self.detector.temp_event
        await attr.update(temp_event)
