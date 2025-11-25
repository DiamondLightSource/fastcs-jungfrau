from dataclasses import KW_ONLY, dataclass
from typing import Any

from fastcs.attributes import AttributeIO, AttributeIORef, AttrR, AttrW
from fastcs.datatypes import DType_T
from fastcs.logging import bind_logger
from slsdet import Jungfrau

logger = bind_logger(__name__)


@dataclass
class JungfrauAttributeIORef(AttributeIORef):
    command_name: str
    _: KW_ONLY
    update_period: float | None = 0.2


class JungfrauAttributeIO(AttributeIO[DType_T, JungfrauAttributeIORef]):
    def __init__(self, detector: Jungfrau):
        self.detector = detector
        super().__init__()

    async def update(self, attr: AttrR[DType_T, JungfrauAttributeIORef]):
        await attr.update(getattr(self.detector, attr.io_ref.command_name))

    async def send(self, attr: AttrW[DType_T, JungfrauAttributeIORef], value: Any):
        setattr(self.detector, attr.io_ref.command_name, value)
