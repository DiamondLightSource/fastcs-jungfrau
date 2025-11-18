from dataclasses import KW_ONLY, dataclass

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import AttrR
from fastcs.datatypes import T
from fastcs.logging import bind_logger
from slsdet import Jungfrau

logger = bind_logger(__name__)


@dataclass
class TemperatureAttributeIORef(AttributeIORef):
    module_index: int
    temperature_index: int
    _: KW_ONLY
    update_period: float | None = 1.0


class TemperatureAttributeIO(AttributeIO[T, TemperatureAttributeIORef]):
    def __init__(self, detector: Jungfrau):
        self.detector = detector

        super().__init__()

    async def update(self, attr: AttrR[T, TemperatureAttributeIORef]):
        temperature = self.detector.getTemperature(attr.io_ref.temperature_index)[
            attr.io_ref.module_index
        ]
        await attr.update(temperature)
