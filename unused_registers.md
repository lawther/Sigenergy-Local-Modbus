# Unused Sigenergy ESS Registers

This document lists registers from `const.py` that are not currently implemented in any of the platform files (sensor.py, switch.py, select.py).

## Plant Registers

### Running Info (Read-Only) - Suitable for sensor.py
| Register Name | Address | Description | 
|--------------|---------|-------------|
| plant_system_time | 30000 | System time (Epoch seconds) |
| plant_system_timezone | 30002 | System timezone |
| plant_max_active_power | 30010 | Max active power |
| plant_max_apparent_power | 30012 | Max apparent power |
| plant_phase_a_active_power | 30015 | Plant phase A active power |
| plant_phase_b_active_power | 30017 | Plant phase B active power |
| plant_phase_c_active_power | 30019 | Plant phase C active power |
| plant_phase_a_reactive_power | 30021 | Plant phase A reactive power |
| plant_phase_b_reactive_power | 30023 | Plant phase B reactive power |
| plant_phase_c_reactive_power | 30025 | Plant phase C reactive power |
| plant_general_alarm1 | 30027 | General Alarm1 (Refer to Appendix2) |
| plant_general_alarm2 | 30028 | General Alarm2 (Refer to Appendix3) |
| plant_general_alarm3 | 30029 | General Alarm3 (Refer to Appendix4) |
| plant_general_alarm4 | 30030 | General Alarm4 (Refer to Appendix5) |
| plant_grid_sensor_phase_a_active_power | 30052 | Grid sensor Phase A active power |
| plant_grid_sensor_phase_b_active_power | 30054 | Grid sensor Phase B active power |
| plant_grid_sensor_phase_c_active_power | 30056 | Grid sensor Phase C active power |
| plant_grid_sensor_phase_a_reactive_power | 30058 | Grid sensor Phase A reactive power |
| plant_grid_sensor_phase_b_reactive_power | 30060 | Grid sensor Phase B reactive power |
| plant_grid_sensor_phase_c_reactive_power | 30062 | Grid sensor Phase C reactive power |
| plant_ess_rated_charging_power | 30068 | ESS Rated charging power |
| plant_ess_rated_discharging_power | 30070 | ESS Rated discharging power |
| plant_general_alarm5 | 30072 | General Alarm5 (Refer to Appendix11) |

### Parameters (Read-Write) - Suitable for switch.py/select.py
| Register Name | Address | Description |
|--------------|---------|-------------|
| plant_active_power_fixed_target | 40001 | Active power fixed adjustment target value |
| plant_reactive_power_fixed_target | 40003 | Reactive power fixed adjustment target value |
| plant_active_power_percentage_target | 40005 | Active power percentage adjustment target value |
| plant_qs_ratio_target | 40006 | Q/S adjustment target value |
| plant_power_factor_target | 40007 | Power factor adjustment target value |
| plant_phase_a_active_power_fixed_target | 40008 | Phase A active power fixed adjustment target value |
| plant_phase_b_active_power_fixed_target | 40010 | Phase B active power fixed adjustment target value |
| plant_phase_c_active_power_fixed_target | 40012 | Phase C active power fixed adjustment target value |
| plant_phase_a_reactive_power_fixed_target | 40014 | Phase A reactive power fixed adjustment target value |
| plant_phase_b_reactive_power_fixed_target | 40016 | Phase B reactive power fixed adjustment target value |
| plant_phase_c_reactive_power_fixed_target | 40018 | Phase C reactive power fixed adjustment target value |
| plant_phase_a_active_power_percentage_target | 40020 | Phase A Active power percentage adjustment target value |
| plant_phase_b_active_power_percentage_target | 40021 | Phase B Active power percentage adjustment target value |
| plant_phase_c_active_power_percentage_target | 40022 | Phase C Active power percentage adjustment target value |
| plant_phase_a_qs_ratio_target | 40023 | Phase A Q/S fixed adjustment target value |
| plant_phase_b_qs_ratio_target | 40024 | Phase B Q/S fixed adjustment target value |
| plant_phase_c_qs_ratio_target | 40025 | Phase C Q/S fixed adjustment target value |
| plant_ess_max_charging_limit | 40032 | ESS max charging limit |
| plant_ess_max_discharging_limit | 40034 | ESS max discharging limit |
| plant_pv_max_power_limit | 40036 | PV max power limit |
| plant_grid_point_maximum_export_limitation | 40038 | Grid Point Maximum export limitation |
| plant_grid_maximum_import_limitation | 40040 | Grid Point Maximum import limitation |
| plant_pcs_maximum_export_limitation | 40042 | PCS maximum export limitation |
| plant_pcs_maximum_import_limitation | 40044 | PCS maximum import limitation |

## Inverter Registers

