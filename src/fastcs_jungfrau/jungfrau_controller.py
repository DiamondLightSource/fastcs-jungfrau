import enum
from dataclasses import dataclass
from typing import Any

from fastcs.attributes import AttrHandlerRW, AttrR, AttrRW, AttrW
from fastcs.controller import BaseController, Controller
from fastcs.datatypes import Bool, Enum, Float, Int, String
from fastcs.wrappers import command, scan
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


# TODO combine these two classes, maybe need to refactor the dataclass above


class StatusHandler(JungfrauHandler):
    async def update(self, attr):
        # Get the status enum from the slsdet package
        status_enum: enum.IntEnum = getattr(self.controller.detector, self.command_name)

        # Get value compatible with DetectorStatus
        new_enum = DETECTOR_STATUS_MAPPING[status_enum.value]

        await attr.set(new_enum.value)


class TriggerModeHandler(JungfrauHandler):
    async def update(self, attr):
        # Get the status enum from the slsdet package
        status_enum: enum.IntEnum = getattr(self.controller.detector, self.command_name)

        # Get value compatible with TriggerMode
        new_enum = TRIGGER_MODE_ENUM_MAPPING[status_enum.value]

        await attr.set(new_enum.value)


class TempEventReadHandler(JungfrauHandler):
    async def update(self, attr):
        temp_event = getattr(self.controller.detector, self.command_name)
        await attr.set(bool(temp_event))


class PedestalParamHandler(JungfrauHandler):
    # Pedestal frames and loops are not stored
    # as individually accessible detector parameters
    # so there is nothing to update from
    update_period = None
    command_name = ""

    async def update(self, attr: AttrR):
        pass

    async def put(self, attr: AttrW, value: Any):
        # Update the GUI
        if isinstance(attr, AttrRW):
            await attr.set(value)
        # Trigger a put of the current pedestal mode so that the frames and
        # loops parameters are updated even if the mode is currently enabled
        pedestal_mode_state = self._controller.pedestal_mode_state.get()
        await self._controller.pedestal_mode_state.process(pedestal_mode_state)


# The keys for these enums correspond to the keys of the enums given by the slsdet
# package. In our AttrHandlers, we use the keys to map to the new enums defined below


class OnOffEnum(enum.StrEnum):
    OFF = "Off"
    ON = "On"


class DetectorStatus(enum.StrEnum):
    IDLE = "Idle"
    ERROR = "Error"
    WAITING = "Waiting"
    RUN_FINISHED = "Run Finished"
    TRANSMITTING = "Transmitting"
    RUNNING = "Running"
    STOPPED = "Stopped"


class TriggerMode(enum.StrEnum):
    AUTO_TIMING = "Internal"
    TRIGGER_EXPOSURE = "External"


DETECTOR_STATUS_MAPPING = {
    0: DetectorStatus.IDLE,
    1: DetectorStatus.ERROR,
    2: DetectorStatus.WAITING,
    3: DetectorStatus.RUN_FINISHED,
    4: DetectorStatus.TRANSMITTING,
    5: DetectorStatus.RUNNING,
    6: DetectorStatus.STOPPED,
}


TRIGGER_MODE_ENUM_MAPPING = {
    0: TriggerMode.AUTO_TIMING,
    1: TriggerMode.TRIGGER_EXPOSURE,
}


class PedestalModeHandler(JungfrauHandler):
    async def update(self, attr: AttrR):
        pedestal_mode_state = getattr(self.controller.detector, self.command_name)

        if pedestal_mode_state.enable:
            await attr.set(OnOffEnum.ON)
        else:
            await attr.set(OnOffEnum.OFF)

    async def put(self, attr: AttrW, value: Any):
        pedestal_params = pedestalParameters()

        pedestal_params.frames = self._controller.pedestal_mode_frames.get()
        pedestal_params.loops = self._controller.pedestal_mode_loops.get()
        pedestal_params.enable = int(value)
        setattr(self.controller.detector, self.command_name, pedestal_params)


