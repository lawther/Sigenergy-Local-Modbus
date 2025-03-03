"""Modbus communication for Sigenergy ESS."""
# pylint: disable=import-error
# pyright: reportMissingImports=false
from __future__ import annotations

import asyncio
import logging
import struct
from typing import Any, Dict, List, Optional, Tuple, Union

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_HOST, CONF_PORT
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from pymodbus.client import AsyncModbusTcpClient
from pymodbus.constants import Endian
from pymodbus.exceptions import ConnectionException, ModbusException
from pymodbus.payload import BinaryPayloadBuilder, BinaryPayloadDecoder
from pymodbus.client.mixin import ModbusClientMixin

from .const import (
    CONF_AC_CHARGER_COUNT,
    CONF_AC_CHARGER_SLAVE_IDS,
    CONF_DC_CHARGER_COUNT,
    CONF_DC_CHARGER_SLAVE_IDS,
    CONF_INVERTER_COUNT,
    CONF_INVERTER_SLAVE_IDS,
    CONF_PLANT_ID,
    CONF_SLAVE_ID,
    DEFAULT_AC_CHARGER_COUNT,
    DEFAULT_DC_CHARGER_COUNT,
    DEFAULT_INVERTER_COUNT,
    DEFAULT_SLAVE_ID,
    DataType,
    PLANT_RUNNING_INFO_REGISTERS,
    PLANT_PARAMETER_REGISTERS,
    INVERTER_RUNNING_INFO_REGISTERS,
    INVERTER_PARAMETER_REGISTERS,
    AC_CHARGER_RUNNING_INFO_REGISTERS,
    AC_CHARGER_PARAMETER_REGISTERS,
    DC_CHARGER_RUNNING_INFO_REGISTERS,
    DC_CHARGER_PARAMETER_REGISTERS,
    RegisterType,
)

_LOGGER = logging.getLogger(__name__)


class SigenergyModbusError(HomeAssistantError):
    """Exception for Sigenergy Modbus errors."""


