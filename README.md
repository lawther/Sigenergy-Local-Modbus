# Sigenergy ESS Integration for Home Assistant

This integration allows you to monitor and control your Sigenergy ESS through Home Assistant.

## Features

- Real-time monitoring of power flows (grid import/export, battery charge/discharge, PV production)
- Energy statistics (daily/monthly/yearly counters)
- Battery metrics (SoC, SoH, temperature, cycles, cell data)
- Inverter parameters (voltages, currents, frequencies, power factors)
- System status indicators
- Control capabilities (operation modes, thresholds, enabling/disabling functions)
- Support for multiple inverters and AC/DC chargers
- Comprehensive device registry with proper relationships

## Requirements

- Home Assistant 2023.8.0 or newer
- Sigenergy ESS with ModbusTCP access
- Network connectivity between Home Assistant and the Sigenergy system

## Installation

### HACS Installation (Recommended)

1. Make sure [HACS](https://hacs.xyz/) is installed in your Home Assistant instance.
2. Add this repository as a custom repository in HACS:
   - Go to HACS > Integrations
   - Click the three dots in the top right corner
   - Select "Custom repositories"
   - Add the URL of this repository
   - Select "Integration" as the category
3. Click "Install" on the Sigenergy integration card
4. Restart Home Assistant

### Manual Installation

1. Download the latest release from the GitHub repository
2. Create a `custom_components/sigen` directory in your Home Assistant configuration directory
3. Extract the contents of the release into the `custom_components/sigen` directory
4. Restart Home Assistant

## Configuration

The integration can be configured through the Home Assistant UI:

1. Go to Settings > Devices & Services
2. Click "Add Integration"
3. Search for "Sigenergy"
4. Follow the configuration flow

### Configuration Parameters

- **Host**: The IP address of your Sigenergy system
- **Port**: The Modbus TCP port (default: 502)
- **Plant ID**: The Modbus slave ID for the plant (default: 247)
- **Inverter Count**: Number of inverters in the system
- **AC Charger Count**: Number of AC chargers in the system

### Advanced Configuration

After the initial setup, you can modify the following options:

- **Scan Interval**: How often to poll the Sigenergy system (in seconds)

## Entities

The integration creates the following entities:

### Plant Sensors

- **Plant Active Power**: Total active power of the plant
- **Plant Reactive Power**: Total reactive power of the plant
- **Photovoltaic Power**: Total PV power production
- **Battery State of Charge**: Current battery SoC
- **Battery State of Health**: Current battery SoH
- **Battery Power**: Current battery power (positive for charging, negative for discharging)
- **Grid Active Power**: Grid power (positive for import, negative for export)
- **Grid Reactive Power**: Grid reactive power
- **EMS Work Mode**: Current EMS operation mode
- **Plant Running State**: Current plant running state

### Inverter Sensors

- **Active Power**: Inverter active power
- **Reactive Power**: Inverter reactive power
- **Battery Power**: Battery power for this inverter
- **Battery State of Charge**: Battery SoC for this inverter
- **Battery State of Health**: Battery SoH for this inverter
- **Battery Temperature**: Battery temperature
- **Battery Cell Voltage**: Average cell voltage
- **PV Power**: PV power for this inverter
- **Grid Frequency**: Grid frequency
- **Phase Voltages**: Voltage for each phase
- **Phase Currents**: Current for each phase
- **Power Factor**: Power factor
- **Daily Charge Energy**: Energy charged today
- **Daily Discharge Energy**: Energy discharged today
- **Total Charge Energy**: Total energy charged
- **Total Discharge Energy**: Total energy discharged

### AC Charger Sensors

- **System State**: Current state of the AC charger
- **Charging Power**: Current charging power
- **Total Energy Consumed**: Total energy consumed by the AC charger

### Controls

- **Plant Power**: Switch to start/stop the plant
- **Inverter Power**: Switch to start/stop individual inverters
- **AC Charger Power**: Switch to start/stop AC chargers
- **DC Charger**: Switch to start/stop DC chargers
- **Remote EMS**: Switch to enable/disable remote EMS
- **EMS Work Mode**: Select to change the EMS work mode
- **Remote EMS Control Mode**: Select to change the remote EMS control mode
- **Active Power Adjustment**: Number to adjust active power
- **Reactive Power Adjustment**: Number to adjust reactive power
- **ESS Max Charging Limit**: Number to set maximum charging power
- **ESS Max Discharging Limit**: Number to set maximum discharging power
- **Grid Export Limitation**: Number to set maximum grid export power
- **Grid Import Limitation**: Number to set maximum grid import power

## Troubleshooting

### Connection Issues

- Ensure the IP address and port are correct
- Check that the Sigenergy system is powered on and connected to the network
- Verify that there are no firewalls blocking the connection
- Check the Home Assistant logs for detailed error messages

### Entity Issues

- If entities are showing as unavailable, check the connection to the Sigenergy system
- If values seem incorrect, verify the Modbus slave IDs are configured correctly
- For missing entities, check that the correct number of inverters and chargers is configured

## System Compatibility

This integration has been tested with the following Sigenergy models:

- SigenStorEC series
- SigenHybrid series
- SigenPV series
- SigenEVAC series

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

This integration is licensed under the MIT License.