### Running Info (Read-Only) - Suitable for sensor.py
| Register Name | Address | Description |
|--------------|---------|-------------|
| inverter_max_apparent_power | 30542 | Max. Apparent Power |
| inverter_max_active_power | 30544 | Max. Active Power |
| inverter_max_absorption_power | 30546 | Max. Absorption Power |
| inverter_rated_battery_capacity | 30548 | Rated Battery Capacity |
| inverter_ess_rated_charge_power | 30550 | ESS Rated Charge Power |
| inverter_ess_rated_discharge_power | 30552 | ESS Rated Discharge Power |
| inverter_max_active_power_adjustment_value | 30579 | Max. Active Power Adjustment Value |
| inverter_min_active_power_adjustment_value | 30581 | Min. Active Power Adjustment Value |
| inverter_max_reactive_power_adjustment_value_fed | 30583 | Max. Reactive Power Adjustment Value Fed to AC Terminal |
| inverter_max_reactive_power_adjustment_value_absorbed | 30585 | Max. Reactive Power Adjustment Value Absorbed from AC Terminal |
| inverter_ess_max_battery_charge_power | 30591 | ESS Max. Battery Charge Power |
| inverter_ess_max_battery_discharge_power | 30593 | ESS Max. Battery Discharge Power |
| inverter_ess_available_battery_charge_energy | 30595 | ESS Available Battery Charge Energy |
| inverter_ess_available_battery_discharge_energy | 30597 | ESS Available Battery Discharge Energy |
| inverter_alarm1 | 30605 | Alarm1 (Refer to Appendix 2) |
| inverter_alarm2 | 30606 | Alarm2 (Refer to Appendix 3) |
| inverter_alarm3 | 30607 | Alarm3 (Refer to Appendix 4) |
| inverter_alarm4 | 30608 | Alarm4 (Refer to Appendix 5) |
| inverter_alarm5 | 30609 | Alarm5 (Refer to Appendix 11) |
| inverter_rated_grid_voltage | 31000 | Rated Grid Voltage |
| inverter_rated_grid_frequency | 31001 | Rated Grid Frequency |
| inverter_ab_line_voltage | 31005 | A-B Line Voltage |
| inverter_bc_line_voltage | 31007 | B-C Line Voltage |
| inverter_ca_line_voltage | 31009 | C-A Line Voltage |
| inverter_pack_count | 31024 | PACK Count |
| inverter_pv_string_count | 31025 | PV String Count |
| inverter_mppt_count | 31026 | MPPT Count |
| inverter_pv1_voltage | 31027 | PV1 Voltage |
| inverter_pv1_current | 31028 | PV1 Current |
| inverter_pv2_voltage | 31029 | PV2 Voltage |
| inverter_pv2_current | 31030 | PV2 Current |
| inverter_pv3_voltage | 31031 | PV3 Voltage |
| inverter_pv3_current | 31032 | PV3 Current |
| inverter_pv4_voltage | 31033 | PV4 Voltage |
| inverter_pv4_current | 31034 | PV4 Current |
| inverter_insulation_resistance | 31037 | Insulation Resistance |
| inverter_startup_time | 31038 | Startup Time |
| inverter_shutdown_time | 31040 | Shutdown Time |
| inverter_pv5_voltage | 31042 | PV5 Voltage |
| inverter_pv5_current | 31043 | PV5 Current |
| inverter_pv6_voltage | 31044 | PV6 Voltage |
| inverter_pv6_current | 31045 | PV6 Current |
| inverter_pv7_voltage | 31046 | PV7 Voltage |
| inverter_pv7_current | 31047 | PV7 Current |
| inverter_pv8_voltage | 31048 | PV8 Voltage |
| inverter_pv8_current | 31049 | PV8 Current |
| inverter_pv9_voltage | 31050 | PV9 Voltage |
| inverter_pv9_current | 31051 | PV9 Current |
| inverter_pv10_voltage | 31052 | PV10 Voltage |
| inverter_pv10_current | 31053 | PV10 Current |
| inverter_pv11_voltage | 31054 | PV11 Voltage |
| inverter_pv11_current | 31055 | PV11 Current |
| inverter_pv12_voltage | 31056 | PV12 Voltage |
| inverter_pv12_current | 31057 | PV12 Current |
| inverter_pv13_voltage | 31058 | PV13 Voltage |
| inverter_pv13_current | 31059 | PV13 Current |
| inverter_pv14_voltage | 31060 | PV14 Voltage |
| inverter_pv14_current | 31061 | PV14 Current |
| inverter_pv15_voltage | 31062 | PV15 Voltage |
| inverter_pv15_current | 31063 | PV15 Current |
| inverter_pv16_voltage | 31064 | PV16 Voltage |
| inverter_pv16_current | 31065 | PV16 Current |

### Parameters (Read-Write) - Suitable for switch.py/select.py
| Register Name | Address | Description |
|--------------|---------|-------------|
| inverter_grid_code | 40501 | Grid code setting |
| inverter_active_power_fixed_adjustment | 41501 | Active power fixed value adjustment |
| inverter_reactive_power_fixed_adjustment | 41503 | Reactive power fixed value adjustment |
| inverter_active_power_percentage_adjustment | 41505 | Active power percentage adjustment |
| inverter_reactive_power_qs_adjustment | 41506 | Reactive power Q/S adjustment |
| inverter_power_factor_adjustment | 41507 | Power factor adjustment |

## AC Charger Registers

### Running Info (Read-Only) - Suitable for sensor.py
| Register Name | Address | Description |
|--------------|---------|-------------|
| ac_charger_input_breaker_rated_current | 32010 | AC-Charger input breaker rated current |
| ac_charger_alarm1 | 32012 | Alarm1 |
| ac_charger_alarm2 | 32013 | Alarm2 |
| ac_charger_alarm3 | 32014 | Alarm3 |

### Parameters (Read-Write) - Suitable for switch.py/select.py
| Register Name | Address | Description |
|--------------|---------|-------------|
| ac_charger_output_current | 42001 | Charger output current |

## Special Notes

1. **Alarms**: There are multiple alarm registers that need special handling:
   - Plant alarms (general_alarm1-5)
   - Inverter alarms (alarm1-5)
   - AC Charger alarms (alarm1-3)
   These should be implemented with proper alarm state mapping.

2. **PV String Data**: There are 16 PV string voltage/current pairs that could be consolidated into a more manageable interface.

3. **Phase-Specific Controls**: Many plant parameters have phase-specific variants (A/B/C) that should be grouped logically in the interface.

4. **Multiple Power Settings**: Various power-related settings need careful consideration to prevent conflicting configurations:
   - Fixed vs. Percentage adjustments
   - Phase-specific vs. Overall adjustments
   - Multiple limit types (ESS, PV, Grid, PCS)