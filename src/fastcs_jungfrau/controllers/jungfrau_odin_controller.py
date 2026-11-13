import asyncio
from dataclasses import dataclass

from fastcs.connections import IPConnectionSettings
from fastcs_odin.controllers import OdinController
from fastcs_odin.controllers.odin_controller import OdinControllerSettings

from fastcs_jungfrau.controllers.jungfrau_controller import (
    JungfrauController,
    JungfrauControllerSettings,
)


@dataclass
class JungfrauOdinControllerSettings(JungfrauControllerSettings):
    odin_connection_settings: IPConnectionSettings


class JungfrauOdinController(JungfrauController):
    """Jungfrau controller with Odin sub controller"""

    def __init__(self, settings: JungfrauOdinControllerSettings) -> None:
        super().__init__(settings)

        self.OD = OdinController(
            OdinControllerSettings(
                connection_settings=settings.odin_connection_settings
            )
        )

    async def initialise(self) -> None:
        """Initialise jungfrau controller and odin controller"""

        await asyncio.gather(super().initialise(), self.OD.initialise())
