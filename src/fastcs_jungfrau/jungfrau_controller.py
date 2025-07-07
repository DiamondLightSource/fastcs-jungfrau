from dataclasses import dataclass
from typing import Any

from fastcs.attributes import AttrHandlerRW, AttrR, AttrRW, AttrW
from fastcs.controller import BaseController, Controller
from fastcs.datatypes import Float, Int, String
from fastcs.wrappers import command
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
    # Read Only Attributes
    hardware_version = AttrR(String(), handler=JungfrauHandler("hardwareversion"))
    kernel_version = AttrR(String(), handler=JungfrauHandler("kernelversion"))
    client_version = AttrR(String(), handler=JungfrauHandler("clientversion"))
    receiver_version = AttrR(String(), handler=JungfrauHandler("rx_version"))
    dynamic_range = AttrR(String(), handler=JungfrauHandler("dr"))
    frames_left = AttrR(String(), handler=JungfrauHandler("framesl"))
    temperatures = AttrR(String(), handler=JungfrauHandler("tempvalues"))
    module_geometry = AttrR(String(), handler=JungfrauHandler("module_geometry"))
    module_size = AttrR(String(), handler=JungfrauHandler("module_size"))
    detector_size = AttrR(String(), handler=JungfrauHandler("detsize"))
    status = AttrR(String(), handler=JungfrauHandler("status"))
    # Read/Write Attributes
    exposure_time = AttrRW(Float(), handler=JungfrauHandler("exptime"))
    period_between_frames = AttrRW(Float(), handler=JungfrauHandler("period"))
    delay_after_trigger = AttrRW(Float(), handler=JungfrauHandler("delay"))
    frames_per_acq = AttrRW(Int(), handler=JungfrauHandler("frames"))
    temperature_threshold = AttrRW(Float(), handler=JungfrauHandler("temp_threshold"))
    temperature_event = AttrRW(Int(), handler=JungfrauHandler("temp_event"))
    high_voltage = AttrRW(Int(), handler=JungfrauHandler("highvoltage"))
    power_chip = AttrRW(Int(), handler=JungfrauHandler("powerchip"))

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

    @command()
    async def start_acquisition(self) -> None:
        self.detector.start()

    @command()
    async def stop_acquisition(self) -> None:
        self.detector.stop()
        # If acquisition was aborted during the acquire
        # command, clear the acquiring flag in shared
        # memory ready for starting the next acquisition
        self.detector.clearbusy()

    # Starts receiver listener for detector data packets
    # and creates a data file (if file write is enabled)
    @command()
    async def start_receiver(self) -> None:
        self.detector.rx_start()

    # Stops receiver listener for detector data packets
    # and closes current data file (if file write is enabled)
    @command()
    async def stop_receiver(self) -> None:
        self.detector.rx_stop()
