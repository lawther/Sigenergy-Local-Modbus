"""Test script for integration sensors."""
import asyncio
import logging
from datetime import datetime, timedelta
from decimal import Decimal

from homeassistant.const import STATE_UNAVAILABLE, STATE_UNKNOWN
from homeassistant.core import HomeAssistant, State
from homeassistant.util import dt as dt_util

from .calculated_sensor import SigenergyIntegrationSensor

_LOGGER = logging.getLogger(__name__)

async def test_integration_sensor(hass: HomeAssistant):
    """Test the integration sensor."""
    # Create a mock coordinator
    class MockCoordinator:
        def __init__(self):
            self.hub = type('obj', (object,), {
                'config_entry': type('obj', (object,), {
                    'entry_id': 'test_entry_id'
                })
            })
            self.data = {}
    
    coordinator = MockCoordinator()
    
    # Create a test sensor
    sensor = SigenergyIntegrationSensor(
        coordinator=coordinator,
        description=type('obj', (object,), {
            'key': 'test_sensor',
            'name': 'Test Sensor',
        }),
        name="Test Integration Sensor",
        device_type="plant",
        device_id=None,
        device_name="Test Plant",
        source_entity_id="sensor.test_power",
        round_digits=3,
        max_sub_interval=timedelta(seconds=30),
    )
    
    # Test state restoration
    sensor._state = Decimal('10.5')
    assert sensor.native_value == Decimal('10.500')
    
    # Test trapezoidal integration
    old_state = State(
        entity_id="sensor.test_power",
        state="5.0",
        last_updated=dt_util.utcnow() - timedelta(seconds=10),
    )
    new_state = State(
        entity_id="sensor.test_power",
        state="10.0",
        last_updated=dt_util.utcnow(),
    )
    
    # Simulate state change
    sensor._integrate_on_state_change(old_state, new_state)
    
    # Expected calculation: (5.0 + 10.0) / 2 * 10 seconds / 3600 = 0.0208333... kWh
    expected = Decimal('10.5') + (Decimal('5.0') + Decimal('10.0')) / Decimal('2') * Decimal('10') / Decimal('3600')
    assert abs(sensor.native_value - expected) < Decimal('0.001')
    
    # Test zero values
    old_state = State(
        entity_id="sensor.test_power",
        state="0.0",
        last_updated=dt_util.utcnow() - timedelta(seconds=10),
    )
    new_state = State(
        entity_id="sensor.test_power",
        state="0.0",
        last_updated=dt_util.utcnow(),
    )
    
    # Save current value
    previous_value = sensor.native_value
    
    # Simulate state change with zero values
    sensor._integrate_on_state_change(old_state, new_state)
    
    # Expected: no change since power is zero
    assert sensor.native_value == previous_value
    
    # Test unavailable state
    new_state = State(
        entity_id="sensor.test_power",
        state=STATE_UNAVAILABLE,
        last_updated=dt_util.utcnow(),
    )
    
    # Simulate state change with unavailable state
    sensor._integrate_on_state_change(old_state, new_state)
    
    # Expected: sensor should be unavailable
    assert sensor._attr_available is False
    
    # Test max_sub_interval
    # This is harder to test directly, but we can verify the callback is scheduled
    old_state = State(
        entity_id="sensor.test_power",
        state="5.0",
        last_updated=dt_util.utcnow() - timedelta(seconds=10),
    )
    new_state = State(
        entity_id="sensor.test_power",
        state="5.0",
        last_updated=dt_util.utcnow(),
    )
    
    # Mock the async_call_later function
    called = False
    def mock_async_call_later(hass, interval, callback):
        nonlocal called
        called = True
        return lambda: None
    
    # Replace the async_call_later function
    original_async_call_later = sensor.hass.helpers.event.async_call_later
    sensor.hass.helpers.event.async_call_later = mock_async_call_later
    
    # Schedule the callback
    sensor._schedule_max_sub_interval_exceeded_if_state_is_numeric(new_state)
    
    # Verify the callback was scheduled
    assert called is True
    
    # Restore the original function
    sensor.hass.helpers.event.async_call_later = original_async_call_later
    
    _LOGGER.info("All tests passed!")

if __name__ == "__main__":
    asyncio.run(test_integration_sensor(HomeAssistant()))