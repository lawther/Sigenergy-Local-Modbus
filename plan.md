# Register Probing Implementation Plan

## Overview
Implement a system to probe Modbus registers during setup to determine which registers are supported by each device. This will prevent reading unavailable registers and improve system reliability.

## Implementation Details

### 1. Modify ModbusRegisterDefinition Class
```python
@dataclass
class ModbusRegisterDefinition:
    address: int
    count: int
    register_type: RegisterType
    data_type: DataType
    gain: float
    unit: Optional[str] = None
    description: Optional[str] = None
    applicable_to: Optional[list[str]] = None
    is_supported: Optional[bool] = None  # New field to track register support
```

### 2. Add Register Probing Method in SigenergyModbusHub
```python
async def async_probe_registers(self, slave_id: int, register_defs: Dict[str, ModbusRegisterDefinition]) -> Dict[str, bool]:
    """Probe registers to determine which ones are supported.
    
    Returns a dictionary mapping register names to their support status.
    """
    supported_registers = {}
    for name, register in register_defs.items():
        try:
            # Attempt to read the register
            result = await self.async_read_registers(
                slave_id=slave_id,
                address=register.address,
                count=register.count,
                register_type=register.register_type
            )
            # Check if the result is valid (not all zeros, within expected range, etc.)
            supported = self._validate_register_response(result, register)
            supported_registers[name] = supported
            _LOGGER.debug("Register %s (0x%04X) is %s", 
                         name, register.address,
                         "supported" if supported else "not supported")
        except Exception as ex:
            _LOGGER.debug("Register %s (0x%04X) is not supported: %s", 
                         name, register.address, str(ex))
            supported_registers[name] = False
            
    return supported_registers
```

### 3. Initialize Register Support During Setup
Modify coordinator.py to probe registers during initialization:

```python
async def async_setup(self) -> None:
    """Probe registers and initialize supported register list."""
    # Probe plant registers
    self._supported_plant_registers = await self.hub.async_probe_registers(
        self.hub.plant_id, PLANT_RUNNING_INFO_REGISTERS
    )
    
    # Probe inverter registers for each inverter
    self._supported_inverter_registers = {}
    for inverter_id in self.hub.inverter_slave_ids:
        self._supported_inverter_registers[inverter_id] = await self.hub.async_probe_registers(
            inverter_id, INVERTER_RUNNING_INFO_REGISTERS
        )
```

### 4. Use Supported Register List in Data Updates
Modify the data update method to only read supported registers:

```python
async def async_read_inverter_data(self, inverter_id: int) -> Dict[str, Any]:
    """Read only supported inverter registers."""
    data = {}
    supported_registers = self._supported_registers.get(inverter_id, {})
    
    for register_name, register_def in INVERTER_RUNNING_INFO_REGISTERS.items():
        if supported_registers.get(register_name, False):
            try:
                registers = await self.async_read_registers(
                    slave_id=inverter_id,
                    address=register_def.address,
                    count=register_def.count,
                    register_type=register_def.register_type,
                )
                value = self._decode_value(
                    registers=registers,
                    data_type=register_def.data_type,
                    gain=register_def.gain,
                )
                data[register_name] = value
            except Exception as ex:
                _LOGGER.error("Error reading inverter %s register %s: %s", 
                            inverter_id, register_name, ex)
                data[register_name] = None
    
    return data
```

## Benefits

1. **Reliability**: Avoids trying to read unsupported registers
2. **Performance**: Reduces unnecessary Modbus reads
3. **Diagnostics**: Better error logging and debugging
4. **Flexibility**: Automatically adapts to different inverter models
5. **Future-proof**: Easy to add support for new registers

## Implementation Steps

1. Add is_supported field to ModbusRegisterDefinition
2. Implement register probing method
3. Add probing during coordinator setup
4. Modify data reading methods to use supported register list
5. Add debug logging for register support status
6. Update documentation

Would you like me to proceed with implementing this plan?