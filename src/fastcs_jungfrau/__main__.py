from fastcs.launch import launch

from fastcs_jungfrau import __version__

from .controllers.jungfrau_controller import JungfrauController
from .controllers.jungfrau_odin_controller import JungfrauOdinController

launch(
    controller_classes=[JungfrauController, JungfrauOdinController], version=__version__
)
