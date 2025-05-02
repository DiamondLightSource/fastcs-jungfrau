from fastcs.attributes import AttrR
from fastcs.controller import Controller
from fastcs.datatypes import Int
from slsdet import Jungfrau


class JungfrauController(Controller):
    """
    Controller Class for Jungfrau Detector

    Used for dynamic creation of variables useed in logic of the JungfrauFastCS backend
    Sets up all connections to send and receive information
    """

    def __init__(self) -> None:
        JungfrauController.number = AttrR(Int())
        # Create a Jungfrau detector object
        # and initialise it with a config file
        # self.detector = Jungfrau()
        # self.detector.config = "/workspaces/jungfrau_2_modules.config"

        props = self.read_properties(Jungfrau)

        for prop_name, methods in props.items():
            setattr(JungfrauController, prop_name, AttrR(Int()))
            print(f"Property: {prop_name}")
            print(f"  Getter: {methods['getter']}")
            print(f"  Setter: {methods['setter']}")

        super().__init__()

    # Function to read out properties
    def read_properties(self, cls):
        properties = {}
        for attr_name in dir(cls):
            attr = getattr(cls, attr_name)
            if isinstance(attr, property):
                properties[attr_name] = {"getter": attr.fget, "setter": attr.fset}
        return properties
