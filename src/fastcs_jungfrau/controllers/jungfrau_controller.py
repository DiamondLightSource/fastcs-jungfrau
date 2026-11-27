import enum
import os
import tempfile
from dataclasses import dataclass

from bidict import bidict
from fastcs.attributes import AttrR, AttrRW
from fastcs.controllers import Controller
from fastcs.datatypes import Bool, Enum, Float, Int, String
from fastcs.logging import logger
from fastcs.methods import command, scan
from slsdet import Jungfrau, defs

from fastcs_jungfrau.config_splitter import split_config
from fastcs_jungfrau.io.enum_attribute_io import EnumAttributeIO, EnumAttributeIORef
from fastcs_jungfrau.io.jungfrau_attribute_io import (
    JungfrauAttributeIO,
    JungfrauAttributeIORef,
)
from fastcs_jungfrau.io.pedestal_mode_attribute_io import (
    PedestalModeAttributeIO,
    PedestalModeAttributeIORef,
)
from fastcs_jungfrau.io.pedestal_param_attribute_io import (
    PedestalParamAttributeIO,
    PedestalParamAttributeIORef,
)
from fastcs_jungfrau.io.static_attribute_io import (
    JungfrauStaticIO,
    JungfrauStaticIORef,
)
from fastcs_jungfrau.io.temp_event_read_attribute_io import (
    TempEventReadAttributeIO,
    TempEventReadAttributeIORef,
)
from fastcs_jungfrau.io.temperature_attribute_io import (
    TemperatureAttributeIO,
    TemperatureAttributeIORef,
)

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


class OnOffEnum(enum.IntEnum):
    Off = 0
    On = 1


