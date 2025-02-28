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

# Define register definitions based on PLANT_RUNNING_INFO_REGISTERS.csv
PLANT_RUNNING_INFO_REGISTERS = {
    "system_time": ModbusRegisterDefinition(
        address=30000,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=1,
        unit="s",
        description="System time (Epoch seconds)",
    ),
    "system_timezone": ModbusRegisterDefinition(
        address=30002,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S16,
        gain=1,
        unit="min",
        description="System timezone",
    ),
    "ems_work_mode": ModbusRegisterDefinition(
        address=30003,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="EMS work mode",
    ),
    "grid_sensor_status": ModbusRegisterDefinition(
        address=30004,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="Grid Sensor Status (0: not connected, 1: connected)",
    ),
    "grid_sensor_active_power": ModbusRegisterDefinition(
        address=30005,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Grid Active Power (>0 buy from grid; <0 sell to grid)",
    ),
    "grid_sensor_reactive_power": ModbusRegisterDefinition(
        address=30007,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit="kVar",
        description="Grid Reactive Power",
    ),
    "on_off_grid_status": ModbusRegisterDefinition(
        address=30009,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="On/Off Grid status (0: ongrid, 1: offgrid(auto), 2: offgrid(manual))",
    ),
    "max_active_power": ModbusRegisterDefinition(
        address=30010,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Max active power",
    ),
    "max_apparent_power": ModbusRegisterDefinition(
        address=30012,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=1000,
        unit="kVar",
        description="Max apparent power",
    ),
    "ess_soc": ModbusRegisterDefinition(
        address=30014,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=10,
        unit=PERCENTAGE,
        description="Battery State of Charge",
    ),
    "plant_phase_a_active_power": ModbusRegisterDefinition(
        address=30015,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Plant phase A active power",
    ),
    "plant_phase_b_active_power": ModbusRegisterDefinition(
        address=30017,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Plant phase B active power",
    ),
    "plant_phase_c_active_power": ModbusRegisterDefinition(
        address=30019,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Plant phase C active power",
    ),
    "plant_phase_a_reactive_power": ModbusRegisterDefinition(
        address=30021,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit="kVar",
        description="Plant phase A reactive power",
    ),
    "plant_phase_b_reactive_power": ModbusRegisterDefinition(
        address=30023,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit="kVar",
        description="Plant phase B reactive power",
    ),
    "plant_phase_c_reactive_power": ModbusRegisterDefinition(
        address=30025,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit="kVar",
        description="Plant phase C reactive power",
    ),
    "general_alarm1": ModbusRegisterDefinition(
        address=30027,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="General Alarm1 (Refer to Appendix2)",
    ),
    "general_alarm2": ModbusRegisterDefinition(
        address=30028,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="General Alarm2 (Refer to Appendix3)",
    ),
    "general_alarm3": ModbusRegisterDefinition(
        address=30029,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="General Alarm3 (Refer to Appendix4)",
    ),
    "general_alarm4": ModbusRegisterDefinition(
        address=30030,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="General Alarm4 (Refer to Appendix5)",
    ),
    "plant_active_power": ModbusRegisterDefinition(
        address=30031,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Plant active power",
    ),
    "plant_reactive_power": ModbusRegisterDefinition(
        address=30033,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit="kVar",
        description="Plant reactive power",
    ),
    "photovoltaic_power": ModbusRegisterDefinition(
        address=30035,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Photovoltaic power",
    ),
    "ess_power": ModbusRegisterDefinition(
        address=30037,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="ESS power (<0: discharging, >0: charging)",
    ),
    "available_max_active_power": ModbusRegisterDefinition(
        address=30039,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Available max active power",
    ),
    "available_min_active_power": ModbusRegisterDefinition(
        address=30041,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Available min active power",
    ),
    "available_max_reactive_power": ModbusRegisterDefinition(
        address=30043,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=1000,
        unit="kVar",
        description="Available max reactive power",
    ),
    "available_min_reactive_power": ModbusRegisterDefinition(
        address=30045,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=1000,
        unit="kVar",
        description="Available min reactive power",
    ),
    "ess_available_max_charging_power": ModbusRegisterDefinition(
        address=30047,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="ESS Available max charging power",
    ),
    "ess_available_max_discharging_power": ModbusRegisterDefinition(
        address=30049,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="ESS Available max discharging power",
    ),
    "plant_running_state": ModbusRegisterDefinition(
        address=30051,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="Plant running state (Refer to Appendix1)",
    ),
    "grid_sensor_phase_a_active_power": ModbusRegisterDefinition(
        address=30052,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Grid sensor Phase A active power",
    ),
    "grid_sensor_phase_b_active_power": ModbusRegisterDefinition(
        address=30054,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Grid sensor Phase B active power",
    ),
    "grid_sensor_phase_c_active_power": ModbusRegisterDefinition(
        address=30056,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Grid sensor Phase C active power",
    ),
    "grid_sensor_phase_a_reactive_power": ModbusRegisterDefinition(
        address=30058,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit="kVar",
        description="Grid sensor Phase A reactive power",
    ),
    "grid_sensor_phase_b_reactive_power": ModbusRegisterDefinition(
        address=30060,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit="kVar",
        description="Grid sensor Phase B reactive power",
    ),
    "grid_sensor_phase_c_reactive_power": ModbusRegisterDefinition(
        address=30062,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit="kVar",
        description="Grid sensor Phase C reactive power",
    ),
    "ess_available_max_charging_capacity": ModbusRegisterDefinition(
        address=30064,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=100,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        description="ESS Available max charging capacity",
    ),
    "ess_available_max_discharging_capacity": ModbusRegisterDefinition(
        address=30066,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=100,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        description="ESS Available max discharging capacity",
    ),
    "ess_rated_charging_power": ModbusRegisterDefinition(
        address=30068,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="ESS Rated charging power",
    ),
    "ess_rated_discharging_power": ModbusRegisterDefinition(
        address=30070,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="ESS Rated discharging power",
    ),
    "general_alarm5": ModbusRegisterDefinition(
        address=30072,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="General Alarm5 (Refer to Appendix11)",
    ),
    "ess_rated_energy_capacity": ModbusRegisterDefinition(
        address=30083,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=100,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        description="ESS rated energy capacity",
    ),
    "ess_charge_cut_off_soc": ModbusRegisterDefinition(
        address=30085,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=10,
        unit=PERCENTAGE,
        description="ESS charge Cut-Off SOC",
    ),
    "ess_discharge_cut_off_soc": ModbusRegisterDefinition(
        address=30086,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=10,
        unit=PERCENTAGE,
        description="ESS discharge Cut-Off SOC",
    ),
    "ess_soh": ModbusRegisterDefinition(
        address=30087,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=10,
        unit=PERCENTAGE,
        description="Battery State of Health (weighted average of all ESS devices)",
    ),
}

