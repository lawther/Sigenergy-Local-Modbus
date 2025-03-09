"""Calculated sensor implementations for Sigenergy integration."""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, Optional

_LOGGER = logging.getLogger(__name__)


class SigenergyCalculations:
    """Static class for Sigenergy calculated sensor functions."""
    
    @staticmethod
    def minutes_to_gmt(minutes: Any) -> str:
        """Convert minutes offset to GMT format."""
        if minutes is None:
            return None
        try:
            hours = int(minutes) // 60
            return f"GMT{'+' if hours >= 0 else ''}{hours}"
        except (ValueError, TypeError):
            return None

    @staticmethod
    def epoch_to_datetime(epoch: Any, coordinator_data: Optional[dict] = None) -> Optional[datetime]:
        """Convert epoch timestamp to datetime using system's configured timezone."""
        _LOGGER.debug("Converting epoch timestamp: %s (type: %s)", epoch, type(epoch))
        if epoch is None or epoch == 0:  # Also treat 0 as None for timestamps
            return None

        try:
            # Convert epoch to integer if it isn't already
            epoch_int = int(epoch)
            
            # Create timezone based on coordinator data if available
            if coordinator_data and "plant" in coordinator_data:
                try:
                    tz_offset = coordinator_data["plant"].get("plant_system_timezone")
                    if tz_offset is not None:
                        tz_minutes = int(tz_offset)
                        tz_hours = tz_minutes // 60
                        tz_remaining_minutes = tz_minutes % 60
                        tz = timezone(timedelta(hours=tz_hours, minutes=tz_remaining_minutes))
                    else:
                        tz = timezone.utc
                except (ValueError, TypeError):
                    _LOGGER.warning("Invalid timezone offset in coordinator data, using UTC")
                    tz = timezone.utc
            else:
                tz = timezone.utc
                
            # Additional validation for timestamp range
            if epoch_int < 0 or epoch_int > 32503680000:  # Jan 1, 3000
                _LOGGER.warning("Timestamp %s out of reasonable range", epoch_int)
                return None

            try:
                # Convert timestamp using the determined timezone
                dt = datetime.fromtimestamp(epoch_int, tz=tz)
                _LOGGER.debug("Converted epoch %s to datetime %s with timezone %s", epoch_int, dt, tz)
                return dt
            except (OSError, OverflowError) as ex:
                _LOGGER.warning("Invalid timestamp value %s: %s", epoch_int, ex)
                return None
            
        except (ValueError, TypeError, OSError) as ex:
            _LOGGER.warning("Error converting epoch %s to datetime: %s", epoch, ex)
            return None

    @staticmethod
    def calculate_pv_power(_, coordinator_data: Optional[Dict[str, Any]] = None, extra_params: Optional[Dict[str, Any]] = None) -> Optional[float]:
        """Calculate PV string power with proper error handling."""
        if not coordinator_data or not extra_params:
            _LOGGER.debug("Missing required data for PV power calculation")
            return None
            
        try:
            pv_idx = extra_params.get("pv_idx")
            device_id = extra_params.get("device_id")
            
            if not pv_idx or not device_id:
                _LOGGER.debug("Missing PV string index or device ID for power calculation")
                return None
                
            inverter_data = coordinator_data.get("inverters", {}).get(device_id, {})
            if not inverter_data:
                _LOGGER.debug("No inverter data available for power calculation")
                return None
                
            v_key = f"inverter_pv{pv_idx}_voltage"
            c_key = f"inverter_pv{pv_idx}_current"
            
            pv_voltage = inverter_data.get(v_key)
            pv_current = inverter_data.get(c_key)
            
            # Validate inputs
            if pv_voltage is None or pv_current is None:
                _LOGGER.debug("Missing voltage or current data for PV string %d", pv_idx)
                return None
                
            if not isinstance(pv_voltage, (int, float)) or not isinstance(pv_current, (int, float)):
                _LOGGER.debug("Invalid data types for PV string %d: voltage=%s, current=%s",
                            pv_idx, type(pv_voltage), type(pv_current))
                return None
                
            # Calculate power with bounds checking
            # Make sure we don't return unreasonable values
            power = pv_voltage * pv_current  # Already in Watts since voltage is in V and current in A
            
            # Apply some reasonable bounds
            MAX_REASONABLE_POWER = 20000  # 20kW per string is very high already
            if abs(power) > MAX_REASONABLE_POWER:
                _LOGGER.warning("Calculated power for PV string %d seems excessive: %s W",
                            pv_idx, power)
                
            return power / 1000  # Convert to kW
        except Exception as ex:
            _LOGGER.warning("Error calculating power for PV string %d: %s",
                        extra_params.get("pv_idx", "unknown"), ex)
            return None