"""Constants for the Sigenergy ESS integration."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum, IntEnum
from typing import Final, Optional

# Import needed Home Assistant constants
from homeassistant.const import (
    PERCENTAGE,
    UnitOfElectricCurrent,
    UnitOfElectricPotential,
    UnitOfEnergy,
    UnitOfFrequency,
    UnitOfPower,
    UnitOfTemperature,
)

# Integration domain
DOMAIN = "sigenergy"
DEFAULT_NAME = "Sigenergy ESS"

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
PLANT_RUNNING_INFO_REGISTERS = {
    "plant_running_state": ModbusRegisterDefinition(
        address=30051,  # Example address
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        unit=None,
        description="Plant running state",
    ),
    "ess_soc": ModbusRegisterDefinition(
        address=30014,  # Example address
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=10,  # If SOC is stored as 0-1000 representing 0-100%
        unit=PERCENTAGE,
        description="Battery State of Charge",
    ),
    "ems_work_mode": ModbusRegisterDefinition(
        address=30001,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="EMS Work Mode",
    ),
    "grid_sensor_status": ModbusRegisterDefinition(
        address=30002,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="Grid Sensor Status",
    ),
    "grid_sensor_active_power": ModbusRegisterDefinition(
        address=30003,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit=UnitOfPower.KILO_WATT,
        description="Grid Active Power",
    ),
    "grid_sensor_reactive_power": ModbusRegisterDefinition(
        address=30005,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit="kVar",
        description="Grid Reactive Power",
    ),
    "on_off_grid_status": ModbusRegisterDefinition(
        address=30007,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="Grid Connection Status",
    ),
    "ess_soh": ModbusRegisterDefinition(
        address=30015,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=10,
        unit=PERCENTAGE,
        description="Battery State of Health",
    ),
    "plant_active_power": ModbusRegisterDefinition(
        address=30016,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit=UnitOfPower.KILO_WATT,
        description="Plant Active Power",
    ),
    "plant_reactive_power": ModbusRegisterDefinition(
        address=30018,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit="kVar",
        description="Plant Reactive Power",
    ),
    "photovoltaic_power": ModbusRegisterDefinition(
        address=30020,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit=UnitOfPower.KILO_WATT,
        description="PV Power",
    ),
    "ess_power": ModbusRegisterDefinition(
        address=30022,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit=UnitOfPower.KILO_WATT,
        description="Battery Power",
    ),
    "ess_available_max_charging_power": ModbusRegisterDefinition(
        address=30024,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit=UnitOfPower.KILO_WATT,
        description="Available Max Charging Power",
    ),
    "ess_available_max_discharging_power": ModbusRegisterDefinition(
        address=30026,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit=UnitOfPower.KILO_WATT,
        description="Available Max Discharging Power",
    ),
    "ess_available_max_charging_capacity": ModbusRegisterDefinition(
        address=30028,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        description="Available Max Charging Capacity",
    ),
    "ess_available_max_discharging_capacity": ModbusRegisterDefinition(
        address=30030,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        description="Available Max Discharging Capacity",
    ),
    "ess_rated_energy_capacity": ModbusRegisterDefinition(
        address=30032,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        description="Rated Energy Capacity",
    ),
    "ess_charge_cut_off_soc": ModbusRegisterDefinition(
        address=30034,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        unit=PERCENTAGE,
        description="Charge Cut-Off SOC",
    ),
    "ess_discharge_cut_off_soc": ModbusRegisterDefinition(
        address=30035,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        unit=PERCENTAGE,
        description="Discharge Cut-Off SOC",
    ),
}

PLANT_PARAMETER_REGISTERS = {}

INVERTER_RUNNING_INFO_REGISTERS = {
    "running_state": ModbusRegisterDefinition(
        address=30578,  # Example address
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
    ),
    "model_type": ModbusRegisterDefinition(
        address=30501,
        count=8,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.STRING,
        gain=1,
        description="Model Type",
    ),
    "serial_number": ModbusRegisterDefinition(
        address=30509,
        count=8,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.STRING,
        gain=1,
        description="Serial Number",
    ),
    "machine_firmware_version": ModbusRegisterDefinition(
        address=30517,
        count=4,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.STRING,
        gain=1,
        description="Firmware Version",
    ),
    "rated_active_power": ModbusRegisterDefinition(
        address=30521,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=0.001,
        unit=UnitOfPower.KILO_WATT,
        description="Rated Active Power",
    ),
    "active_power": ModbusRegisterDefinition(
        address=30581,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit=UnitOfPower.KILO_WATT,
        description="Active Power",
    ),
    "reactive_power": ModbusRegisterDefinition(
        address=30583,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit="kVar",
        description="Reactive Power",
    ),
    "ess_charge_discharge_power": ModbusRegisterDefinition(
        address=30585,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit=UnitOfPower.KILO_WATT,
        description="Battery Power",
    ),
    "ess_battery_soc": ModbusRegisterDefinition(
        address=30587,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=0.1,
        unit=PERCENTAGE,
        description="Battery State of Charge",
    ),
    "ess_battery_soh": ModbusRegisterDefinition(
        address=30588,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=0.1,
        unit=PERCENTAGE,
        description="Battery State of Health",
    ),
    "ess_average_cell_temperature": ModbusRegisterDefinition(
        address=30589,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S16,
        gain=0.1,
        unit=UnitOfTemperature.CELSIUS,
        description="Battery Average Cell Temperature",
    ),
    "ess_average_cell_voltage": ModbusRegisterDefinition(
        address=30590,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=0.001,
        unit=UnitOfElectricPotential.VOLT,
        description="Battery Average Cell Voltage",
    ),
    "ess_maximum_battery_temperature": ModbusRegisterDefinition(
        address=30591,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S16,
        gain=0.1,
        unit=UnitOfTemperature.CELSIUS,
        description="Battery Maximum Temperature",
    ),
    "ess_minimum_battery_temperature": ModbusRegisterDefinition(
        address=30592,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S16,
        gain=0.1,
        unit=UnitOfTemperature.CELSIUS,
        description="Battery Minimum Temperature",
    ),
    "ess_maximum_battery_cell_voltage": ModbusRegisterDefinition(
        address=30593,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=0.001,
        unit=UnitOfElectricPotential.VOLT,
        description="Battery Maximum Cell Voltage",
    ),
    "ess_minimum_battery_cell_voltage": ModbusRegisterDefinition(
        address=30594,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=0.001,
        unit=UnitOfElectricPotential.VOLT,
        description="Battery Minimum Cell Voltage",
    ),
    "grid_frequency": ModbusRegisterDefinition(
        address=30595,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=0.01,
        unit=UnitOfFrequency.HERTZ,
        description="Grid Frequency",
    ),
    "pcs_internal_temperature": ModbusRegisterDefinition(
        address=30596,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S16,
        gain=0.1,
        unit=UnitOfTemperature.CELSIUS,
        description="PCS Internal Temperature",
    ),
    "output_type": ModbusRegisterDefinition(
        address=30597,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="Output Type",
    ),
    "phase_a_voltage": ModbusRegisterDefinition(
        address=30598,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=0.1,
        unit=UnitOfElectricPotential.VOLT,
        description="Phase A Voltage",
    ),
    "phase_b_voltage": ModbusRegisterDefinition(
        address=30599,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=0.1,
        unit=UnitOfElectricPotential.VOLT,
        description="Phase B Voltage",
    ),
    "phase_c_voltage": ModbusRegisterDefinition(
        address=30600,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=0.1,
        unit=UnitOfElectricPotential.VOLT,
        description="Phase C Voltage",
    ),
    "phase_a_current": ModbusRegisterDefinition(
        address=30601,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=0.01,
        unit=UnitOfElectricCurrent.AMPERE,
        description="Phase A Current",
    ),
    "phase_b_current": ModbusRegisterDefinition(
        address=30602,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=0.01,
        unit=UnitOfElectricCurrent.AMPERE,
        description="Phase B Current",
    ),
    "phase_c_current": ModbusRegisterDefinition(
        address=30603,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=0.01,
        unit=UnitOfElectricCurrent.AMPERE,
        description="Phase C Current",
    ),
    "power_factor": ModbusRegisterDefinition(
        address=30604,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S16,
        gain=0.001,
        description="Power Factor",
    ),
    "pv_power": ModbusRegisterDefinition(
        address=30605,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=0.001,
        unit=UnitOfPower.KILO_WATT,
        description="PV Power",
    ),
    "insulation_resistance": ModbusRegisterDefinition(
        address=30607,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=0.1,
        unit="MΩ",
        description="Insulation Resistance",
    ),
    "ess_daily_charge_energy": ModbusRegisterDefinition(
        address=30631,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=0.1,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        description="Daily Charge Energy",
    ),
    "ess_accumulated_charge_energy": ModbusRegisterDefinition(
        address=30633,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U64,
        gain=0.1,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        description="Total Charge Energy",
    ),
    "ess_daily_discharge_energy": ModbusRegisterDefinition(
        address=30637,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=0.1,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        description="Daily Discharge Energy",
    ),
    "ess_accumulated_discharge_energy": ModbusRegisterDefinition(
        address=30639,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U64,
        gain=0.1,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        description="Total Discharge Energy",
    ),
}

INVERTER_PARAMETER_REGISTERS = {}

AC_CHARGER_RUNNING_INFO_REGISTERS = {
    "system_state": ModbusRegisterDefinition(
        address=30801,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="System State",
    ),
    "total_energy_consumed": ModbusRegisterDefinition(
        address=30802,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U64,
        gain=0.1,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        description="Total Energy Consumed",
    ),
    "charging_power": ModbusRegisterDefinition(
        address=30806,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=0.001,
        unit=UnitOfPower.KILO_WATT,
        description="Charging Power",
    ),
    "rated_power": ModbusRegisterDefinition(
        address=30808,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=0.001,
        unit=UnitOfPower.KILO_WATT,
        description="Rated Power",
    ),
    "rated_current": ModbusRegisterDefinition(
        address=30810,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=0.001,
        unit=UnitOfElectricCurrent.AMPERE,
        description="Rated Current",
    ),
    "rated_voltage": ModbusRegisterDefinition(
        address=30812,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=0.1,
        unit=UnitOfElectricPotential.VOLT,
        description="Rated Voltage",
    ),
}

AC_CHARGER_PARAMETER_REGISTERS = {}