PLANT_PARAMETER_REGISTERS = {
    "start_stop": ModbusRegisterDefinition(
        address=40000,
        count=1,
        register_type=RegisterType.WRITE_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="Start/Stop (0: Stop 1: Start)",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
    "active_power_fixed_target": ModbusRegisterDefinition(
        address=40001,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Active power fixed adjustment target value",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
    "reactive_power_fixed_target": ModbusRegisterDefinition(
        address=40003,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S32,
        gain=1000,
        unit="kVar",
        description="Reactive power fixed adjustment target value",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
    "active_power_percentage_target": ModbusRegisterDefinition(
        address=40005,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S16,
        gain=100,
        unit=PERCENTAGE,
        description="Active power percentage adjustment target value",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
    "qs_ratio_target": ModbusRegisterDefinition(
        address=40006,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S16,
        gain=100,
        unit=PERCENTAGE,
        description="Q/S adjustment target value",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
    "power_factor_target": ModbusRegisterDefinition(
        address=40007,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S16,
        gain=1000,
        description="Power factor adjustment target value",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
    "phase_a_active_power_fixed_target": ModbusRegisterDefinition(
        address=40008,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Phase A active power fixed adjustment target value",
        applicable_to=["hybrid_inverter"],
    ),
    "phase_b_active_power_fixed_target": ModbusRegisterDefinition(
        address=40010,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Phase B active power fixed adjustment target value",
        applicable_to=["hybrid_inverter"],
    ),
    "phase_c_active_power_fixed_target": ModbusRegisterDefinition(
        address=40012,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Phase C active power fixed adjustment target value",
        applicable_to=["hybrid_inverter"],
    ),
    "phase_a_reactive_power_fixed_target": ModbusRegisterDefinition(
        address=40014,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S32,
        gain=1000,
        unit="kVar",
        description="Phase A reactive power fixed adjustment target value",
        applicable_to=["hybrid_inverter"],
    ),
    "phase_b_reactive_power_fixed_target": ModbusRegisterDefinition(
        address=40016,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S32,
        gain=1000,
        unit="kVar",
        description="Phase B reactive power fixed adjustment target value",
        applicable_to=["hybrid_inverter"],
    ),
    "phase_c_reactive_power_fixed_target": ModbusRegisterDefinition(
        address=40018,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S32,
        gain=1000,
        unit="kVar",
        description="Phase C reactive power fixed adjustment target value",
        applicable_to=["hybrid_inverter"],
    ),
    "phase_a_active_power_percentage_target": ModbusRegisterDefinition(
        address=40020,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S16,
        gain=100,
        unit=PERCENTAGE,
        description="Phase A Active power percentage adjustment target value",
        applicable_to=["hybrid_inverter"],
    ),
    "phase_b_active_power_percentage_target": ModbusRegisterDefinition(
        address=40021,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S16,
        gain=100,
        unit=PERCENTAGE,
        description="Phase B Active power percentage adjustment target value",
        applicable_to=["hybrid_inverter"],
    ),
    "phase_c_active_power_percentage_target": ModbusRegisterDefinition(
        address=40022,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S16,
        gain=100,
        unit=PERCENTAGE,
        description="Phase C Active power percentage adjustment target value",
        applicable_to=["hybrid_inverter"],
    ),
    "phase_a_qs_ratio_target": ModbusRegisterDefinition(
        address=40023,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S16,
        gain=100,
        unit=PERCENTAGE,
        description="Phase A Q/S fixed adjustment target value",
        applicable_to=["hybrid_inverter"],
    ),
    "phase_b_qs_ratio_target": ModbusRegisterDefinition(
        address=40024,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S16,
        gain=100,
        unit=PERCENTAGE,
        description="Phase B Q/S fixed adjustment target value",
        applicable_to=["hybrid_inverter"],
    ),
    "phase_c_qs_ratio_target": ModbusRegisterDefinition(
        address=40025,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S16,
        gain=100,
        unit=PERCENTAGE,
        description="Phase C Q/S fixed adjustment target value",
        applicable_to=["hybrid_inverter"],
    ),
    "remote_ems_enable": ModbusRegisterDefinition(
        address=40029,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.U16,
        gain=1,
        description="Remote EMS enable (0: disabled 1: enabled)",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
    "independent_phase_power_control_enable": ModbusRegisterDefinition(
        address=40030,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.U16,
        gain=1,
        description="Independent phase power control enable (0: disabled 1: enabled)",
        applicable_to=["hybrid_inverter"],
    ),
    "remote_ems_control_mode": ModbusRegisterDefinition(
        address=40031,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.U16,
        gain=1,
        description="Remote EMS control mode",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
    "ess_max_charging_limit": ModbusRegisterDefinition(
        address=40032,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="ESS max charging limit",
        applicable_to=["hybrid_inverter"],
    ),
    "ess_max_discharging_limit": ModbusRegisterDefinition(
        address=40034,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="ESS max discharging limit",
        applicable_to=["hybrid_inverter"],
    ),
    "pv_max_power_limit": ModbusRegisterDefinition(
        address=40036,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="PV max power limit",
        applicable_to=["hybrid_inverter"],
    ),
    "grid_maximum_export_limitation": ModbusRegisterDefinition(
        address=40038,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Grid Point Maximum export limitation",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
    "grid_maximum_import_limitation": ModbusRegisterDefinition(
        address=40040,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Grid Point Maximum import limitation",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
    "pcs_maximum_export_limitation": ModbusRegisterDefinition(
        address=40042,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="PCS maximum export limitation",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
    "pcs_maximum_import_limitation": ModbusRegisterDefinition(
        address=40044,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="PCS maximum import limitation",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
}

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

INVERTER_PARAMETER_REGISTERS = {
    "start_stop": ModbusRegisterDefinition(
        address=40500,
        count=1,
        register_type=RegisterType.WRITE_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="Start/Stop inverter (0: Stop 1: Start)",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
    "grid_code": ModbusRegisterDefinition(
        address=40501,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.U16,
        gain=1,
        description="Grid code setting",
        applicable_to=["hybrid_inverter", "pv_inverter"],
    ),
    "dc_charger_start_stop": ModbusRegisterDefinition(
        address=41000,
        count=1,
        register_type=RegisterType.WRITE_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="DC Charger Start/Stop (0: Start 1: Stop)",
        applicable_to=["hybrid_inverter"],
    ),
    "remote_ems_dispatch_enable": ModbusRegisterDefinition(
        address=41500,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.U16,
        gain=1,
        description="Remote EMS dispatch enable (0: disabled 1: enabled)",
        applicable_to=["hybrid_inverter"],
    ),
    "active_power_fixed_adjustment": ModbusRegisterDefinition(
        address=41501,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Active power fixed value adjustment",
        applicable_to=["hybrid_inverter"],
    ),
    "reactive_power_fixed_adjustment": ModbusRegisterDefinition(
        address=41503,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S32,
        gain=1000,
        unit="kVar",
        description="Reactive power fixed value adjustment",
        applicable_to=["hybrid_inverter"],
    ),
    "active_power_percentage_adjustment": ModbusRegisterDefinition(
        address=41505,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S16,
        gain=100,
        unit=PERCENTAGE,
        description="Active power percentage adjustment",
        applicable_to=["hybrid_inverter"],
    ),
    "reactive_power_qs_adjustment": ModbusRegisterDefinition(
        address=41506,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S16,
        gain=100,
        unit=PERCENTAGE,
        description="Reactive power Q/S adjustment",
        applicable_to=["hybrid_inverter"],
    ),
    "power_factor_adjustment": ModbusRegisterDefinition(
        address=41507,
        count=1,
        register_type=RegisterType.HOLDING,
        data_type=DataType.S16,
        gain=1000,
        description="Power factor adjustment",
        applicable_to=["hybrid_inverter"],
    ),
}

AC_CHARGER_RUNNING_INFO_REGISTERS = {
    "system_state": ModbusRegisterDefinition(
        address=32000,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="System states according to IEC61851-1 definition",
    ),
    "total_energy_consumed": ModbusRegisterDefinition(
        address=32001,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=100,
        unit=UnitOfEnergy.KILO_WATT_HOUR,
        description="Total energy consumed",
    ),
    "charging_power": ModbusRegisterDefinition(
        address=32003,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Charging power",
    ),
    "rated_power": ModbusRegisterDefinition(
        address=32005,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U32,
        gain=1000,
        unit=UnitOfPower.KILO_WATT,
        description="Rated power",
    ),
    "rated_current": ModbusRegisterDefinition(
        address=32007,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=100,
        unit=UnitOfElectricCurrent.AMPERE,
        description="Rated current",
    ),
    "rated_voltage": ModbusRegisterDefinition(
        address=32009,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=10,
        unit=UnitOfElectricPotential.VOLT,
        description="Rated voltage",
    ),
    "ac_charger_input_breaker_rated_current": ModbusRegisterDefinition(
        address=32010,
        count=2,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.S32,
        gain=100,
        unit=UnitOfElectricCurrent.AMPERE,
        description="AC-Charger input breaker rated current",
    ),
    "alarm1": ModbusRegisterDefinition(
        address=32012,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="Alarm1",
    ),
    "alarm2": ModbusRegisterDefinition(
        address=32013,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="Alarm2",
    ),
    "alarm3": ModbusRegisterDefinition(
        address=32014,
        count=1,
        register_type=RegisterType.READ_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="Alarm3",
    ),
}

AC_CHARGER_PARAMETER_REGISTERS = {
    "start_stop": ModbusRegisterDefinition(
        address=42000,
        count=1,
        register_type=RegisterType.WRITE_ONLY,
        data_type=DataType.U16,
        gain=1,
        description="Start/Stop AC Charger (0: Start 1: Stop)",
    ),
    "charger_output_current": ModbusRegisterDefinition(
        address=42001,
        count=2,
        register_type=RegisterType.HOLDING,
        data_type=DataType.U32,
        gain=100,
        unit=UnitOfElectricCurrent.AMPERE,
        description="Charger output current ([6, X] X is the smaller value between the rated current and the AC-Charger input breaker rated current.)",
    ),
}