class TemperatureHandler(JungfrauHandler):
    def __init__(self, index: int, key: str):
        self.index = index
        self.key = key

        super().__init__(f"{key} {index}")

    async def update(self, attr):
        temperature_dict: dict = self.controller.tempvalues
        temperature = temperature_dict[self.key][self.index]
        await attr.set(f"{temperature} \u00b0C")


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
    ACQUISITION = "Acquisition"
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
    module_geometry = AttrR(String(), group=HARDWARE_DETAILS)
    module_size = AttrR(String(), group=HARDWARE_DETAILS)
    detector_size = AttrR(String(), group=HARDWARE_DETAILS)
    detector_status = AttrR(
        Enum(DetectorStatus), handler=StatusHandler("status"), group=STATUS
    )
    temperature_over_heat_event = AttrR(
        Bool(), handler=TempEventReadHandler("temp_event"), group=TEMPERATURE
    )

    bit_depth = AttrR(Int(), handler=JungfrauHandler("dr"), group=ACQUISITION)
    trigger_mode = AttrRW(
        Enum(TriggerMode), handler=JungfrauHandler("timing"), group=ACQUISITION
    )

    # Read/Write Attributes
    exposure_time = AttrRW(
        Float(units="s", prec=3),
        handler=JungfrauHandler("exptime"),
        group=ACQUISITION,
    )
    period_between_frames = AttrRW(
        Float(units="s", prec=3),
        handler=JungfrauHandler("period"),
        group=ACQUISITION,
    )
    delay_after_trigger = AttrRW(
        Float(units="s", prec=3),
        handler=JungfrauHandler("delay"),
        group=ACQUISITION,
    )
    frames_per_acq = AttrRW(Int(), handler=JungfrauHandler("frames"), group=ACQUISITION)
    temperature_over_heat_threshold = AttrRW(
        Int(units="\u00b0C"),
        handler=JungfrauHandler("temp_threshold"),
        group=TEMPERATURE,
    )
    high_voltage = AttrRW(
        Int(units="V"),
        handler=JungfrauHandler("highvoltage"),
        group=POWER,
    )
    power_chip_power_state = AttrRW(
        Bool(), handler=JungfrauHandler("powerchip"), group=POWER
    )
    pedestal_mode_frames = AttrRW(
        Int(), handler=PedestalParamHandler(""), group=PEDESTAL_MODE
    )
    pedestal_mode_loops = AttrRW(
        Int(), handler=PedestalParamHandler(""), group=PEDESTAL_MODE
    )
    pedestal_mode_state = AttrRW(
        Enum(OnOffEnum),
        handler=PedestalModeHandler("pedestalmode"),
        group=PEDESTAL_MODE,
    )
    trigger_mode = AttrRW(
        Enum(TriggerMode), handler=TriggerModeHandler("timing"), group=ACQUISITION
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

    async def initialise(self):
        # Get the dictionary of temperatures
        temperature_dict = self.detector.tempvalues

        # Determine the number of modules
        module_geometry = self.detector.module_geometry
        number_of_modules = module_geometry.x * module_geometry.y

        # Create a TemperatureHandler for each module temperature
        # sensor and group them under their dictionary key name
        for key in temperature_dict.keys():
            # Go from temperature_adc to ADC, for example
            prefix = key.split("_")[1].upper()
            for module_index in range(number_of_modules):
                group_name = f"{prefix}Temperatures"
                self.attributes[f"{group_name}Module{module_index + 1}"] = AttrR(
                    String(),
                    handler=TemperatureHandler(module_index, key),
                    group=group_name,
                )

    # Once initialisation is complete, fetch the module and detector geometry
    async def connect(self):
        detector_size = self.detector.detsize
        module_size = self.detector.module_size
        module_geometry = self.detector.module_geometry
        await self.detector_size.set(f"{detector_size.x} by {detector_size.y}")
        await self.module_geometry.set(
            f"{module_geometry.x} wide by {module_geometry.y} high"
        )
        await self.module_size.set(f"{module_size[0]} by {module_size[1]}")

    @command(group=TEMPERATURE)
    async def over_heat_reset(self) -> None:
        await self.temperature_over_heat_event.set(False)

    @scan(0.2)
    async def update_temperatures(self):
        self.tempvalues = self.detector.tempvalues

    @command(group=ACQUISITION)
    async def acquisition_start(self) -> None:
        self.detector.start()

    @command(group=ACQUISITION)
    async def acquisition_stop(self) -> None:
        self.detector.stop()
        # If acquisition was aborted during the acquire
        # command, clear the acquiring flag in shared
        # memory ready for starting the next acquisition
        self.detector.clearbusy()
