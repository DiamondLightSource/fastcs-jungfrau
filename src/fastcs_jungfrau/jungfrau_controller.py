from dataclasses import dataclass
from typing import Any

from fastcs.attributes import AttrHandlerRW, AttrR, AttrRW, AttrW
from fastcs.controller import BaseController, Controller
from fastcs.datatypes import Float, String

# from fastcs.wrappers import command
from slsdet import Jungfrau


@dataclass
class JungfrauHandler(AttrHandlerRW):
    command_name: str
    update_period: float | None = 0.2

    async def update(self, attr: AttrR):
        await attr.set(attr.dtype(getattr(self.controller.detector, self.command_name)))

    async def put(self, attr: AttrW, value: Any):
        setattr(self.controller.detector, self.command_name, value)

    async def initialise(self, controller: BaseController):
        assert isinstance(controller, JungfrauController)
        self._controller = controller

    @property
    def controller(self) -> "JungfrauController":
        if self._controller is None:
            raise RuntimeError("Handler not initialised")

        return self._controller


class JungfrauController(Controller):
    """
    Controller Class for Jungfrau Detector

    Used for dynamic creation of variables useed in logic of the JungfrauFastCS backend
    Sets up all connections to send and receive information
    """

    firmware_version = AttrR(String(), handler=JungfrauHandler("firmwareversion"))
    detector_server_version = AttrR(
        String(), handler=JungfrauHandler("detectorserverversion")
    )
    hardware_version = AttrR(String(), handler=JungfrauHandler("hardwareversion"))
    kernel_version = AttrR(String(), handler=JungfrauHandler("kernelversion"))
    client_version = AttrR(String(), handler=JungfrauHandler("clientversion"))
    receiver_version = AttrR(String(), handler=JungfrauHandler("rx_version"))
    serial_number = AttrR(String(), handler=JungfrauHandler("serialnumber"))
    receiver_thread_ids = AttrR(String(), handler=JungfrauHandler("rx_threads"))
    dynamic_range = AttrR(String(), handler=JungfrauHandler("dr"))
    exposure_time = AttrRW(Float(), handler=JungfrauHandler("exptime"))

    def __init__(self) -> None:
        # Create a Jungfrau detector object
        # and initialise it with a config file
        self.detector = Jungfrau()
        try:
            self.detector.config = "/workspaces/jungfrau_2_modules.config"
        except RuntimeError as e:
            if "ClientSocket" in str(e):
                print("Jungfrau Receiver is not running")
            exit()

        super().__init__()

    # @command(group="Power")
    # def turn_on(self) -> None:
