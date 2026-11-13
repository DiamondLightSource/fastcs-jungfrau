from dataclasses import KW_ONLY, dataclass

from fastcs.attributes import AttributeIO, AttributeIORef, AttrR
from fastcs.datatypes import DType_T
from slsdet import Jungfrau


@dataclass
class TemperatureAttributeIORef(AttributeIORef):
    module_index: int
    temperature_index: int
    _: KW_ONLY
    update_period: float | None = 1.0


class TemperatureAttributeIO(AttributeIO[DType_T, TemperatureAttributeIORef]):
    def __init__(self, detector: Jungfrau):
        self.detector = detector

        super().__init__()

    async def update(self, attr: AttrR[DType_T, TemperatureAttributeIORef]):
        temperature = self.detector.getTemperature(attr.io_ref.temperature_index)[
            attr.io_ref.module_index
        ]
        await attr.update(temperature)
