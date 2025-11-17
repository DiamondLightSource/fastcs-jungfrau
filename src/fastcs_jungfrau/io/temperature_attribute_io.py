from dataclasses import dataclass

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import AttrR
from fastcs.datatypes import T
from slsdet import Jungfrau


@dataclass
class TemperatureAttributeIORef(AttributeIORef):
    module_index: int
    temperature_index: int


class TemperatureAttributeIO(AttributeIO[T, TemperatureAttributeIORef]):
    def __init__(self, detector: Jungfrau):
        self.detector = detector

        super().__init__()

    async def update(self, attr: AttrR[T, TemperatureAttributeIORef]):
        temperature = self.detector.getTemperature(attr.io_ref.temperature_index)[
            attr.io_ref.module_index
        ]
        await attr.update(temperature)
