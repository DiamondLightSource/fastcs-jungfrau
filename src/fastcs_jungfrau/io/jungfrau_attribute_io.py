from dataclasses import KW_ONLY, dataclass
from typing import Any

from fastcs.attribute_io import AttributeIO
from fastcs.attribute_io_ref import AttributeIORef
from fastcs.attributes import AttrR, AttrW
from fastcs.datatypes import T
from slsdet import Jungfrau


@dataclass
class JungfrauAttributeIORef(AttributeIORef):
    command_name: str
    _: KW_ONLY
    update_period: float | None = 0.2


class JungfrauAttributeIO(AttributeIO[T, JungfrauAttributeIORef]):
    def __init__(self, detector: Jungfrau):
        self.detector = detector
        super().__init__()

    async def update(self, attr: AttrR[T, JungfrauAttributeIORef]):
        await attr.update(getattr(self.detector, attr.io_ref.command_name))

    async def send(self, attr: AttrW[T, JungfrauAttributeIORef], value: Any):
        setattr(self.detector, attr.io_ref.command_name, value)