class SigenergyModbusHub:
    """Modbus hub for Sigenergy ESS."""

    def __init__(
        self,
        hass: HomeAssistant,
        host: str,
        port: int,
        config_entry: ConfigEntry,
    ) -> None:
        """Initialize the Modbus hub."""
        self.hass = hass
        self.host = host
        self.port = port
        self.client: Optional[AsyncModbusTcpClient] = None
        self.lock = asyncio.Lock()
        self.connected = False
        self.config_entry = config_entry
        
        # Get slave IDs from config
        self.plant_id = config_entry.data.get(CONF_PLANT_ID, DEFAULT_SLAVE_ID)
        self.inverter_count = config_entry.data.get(CONF_INVERTER_COUNT, DEFAULT_INVERTER_COUNT)
        self.ac_charger_count = config_entry.data.get(CONF_AC_CHARGER_COUNT, DEFAULT_AC_CHARGER_COUNT)
        self.dc_charger_count = config_entry.data.get(CONF_DC_CHARGER_COUNT, DEFAULT_DC_CHARGER_COUNT)
        
        # Get specific slave IDs if configured
        self.inverter_slave_ids = config_entry.data.get(
            CONF_INVERTER_SLAVE_IDS, list(range(1, self.inverter_count + 1))
        )
        self.ac_charger_slave_ids = config_entry.data.get(
            CONF_AC_CHARGER_SLAVE_IDS, list(range(self.inverter_count + 1, self.inverter_count + self.ac_charger_count + 1))
        )
        self.dc_charger_slave_ids = config_entry.data.get(
            CONF_DC_CHARGER_SLAVE_IDS, list(range(self.inverter_count + self.ac_charger_count + 1,
                                                 self.inverter_count + self.ac_charger_count + self.dc_charger_count + 1))
        )

    async def async_connect(self) -> None:
        """Connect to the Modbus device."""
        if self.connected:
            return

        try:
            async with self.lock:
                self.client = AsyncModbusTcpClient(
                    host=self.host,
                    port=self.port,
                    timeout=10,
                    retries=3,
                    # Removed retry_on_empty parameter as it's not supported
                )
                
                connected = await self.client.connect()
                if not connected:
                    raise SigenergyModbusError(f"Failed to connect to {self.host}:{self.port}")
                
                self.connected = True
                _LOGGER.info("Connected to Sigenergy system at %s:%s", self.host, self.port)
        except Exception as ex:
            self.connected = False
            raise SigenergyModbusError(f"Error connecting to Sigenergy system: {ex}") from ex

    async def async_close(self) -> None:
        """Close the Modbus connection."""
        if self.client and self.connected:
            async with self.lock:
                self.client.close()
                self.connected = False
                _LOGGER.info("Disconnected from Sigenergy system at %s:%s", self.host, self.port)

    async def async_read_registers(
        self, 
        slave_id: int, 
        address: int, 
        count: int, 
        register_type: RegisterType
    ) -> List[int]:
        """Read registers from the Modbus device."""
        if not self.connected:
            await self.async_connect()

        try:
            async with self.lock:
                if register_type in [RegisterType.READ_ONLY, RegisterType.HOLDING]:
                    if register_type == RegisterType.READ_ONLY:
                        result = await self.client.read_input_registers(
                            address=address, count=count, slave=slave_id
                        )
                    else:
                        result = await self.client.read_holding_registers(
                            address=address, count=count, slave=slave_id
                        )
                    
                    if result.isError():
                        raise SigenergyModbusError(
                            f"Error reading registers at address {address}: {result}"
                        )
                    
                    return result.registers
                else:
                    raise SigenergyModbusError(
                        f"Register type {register_type} is not readable"
                    )
        except ConnectionException as ex:
            self.connected = False
            raise SigenergyModbusError(f"Connection error: {ex}") from ex
        except ModbusException as ex:
            raise SigenergyModbusError(f"Modbus error: {ex}") from ex
        except Exception as ex:
            raise SigenergyModbusError(f"Error reading registers: {ex}") from ex

    async def async_write_register(
        self, 
        slave_id: int, 
        address: int, 
        value: int, 
        register_type: RegisterType
    ) -> None:
        """Write a single register to the Modbus device."""
        if not self.connected:
            await self.async_connect()

        try:
            async with self.lock:
                if register_type in [RegisterType.HOLDING, RegisterType.WRITE_ONLY]:
                    result = await self.client.write_register(
                        address=address, value=value, slave=slave_id
                    )
                    
                    if result.isError():
                        raise SigenergyModbusError(
                            f"Error writing register at address {address}: {result}"
                        )
                else:
                    raise SigenergyModbusError(
                        f"Register type {register_type} is not writable"
                    )
        except ConnectionException as ex:
            self.connected = False
            raise SigenergyModbusError(f"Connection error: {ex}") from ex
        except ModbusException as ex:
            raise SigenergyModbusError(f"Modbus error: {ex}") from ex
        except Exception as ex:
            raise SigenergyModbusError(f"Error writing register: {ex}") from ex

    async def async_write_registers(
        self, 
        slave_id: int, 
        address: int, 
        values: List[int], 
        register_type: RegisterType
    ) -> None:
        """Write multiple registers to the Modbus device."""
        if not self.connected:
            await self.async_connect()

        try:
            async with self.lock:
                if register_type in [RegisterType.HOLDING, RegisterType.WRITE_ONLY]:
                    result = await self.client.write_registers(
                        address=address, values=values, slave=slave_id
                    )
                    
                    if result.isError():
                        raise SigenergyModbusError(
                            f"Error writing registers at address {address}: {result}"
                        )
                else:
                    raise SigenergyModbusError(
                        f"Register type {register_type} is not writable"
                    )
        except ConnectionException as ex:
            self.connected = False
            raise SigenergyModbusError(f"Connection error: {ex}") from ex
        except ModbusException as ex:
            raise SigenergyModbusError(f"Modbus error: {ex}") from ex
        except Exception as ex:
            raise SigenergyModbusError(f"Error writing registers: {ex}") from ex

    def _decode_value(
        self, 
        registers: List[int], 
        data_type: DataType, 
        gain: float
    ) -> Union[int, float, str]:
        """Decode register values based on data type."""
        if data_type == DataType.U16:
            value = ModbusClientMixin.convert_from_registers(
                registers, data_type=ModbusClientMixin.DATATYPE.UINT16
            )
        elif data_type == DataType.S16:
            value = 0
            value = ModbusClientMixin.convert_from_registers(
                registers, data_type=ModbusClientMixin.DATATYPE.INT16
            )
        elif data_type == DataType.U32:
            value = 0
            value = ModbusClientMixin.convert_from_registers(
                registers, data_type=ModbusClientMixin.DATATYPE.UINT32
            )
        elif data_type == DataType.S32:
            value = 0
            value = ModbusClientMixin.convert_from_registers(
                registers, data_type=ModbusClientMixin.DATATYPE.INT32
            )
        elif data_type == DataType.U64:
            value = 0
            value = ModbusClientMixin.convert_from_registers(
                registers, data_type=ModbusClientMixin.DATATYPE.UINT64
            )
        elif data_type == DataType.STRING:
            # Convert to bytes first, then decode as ASCII
            # bytes_data = b''.join(struct.pack('>H', reg) for reg in registers)
            # value = bytes_data.decode('ascii').strip('\x00')
            return ModbusClientMixin.convert_from_registers(registers, data_type=ModbusClientMixin.DATATYPE.STRING)
            # return value  # No gain for strings
        else:
            raise SigenergyModbusError(f"Unsupported data type: {data_type}")
        
        # Apply gain
        if isinstance(value, (int, float)) and gain != 1:
            value = value / gain
            
        return value

    def _encode_value(
        self, 
        value: Union[int, float, str], 
        data_type: DataType, 
        gain: float
    ) -> List[int]:
        """Encode value to register values based on data type."""
        builder = BinaryPayloadBuilder(word_order='big', wordorder=Endian.BIG)
        
        # Apply gain for numeric values
        if isinstance(value, (int, float)) and gain != 1 and data_type != DataType.STRING:
            value = int(value * gain)
        
        if data_type == DataType.U16:
            builder.add_16bit_uint(value)
        elif data_type == DataType.S16:
            builder.add_16bit_int(value)
        elif data_type == DataType.U32:
            builder.add_32bit_uint(value)
        elif data_type == DataType.S32:
            builder.add_32bit_int(value)
        elif data_type == DataType.U64:
            builder.add_64bit_uint(value)
        elif data_type == DataType.STRING:
            builder.add_string(value)
        else:
            raise SigenergyModbusError(f"Unsupported data type: {data_type}")
        
        return builder.to_registers()

    async def async_read_plant_data(self) -> Dict[str, Any]:
        """Read all plant data."""
        data = {}
        
        for register_name, register_def in PLANT_RUNNING_INFO_REGISTERS.items():
            try:
                registers = await self.async_read_registers(
                    slave_id=self.plant_id,
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
                _LOGGER.error("Error reading plant register %s: %s", register_name, ex)
                data[register_name] = None
        
        return data

    async def async_read_inverter_data(self, inverter_id: int) -> Dict[str, Any]:
        """Read all inverter data."""
        data = {}
        
        for register_name, register_def in INVERTER_RUNNING_INFO_REGISTERS.items():
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
                _LOGGER.error("Error reading inverter %s register %s: %s", inverter_id, register_name, ex)
                data[register_name] = None
        
        return data

    async def async_read_ac_charger_data(self, ac_charger_id: int) -> Dict[str, Any]:
        """Read all AC charger data."""
        data = {}
        
        for register_name, register_def in AC_CHARGER_RUNNING_INFO_REGISTERS.items():
            try:
                registers = await self.async_read_registers(
                    slave_id=ac_charger_id,
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
                _LOGGER.error("Error reading AC charger %s register %s: %s", ac_charger_id, register_name, ex)
                data[register_name] = None
        
        return data

    async def async_read_dc_charger_data(self, dc_charger_id: int) -> Dict[str, Any]:
        """Read all DC charger data."""
        data = {}
        
        for register_name, register_def in DC_CHARGER_RUNNING_INFO_REGISTERS.items():
            try:
                registers = await self.async_read_registers(
                    slave_id=dc_charger_id,
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
                _LOGGER.error("Error reading DC charger %s register %s: %s", dc_charger_id, register_name, ex)
                data[register_name] = None
        
        return data

    async def async_write_plant_parameter(
        self, 
        register_name: str, 
        value: Union[int, float, str]
    ) -> None:
        """Write a plant parameter."""
        if register_name not in PLANT_PARAMETER_REGISTERS:
            raise SigenergyModbusError(f"Unknown plant parameter: {register_name}")
        
        register_def = PLANT_PARAMETER_REGISTERS[register_name]
        
        encoded_values = self._encode_value(
            value=value,
            data_type=register_def.data_type,
            gain=register_def.gain,
        )
        
        if len(encoded_values) == 1:
            await self.async_write_register(
                slave_id=self.plant_id,
                address=register_def.address,
                value=encoded_values[0],
                register_type=register_def.register_type,
            )
        else:
            await self.async_write_registers(
                slave_id=self.plant_id,
                address=register_def.address,
                values=encoded_values,
                register_type=register_def.register_type,
            )

    async def async_write_inverter_parameter(
        self, 
        inverter_id: int, 
        register_name: str, 
        value: Union[int, float, str]
    ) -> None:
        """Write an inverter parameter."""
        if register_name not in INVERTER_PARAMETER_REGISTERS:
            raise SigenergyModbusError(f"Unknown inverter parameter: {register_name}")
        
        register_def = INVERTER_PARAMETER_REGISTERS[register_name]
        
        encoded_values = self._encode_value(
            value=value,
            data_type=register_def.data_type,
            gain=register_def.gain,
        )
        
        if len(encoded_values) == 1:
            await self.async_write_register(
                slave_id=inverter_id,
                address=register_def.address,
                value=encoded_values[0],
                register_type=register_def.register_type,
            )
        else:
            await self.async_write_registers(
                slave_id=inverter_id,
                address=register_def.address,
                values=encoded_values,
                register_type=register_def.register_type,
            )

    async def async_write_ac_charger_parameter(
        self, 
        ac_charger_id: int, 
        register_name: str, 
        value: Union[int, float, str]
    ) -> None:
        """Write an AC charger parameter."""
        if register_name not in AC_CHARGER_PARAMETER_REGISTERS:
            raise SigenergyModbusError(f"Unknown AC charger parameter: {register_name}")
        
        register_def = AC_CHARGER_PARAMETER_REGISTERS[register_name]
        
        encoded_values = self._encode_value(
            value=value,
            data_type=register_def.data_type,
            gain=register_def.gain,
        )
        
        if len(encoded_values) == 1:
            await self.async_write_register(
                slave_id=ac_charger_id,
                address=register_def.address,
                value=encoded_values[0],
                register_type=register_def.register_type,
            )
        else:
            await self.async_write_registers(
                slave_id=ac_charger_id,
                address=register_def.address,
                values=encoded_values,
                register_type=register_def.register_type,
            )
            
    async def async_write_dc_charger_parameter(
        self,
        dc_charger_id: int,
        register_name: str,
        value: Union[int, float, str]
    ) -> None:
        """Write a DC charger parameter."""
        if register_name not in DC_CHARGER_PARAMETER_REGISTERS:
            raise SigenergyModbusError(f"Unknown DC charger parameter: {register_name}")
        
        register_def = DC_CHARGER_PARAMETER_REGISTERS[register_name]
        
        encoded_values = self._encode_value(
            value=value,
            data_type=register_def.data_type,
            gain=register_def.gain,
        )
        
        if len(encoded_values) == 1:
            await self.async_write_register(
                slave_id=dc_charger_id,
                address=register_def.address,
                value=encoded_values[0],
                register_type=register_def.register_type,
            )
        else:
            await self.async_write_registers(
                slave_id=dc_charger_id,
                address=register_def.address,
                values=encoded_values,
                register_type=register_def.register_type,
            )