import enum
from dataclasses import dataclass
from typing import Any

from fastcs.attributes import AttrHandlerRW, AttrR, AttrRW, AttrW
from fastcs.controller import BaseController, Controller
from fastcs.datatypes import Enum, Float, Int, String
from fastcs.wrappers import command
from slsdet import Jungfrau, pedestalParameters


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


class OnOffEnum(enum.StrEnum):
    Off = "0"
    On = "1"


class PedestalModeHandler(JungfrauHandler):
    async def update(self, attr: AttrR):
        pedestal_mode_state = getattr(self.controller.detector, self.command_name)

        if pedestal_mode_state.enable:
            await attr.set(OnOffEnum.On)
        else:
            await attr.set(OnOffEnum.Off)

    async def put(self, attr: AttrW, value: Any):
        pedestal_params = pedestalParameters()

        pedestal_params.frames = self._controller.pedestal_mode_frames.get()
        pedestal_params.loops = self._controller.pedestal_mode_loops.get()
        pedestal_params.enable = int(value)
        setattr(self.controller.detector, self.command_name, pedestal_params)


class JungfrauController(Controller):
    """
    Controller Class for Jungfrau Detector

    Used for dynamic creation of variables useed in logic of the JungfrauFastCS backend
    Sets up all connections to send and receive information
    """

    # Group Constants
    HARDWARE_DETAILS = "HardwareDetails"
    SOFTWARE_DETAILS = "SoftwareDetails"
    PEDESTAL_MODE = "PedestalMode"
    ACQUISITION_PARAMETERS = "AcquisitionParameters"
    TEMPERATURE = "Temperature"
    STATUS = "Status"
    POWER = "Power"

    firmware_version = AttrR(
        String(), handler=JungfrauHandler("firmwareversion"), group=SOFTWARE_DETAILS
    )
    detector_server_version = AttrR(
        String(),
        handler=JungfrauHandler("detectorserverversion"),
        group=SOFTWARE_DETAILS,
    )
    # Read Only Attributes
    hardware_version = AttrR(
        String(), handler=JungfrauHandler("hardwareversion"), group=HARDWARE_DETAILS
    )
    kernel_version = AttrR(
        String(), handler=JungfrauHandler("kernelversion"), group=SOFTWARE_DETAILS
    )
    client_version = AttrR(
        String(), handler=JungfrauHandler("clientversion"), group=SOFTWARE_DETAILS
    )
    receiver_version = AttrR(
        String(), handler=JungfrauHandler("rx_version"), group=SOFTWARE_DETAILS
    )
    frames_left = AttrR(String(), handler=JungfrauHandler("framesl"), group=STATUS)
    temperatures = AttrR(
        String(), handler=JungfrauHandler("tempvalues"), group=TEMPERATURE
    )
    module_geometry = AttrR(
        String(), handler=JungfrauHandler("module_geometry"), group=HARDWARE_DETAILS
    )
    module_size = AttrR(
        String(), handler=JungfrauHandler("module_size"), group=HARDWARE_DETAILS
    )
    detector_size = AttrR(
        String(), handler=JungfrauHandler("detsize"), group=HARDWARE_DETAILS
    )
    status = AttrR(String(), handler=JungfrauHandler("status"), group=STATUS)
    # Read/Write Attributes
    exposure_time = AttrRW(
        Float(), handler=JungfrauHandler("exptime"), group=ACQUISITION_PARAMETERS
    )
    period_between_frames = AttrRW(
        Float(), handler=JungfrauHandler("period"), group=ACQUISITION_PARAMETERS
    )
    delay_after_trigger = AttrRW(
        Float(), handler=JungfrauHandler("delay"), group=ACQUISITION_PARAMETERS
    )
    frames_per_acq = AttrRW(
        Int(), handler=JungfrauHandler("frames"), group=ACQUISITION_PARAMETERS
    )
    temperature_threshold = AttrRW(
        Float(), handler=JungfrauHandler("temp_threshold"), group=TEMPERATURE
    )
    temperature_event = AttrRW(
        Int(), handler=JungfrauHandler("temp_event"), group=TEMPERATURE
    )
    high_voltage = AttrRW(Int(), handler=JungfrauHandler("highvoltage"), group=POWER)
    power_chip = AttrRW(Int(), handler=JungfrauHandler("powerchip"), group=POWER)
    pedestal_mode_frames = AttrRW(Int(), group=PEDESTAL_MODE)
    pedestal_mode_loops = AttrRW(Int(), group=PEDESTAL_MODE)
    pedestal_mode_control = AttrRW(
        Enum(OnOffEnum),
        handler=PedestalModeHandler("pedestalmode"),
        group=PEDESTAL_MODE,
    )

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
