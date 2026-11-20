from dataclasses import KW_ONLY, dataclass
from typing import Any

from fastcs import ONCE
from fastcs.attributes import AttributeIO, AttributeIORef, AttrR, AttrW
from fastcs.datatypes import DType_T
from slsdet import Jungfrau


@dataclass
class JungfrauAttributeIORef(AttributeIORef):
    register: str
    _: KW_ONLY
    update_period: float | None = ONCE


class JungfrauAttributeIO(AttributeIO[DType_T, JungfrauAttributeIORef]):
    def __init__(self, detector: Jungfrau):
        super().__init__()
        self.detector = detector

    async def update(self, attr: AttrR[DType_T, JungfrauAttributeIORef]):
        value = getattr(self.detector, attr.io_ref.register)
        self.log_event(f"{attr.name} changed to {value}", value=value, topic=attr)
        await attr.update(value)

    async def send(self, attr: AttrW[DType_T, JungfrauAttributeIORef], value: Any):
        setattr(self.detector, attr.io_ref.register, value)
