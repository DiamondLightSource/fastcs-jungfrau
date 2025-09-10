import enum
from typing import Any, Generic, TypeVar

from bidict import bidict
from fastcs.attributes import AttrHandlerRW, AttrR, AttrRW, AttrW
from fastcs.controller import BaseController, Controller
from fastcs.datatypes import Bool, Enum, Float, Int, String
from fastcs.wrappers import command, scan
from slsdet import Jungfrau, defs, pedestalParameters

TimingMode: enum.IntEnum = defs.timingMode
RunStatus: enum.IntEnum = defs.runStatus
Gain: enum.IntEnum = defs.gainMode


class DetectorStatus(enum.StrEnum):
    Idle = "Idle"
    Error = "Error"
    Waiting = "Waiting"
    RunFinished = "Run Finished"
    Transmitting = "Transmitting"
    Running = "Running"
    Stopped = "Stopped"


class TriggerMode(enum.StrEnum):
    Internal = "Internal"
    External = "External"


class GainMode(enum.StrEnum):
    Dynamic = "Dynamic"
    ForceSwitchG1 = "Force switch G1"
    ForceSwitchG2 = "Force swith G2"
    FixG1 = "Fix G1"
    FixG2 = "Fix G2"
    FixG0 = "Fix G0 (Use with caution!)"


# Two-way mapping between enum values given by the slsdrivers to our own enums
# These mappings use enums from the private slsdet package, so we can't get typing here

TRIGGER_MODE_ENUM_MAPPING: bidict[enum.StrEnum, enum.IntEnum] = bidict(
    {
        TriggerMode.Internal: TimingMode.AUTO_TIMING,  # type: ignore
        TriggerMode.External: TimingMode.TRIGGER_EXPOSURE,  # type: ignore
    }
)

DETECTOR_STATUS_MAPPING: bidict[enum.StrEnum, enum.IntEnum] = bidict(
    {
        DetectorStatus.Idle: RunStatus.IDLE,  # type: ignore
        DetectorStatus.Error: RunStatus.ERROR,  # type: ignore
        DetectorStatus.Waiting: RunStatus.WAITING,  # type: ignore
        DetectorStatus.RunFinished: RunStatus.RUN_FINISHED,  # type: ignore
        DetectorStatus.Transmitting: RunStatus.TRANSMITTING,  # type: ignore
        DetectorStatus.Running: RunStatus.RUNNING,  # type: ignore
        DetectorStatus.Stopped: RunStatus.STOPPED,  # type: ignore
    }
)

GAIN_MODE_MAPPING: bidict[enum.StrEnum, enum.IntEnum] = bidict(
    {
        GainMode.Dynamic: Gain.DYNAMIC,  # type: ignore
        GainMode.ForceSwitchG1: Gain.FORCE_SWITCH_G1,  # type: ignore
        GainMode.ForceSwitchG2: Gain.FORCE_SWITCH_G2,  # type: ignore
        GainMode.FixG1: Gain.FIX_G1,  # type: ignore
        GainMode.FixG2: Gain.FIX_G2,  # type: ignore
        GainMode.FixG0: Gain.FIX_G0,  # type: ignore
    }
)


class JungfrauHandler(AttrHandlerRW):
    def __init__(self, command_name: str, update_period: float | None = 0.2):
        self.command_name = command_name
        self.update_period = update_period

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


T = TypeVar(name="T", bound=enum.Enum)


class EnumHandler(JungfrauHandler, Generic[T]):
    """Handler for AttrRW using enums, to allow us to map slsdet enums to our own enums.

    Args:
    enum_mapping: A two-way mapping from a user-friendly StrEnum to the slsdet private
    enum.

    mapped_enum_type: The enum class which we are using for this attribute.

    command_name: Name of the relevant slsdet detector property.

    update_period: How often, in seconds, we update the attribute by reading from the
    detector

    """

    def __init__(
        self,
        enum_mapping: bidict[T, enum.IntEnum],
        mapped_enum_type: type[T],
        command_name: str,
        update_period: float | None = 0.2,
    ):
        self.mapped_enum_type = mapped_enum_type
        self.enum_mapping = enum_mapping
        super().__init__(command_name, update_period)

    async def update(self, attr):
        raw_enum: enum.IntEnum = getattr(self.controller.detector, self.command_name)
        mapped_enum = self.enum_mapping.inverse[raw_enum]
        await attr.set(mapped_enum)

    async def put(self, attr: AttrW, value: str):
        mapped_enum = self.mapped_enum_type(value)
        raw_enum = self.enum_mapping[mapped_enum]
        setattr(self.controller.detector, self.command_name, raw_enum)


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