@dataclass
class JungfrauControllerSettings:
    config_file_path: str


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
        String(),
        io_ref=JungfrauStaticIORef("firmwareversion"),
        group=SOFTWARE_DETAILS,
    )
    detector_server_version = AttrR(
        String(),
        io_ref=JungfrauStaticIORef("detectorserverversion"),
        group=SOFTWARE_DETAILS,
    )
    hardware_version = AttrR(
        String(),
        io_ref=JungfrauStaticIORef("hardwareversion"),
        group=HARDWARE_DETAILS,
    )
    kernel_version = AttrR(
        String(), io_ref=JungfrauStaticIORef("kernelversion"), group=SOFTWARE_DETAILS
    )
    client_version = AttrR(
        String(), io_ref=JungfrauStaticIORef("clientversion"), group=SOFTWARE_DETAILS
    )
    receiver_version = AttrR(
        String(), io_ref=JungfrauStaticIORef("rx_version"), group=SOFTWARE_DETAILS
    )
    frames_left = AttrR(
        String(), io_ref=JungfrauAttributeIORef("framesl"), group=STATUS
    )
    module_geometry = AttrR(String(), group=HARDWARE_DETAILS)
    module_size = AttrR(String(), group=HARDWARE_DETAILS)
    detector_size = AttrR(String(), group=HARDWARE_DETAILS)
    detector_status = AttrR(
        Enum(DetectorStatus),
        io_ref=EnumAttributeIORef(DETECTOR_STATUS_MAPPING, DetectorStatus, "status"),
        group=STATUS,
    )
    receiver_connected = AttrR(Bool(), group=STATUS)
    temperature_over_heat_event = AttrR(
        Bool(), io_ref=TempEventReadAttributeIORef(), group=TEMPERATURE
    )

    bit_depth = AttrR(Int(), io_ref=JungfrauAttributeIORef("dr"), group=ACQUISITION)

    # Read/Write Attributes
    exposure_time = AttrRW(
        Float(units="s", prec=3),
        io_ref=JungfrauAttributeIORef("exptime"),
        group=ACQUISITION,
    )
    period_between_frames = AttrRW(
        Float(units="s", prec=3),
        io_ref=JungfrauAttributeIORef("period"),
        group=ACQUISITION,
    )
    delay_after_trigger = AttrRW(
        Float(units="s", prec=3),
        io_ref=JungfrauAttributeIORef("delay"),
        group=ACQUISITION,
    )
    frames_per_acq = AttrRW(
        Int(), io_ref=JungfrauAttributeIORef("frames"), group=ACQUISITION
    )
    temperature_over_heat_threshold = AttrRW(
        Int(units="\u00b0C"),
        io_ref=JungfrauAttributeIORef("temp_threshold"),
        group=TEMPERATURE,
    )
    high_voltage = AttrRW(
        Int(units="V"),
        io_ref=JungfrauAttributeIORef("highvoltage"),
        group=POWER,
    )
    power_chip_power_state = AttrRW(
        Bool(), io_ref=JungfrauAttributeIORef("powerchip"), group=POWER
    )
    pedestal_mode_frames = AttrRW(
        Int(),
        io_ref=PedestalParamAttributeIORef(),
        group=PEDESTAL_MODE,
    )
    pedestal_mode_loops = AttrRW(
        Int(), io_ref=PedestalParamAttributeIORef(), group=PEDESTAL_MODE
    )
    pedestal_mode = AttrRW(
        Enum(OnOffEnum),
        io_ref=PedestalModeAttributeIORef(),
        group=PEDESTAL_MODE,
    )
    trigger_mode = AttrRW(
        Enum(TriggerMode),
        io_ref=EnumAttributeIORef(TRIGGER_MODE_ENUM_MAPPING, TriggerMode, "timing"),
        group=ACQUISITION,
    )
    gain_mode = AttrRW(
        Enum(GainMode),
        io_ref=EnumAttributeIORef(GAIN_MODE_MAPPING, GainMode, "gainmode"),
        group=ACQUISITION,
    )

    def __init__(self, settings: JungfrauControllerSettings) -> None:
        # Create a Jungfrau detector object. The config file is loaded in
        # initialise() so that a missing receiver does not prevent the
        # controller from being constructed
        self.detector = Jungfrau()
        self._config_file_path = settings.config_file_path
        self._receiver_lines: list[str] = []
        self._receiver_connected = False

        # Define pedestal mode and param attribute IOs separately so the
        # pedestal mode, frames, and loops can be set after init where
        # attributes are deep copied and re-assigned to self to make them
        # unique across multiple instances of the controller class.  By
        # re-setting them after init the attributes will be accessible
        # from inside the PedestalMode and PedestalParam AttributeIO classes
        self.pedestal_mode_attribute_io = PedestalModeAttributeIO(
            self.detector, self.pedestal_mode_frames, self.pedestal_mode_loops
        )

        self.pedestal_param_attribute_io = PedestalParamAttributeIO(
            self.detector, self.pedestal_mode
        )

        super().__init__(
            ios=[
                JungfrauStaticIO(self.detector),
                JungfrauAttributeIO(self.detector),
                self.pedestal_mode_attribute_io,
                self.pedestal_param_attribute_io,
                TempEventReadAttributeIO(self.detector),
                EnumAttributeIO(self.detector),
                TemperatureAttributeIO(self.detector),
            ]
        )

    async def initialise(self):
        self._load_config()

        # Get the list of temperatures
        temperature_list = self.detector.getTemperatureList()

        # Set the mode, frames, and loops after init attributes so they
        # will be accessible from inside the PedestalModeAttributeIO class
        self.pedestal_param_attribute_io.pedestal_mode = self.pedestal_mode
        self.pedestal_mode_attribute_io.pedestal_frames = self.pedestal_mode_frames
        self.pedestal_mode_attribute_io.pedestal_loops = self.pedestal_mode_loops

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
                self.add_attribute(
                    f"{group_name}Module{module_index + 1}",
                    AttrR(
                        Int(units="\u00b0C"),
                        io_ref=TemperatureAttributeIORef(
                            module_index, temperature_index
                        ),
                        group=group_name,
                    ),
                )

    # Once initialisation is complete, fetch the module and detector geometry
    async def connect(self):
        try:
            detector_size = self.detector.detsize
            module_size = self.detector.module_size
            module_geometry = self.detector.module_geometry
            await self.detector_size.update(f"{detector_size.x} by {detector_size.y}")
            await self.module_geometry.update(
                f"{module_geometry.x} wide by {module_geometry.y} high"
            )
            await self.module_size.update(f"{module_size[0]} by {module_size[1]}")
            await self.receiver_connected.update(self._receiver_connected)

            self._connected = True

        except Exception:
            self._connected = False
            raise

    def _load_config(self) -> None:
        """Load the config file, tolerating an unavailable receiver.

        Detector commands are loaded with ``Jungfrau.config`` (which frees shared
        memory first) and must succeed. Receiver commands are then loaded
        separately so that, if the receiver is not running, the detector is still
        fully configured and the receiver can be connected later.
        """
        detector_lines, self._receiver_lines = split_config(self._config_file_path)

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".config", delete=False
        ) as detector_config:
            detector_config.write("\n".join(detector_lines) + "\n")
        try:
            self.detector.config = detector_config.name
        finally:
            os.unlink(detector_config.name)

        if not self._receiver_lines:
            logger.warning(
                "No receiver commands found in config file",
                config_file=self._config_file_path,
            )
            return

        self._apply_receiver_config()

    def _apply_receiver_config(self) -> bool:
        """Apply the receiver commands from the config file.

        Never raises; returns whether the receiver is now connected.
        """
        try:
            self.detector.parameters = self._receiver_lines
        except RuntimeError as error:
            logger.warning(
                "Receiver unavailable, continuing without it", error=str(error)
            )
            self._receiver_connected = False
        else:
            logger.info("Receiver connected")
            self._receiver_connected = True
        return self._receiver_connected

    async def _set_receiver_connected(self, connected: bool) -> None:
        self._receiver_connected = connected
        await self.receiver_connected.update(connected)

    async def _on_receiver_connected(self) -> None:
        await self.receiver_connected.update(True)
        try:
            await self.receiver_version.update(self.detector.rx_version)
        except RuntimeError as error:
            logger.warning("Failed to read receiver version", error=str(error))

    @command(group=STATUS)
    async def connect_receiver(self) -> None:
        """Retry applying the receiver commands from the config file"""
        if not self._receiver_lines:
            raise RuntimeError("No receiver commands found in config file")
        if not self._apply_receiver_config():
            raise RuntimeError("Failed to connect to receiver")
        await self._on_receiver_connected()

    @scan(10.0)
    async def retry_receiver_connection(self) -> None:
        # Must not raise: an exception in a scan pauses every scan on the controller
        if self._receiver_connected or not self._receiver_lines:
            return
        if self._apply_receiver_config():
            await self._on_receiver_connected()

    @command(group=TEMPERATURE)
    async def over_heat_reset(self) -> None:
        self.detector.temp_event(0)

    @scan(0.2)
    async def update_temperatures(self):
        self.tempvalues = self.detector.tempvalues

    @command(group=ACQUISITION)
    async def acquisition_start(self) -> None:
        if not self._receiver_connected:
            raise RuntimeError(
                "Cannot start acquisition: receiver not connected. "
                "Start slsReceiver and run connect_receiver"
            )
        # Start receiver listener for detector data packets
        # and create a data file (if file write enabled)
        try:
            self.detector.rx_start()
        except RuntimeError:
            await self._set_receiver_connected(False)
            raise
        # Start detector acquisition. Automatically returns
        # to idle at the end of acquisition.
        self.detector.start()

    @command(group=ACQUISITION)
    async def acquisition_stop(self) -> None:
        # Abort detector acquisition, stop server
        self.detector.stop()
        # Stop receiver listener for detector data packets
        # and close current data file (if file write enabled)
        if self._receiver_connected:
            try:
                self.detector.rx_stop()
            except RuntimeError as error:
                logger.warning("Failed to stop receiver", error=str(error))
                await self._set_receiver_connected(False)
        # If acquisition was aborted during the acquire
        # command, clear the acquiring flag in shared
        # memory ready for starting the next acquisition
        self.detector.clearbusy()

    @command(group=ACQUISITION)
    async def clear_busy_flag(self) -> None:
        self.detector.clearbusy()
