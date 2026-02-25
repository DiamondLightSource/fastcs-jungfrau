import asyncio

from fastcs.connections import IPConnectionSettings
from fastcs_odin.controllers import OdinController

from fastcs_jungfrau.controllers.jungfrau_controller import JungfrauController


class JungfrauOdinController(JungfrauController):
    """Jungfrau controller with Odin sub controller"""

    def __init__(
        self,
        config_file_path: str,
        odin_connection_settings: IPConnectionSettings,
    ) -> None:
        super().__init__(config_file_path=config_file_path)

        self.OD = OdinController(odin_connection_settings)

    async def initialise(self) -> None:
        """Initialise jungfrau controller and odin controller"""

        await asyncio.gather(super().initialise(), self.OD.initialise())