class OnOffEnum(enum.IntEnum):
    Off = 0
    On = 1


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
        pedestal_params.enable = value
        if value:
            self._controller.detector.rx_jsonpara["pedestal"] = "true"
            self._controller.detector.rx_jsonpara["pedestal_frames"] = (
                pedestal_params.frames
            )
            self._controller.detector.rx_jsonpara["pedestal_loops"] = (
                pedestal_params.loops
            )
        else:
            self._controller.detector.rx_jsonpara["pedestal"] = ""
            self._controller.detector.rx_jsonpara["pedestal_frames"] = ""
            self._controller.detector.rx_jsonpara["pedestal_loops"] = ""
        setattr(self.controller.detector, self.command_name, pedestal_params)


class TemperatureHandler(JungfrauHandler):
    def __init__(self, module_index: int, temperature_index: str):
        self.module_index = module_index
        self.temperature_index = temperature_index

        super().__init__(f"{temperature_index} {module_index}")

    async def update(self, attr):
        temperature = self.controller.detector.getTemperature(self.temperature_index)[
            self.module_index
        ]
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
        Enum(DetectorStatus),
        handler=EnumHandler(DETECTOR_STATUS_MAPPING, DetectorStatus, "status"),
        group=STATUS,
    )
    temperature_over_heat_event = AttrR(
        Bool(), handler=TempEventReadHandler("temp_event"), group=TEMPERATURE
    )

    bit_depth = AttrR(Int(), handler=JungfrauHandler("dr"), group=ACQUISITION)

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
        Enum(TriggerMode),
        handler=EnumHandler(TRIGGER_MODE_ENUM_MAPPING, TriggerMode, "timing"),
        group=ACQUISITION,
    )
    gain_mode = AttrRW(
        Enum(GainMode),
        handler=EnumHandler(GAIN_MODE_MAPPING, GainMode, "gainmode"),
        group=ACQUISITION,
    )

    def __init__(self, config_file_path) -> None:
        # Create a Jungfrau detector object
        # and initialise it with a config file
        self.detector = Jungfrau()
        self.detector.config = config_file_path

        super().__init__()

    async def initialise(self):
        # Get the list of temperatures
        temperature_list = self.detector.getTemperatureList()

        # Determine the number of modules
        module_geometry = self.detector.module_geometry
        number_of_modules = module_geometry.x * module_geometry.y

        # Create a TemperatureHandler for each module temperature
        # sensor and group them under their list index
        for temperature_index in temperature_list:
            # Go from dacIndex.TEMPERATURE_ADC to ADC, for example
            prefix = str(temperature_index).split("_")[1].upper()
            for module_index in range(number_of_modules):
                group_name = f"{prefix}Temperatures"
                self.attributes[f"{group_name}Module{module_index + 1}"] = AttrR(
                    String(),
                    handler=TemperatureHandler(module_index, temperature_index),
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
        self.detector.temp_event(0)

    @scan(0.2)
    async def update_temperatures(self):
        self.tempvalues = self.detector.tempvalues

    @command(group=ACQUISITION)
    async def acquisition_start(self) -> None:
        # Start receiver listener for detector data packets
        # and create a data file (if file write enabled)
        self.detector.rx_start()
        # Start detector acquisition. Automatically returns
        # to idle at the end of acquisition.
        self.detector.start()

    @command(group=ACQUISITION)
    async def acquisition_stop(self) -> None:
        # Abort detector acquisition, stop server
        self.detector.stop()
        # Stop receiver listener for detector data packets
        # and close current data file (if file write enabled)
        self.detector.rx_stop()
        # If acquisition was aborted during the acquire
        # command, clear the acquiring flag in shared
        # memory ready for starting the next acquisition
        self.detector.clearbusy()

    @command(group=ACQUISITION)
    async def clear_busy_flag(self) -> None:
        self.detector.clearbusy()
