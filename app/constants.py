from enum import Enum

class SensorId(Enum):
    """ Identifies each sensor in the system """

    # Misc. sensors
    t0 = "t0"    # Temperature of unheated water entering the setup

    # Circuit 1
    v1 = "v1"  # Voltage
    i1 = "i1"  # Current
    t1 = "t1"  # Temperature

    # Circuit 2
    v2 = "v2"  # Voltage
    i2 = "i2"  # Current
    t2 = "t2"  # Temperature

class RelayId(Enum):
    """ Identifies each relay in the system """

    # Inside relays
    circ1 = "circ1"
    circ2 = "circ2"
    
    # Outside relays (GFCI)
    gfci1 = "gfci1"
    gfci2 = "gfci2"
