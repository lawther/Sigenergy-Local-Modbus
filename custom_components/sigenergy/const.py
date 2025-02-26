"""Constants for the Sigenergy Energy Storage System integration."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Final, Optional

# Integration domain
DOMAIN = "sigenergy"
DEFAULT_NAME = "Sigenergy Energy Storage System"

# Configuration keys
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SLAVE_ID = "slave_id"
CONF_PLANT_ID = "plant_id"
CONF_SCAN_INTERVAL = "scan_interval"
CONF_INVERTER_COUNT = "inverter_count"
CONF_AC_CHARGER_COUNT = "ac_charger_count"
CONF_DC_CHARGER_COUNT = "dc_charger_count"
CONF_INVERTER_SLAVE_IDS = "inverter_slave_ids"
CONF_AC_CHARGER_SLAVE_IDS = "ac_charger_slave_ids"

# Default values
DEFAULT_PORT = 502
DEFAULT_SLAVE_ID = 247  # Plant address
DEFAULT_SCAN_INTERVAL = 30
DEFAULT_INVERTER_COUNT = 1
DEFAULT_AC_CHARGER_COUNT = 0
DEFAULT_DC_CHARGER_COUNT = 0

# Platforms
PLATFORMS = ["sensor", "switch", "select", "number", "button"]

# Device types
DEVICE_TYPE_PLANT = "plant"
DEVICE_TYPE_INVERTER = "inverter"
DEVICE_TYPE_AC_CHARGER = "ac_charger"
DEVICE_TYPE_DC_CHARGER = "dc_charger"

# Modbus function codes
FUNCTION_READ_HOLDING_REGISTERS = 3
FUNCTION_READ_INPUT_REGISTERS = 4
FUNCTION_WRITE_REGISTER = 6
FUNCTION_WRITE_REGISTERS = 16

# Modbus register types
class RegisterType(Enum):
    """Modbus register types."""

    READ_ONLY = "ro"
    HOLDING = "rw"
    WRITE_ONLY = "wo"

# Data types
class DataType(Enum):
    """Data types for Modbus registers."""

    U16 = "u16"
    U32 = "u32"
    U64 = "u64"
    S16 = "s16"
    S32 = "s32"
    STRING = "string"

# Running states (Appendix 1)
class RunningState(IntEnum):
    """Running states for Sigenergy devices."""

    STANDBY = 0
    RUNNING = 1
    FAULT = 2
    SHUTDOWN = 3

# EMS work modes
class EMSWorkMode(IntEnum):
    """EMS work modes."""

    MAX_SELF_CONSUMPTION = 0
    AI_MODE = 1
    TOU = 2
    REMOTE_EMS = 7

# Remote EMS control modes (Appendix 6)
class RemoteEMSControlMode(IntEnum):
    """Remote EMS control modes."""

    PCS_REMOTE_CONTROL = 0
    STANDBY = 1
    MAXIMUM_SELF_CONSUMPTION = 2
    COMMAND_CHARGING_GRID_FIRST = 3
    COMMAND_CHARGING_PV_FIRST = 4
    COMMAND_DISCHARGING_PV_FIRST = 5
    COMMAND_DISCHARGING_ESS_FIRST = 6

# Output types
class OutputType(IntEnum):
    """Output types for inverters."""

    L_N = 0
    L1_L2_L3 = 1
    L1_L2_L3_N = 2
    L1_L2_N = 3

# AC-Charger system states (Appendix 7)
class ACChargerSystemState(IntEnum):
    """System states for AC-Chargers."""

    SYSTEM_INIT = 0
    A1_A2 = 1
    B1 = 2
    B2 = 3
    C1 = 4
    C2 = 5
    F = 6
    E = 7

# Register definitions
@dataclass
class ModbusRegisterDefinition:
    """Modbus register definition."""

    address: int
    count: int
    register_type: RegisterType
    data_type: DataType
    gain: float
    unit: Optional[str] = None
    description: Optional[str] = None
    applicable_to: Optional[list[str]] = None

# Define empty dictionaries for register definitions
PLANT_RUNNING_INFO_REGISTERS = {}
PLANT_PARAMETER_REGISTERS = {}
INVERTER_RUNNING_INFO_REGISTERS = {}
INVERTER_PARAMETER_REGISTERS = {}
AC_CHARGER_RUNNING_INFO_REGISTERS = {}
AC_CHARGER_PARAMETER_REGISTERS = {}
