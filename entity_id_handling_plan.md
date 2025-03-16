# Implementation Plan: Using Unique IDs to Find Correct Source Entities

## Background
From the logs, we can see that the integration is looking for a source entity with ID `sensor.sigen_plant_pv_power`, but that entity doesn't exist. Instead, there's an entity with ID `sensor.sigen_plant_pv_power_2` that has data. This mismatch is causing the integration sensor to fail.

The unique ID `01JPEYGJD512B4D2F5YSA7WKXR_plant_plant_photovoltaic_power` is more stable than the entity ID and can be used to reliably find the correct entity regardless of any suffixes that might have been added to the entity ID.

## Implementation Plan

### 1. Enhance the `get_source_entity_id` Function

```python
def get_source_entity_id(hass, device_type, source_key, device_id=None, coordinator=None):
    """Get the source entity ID for a given device type and source key."""
    # ... existing code ...
    
    # New approach: Use entity registry to find entities by unique ID pattern
    entity_registry = async_get_entity_registry(hass)
    
    # Determine the base unique ID pattern we're looking for
    # For plant sensors: {config_entry_id}_plant_{key}
    # For inverter sensors: {config_entry_id}_inverter_{device_id}_{key}
    
    if coordinator and coordinator.hub and coordinator.hub.config_entry:
        config_entry_id = coordinator.hub.config_entry.entry_id
        
        # Build the pattern for the unique ID
        if device_type == DEVICE_TYPE_PLANT:
            unique_id_pattern = f"{config_entry_id}_plant_plant_"
            if "pv_power" in source_key:
                unique_id_pattern += "photovoltaic_power"
            elif "grid_import_power" in source_key:
                unique_id_pattern += "grid_import_power"
            elif "grid_export_power" in source_key:
                unique_id_pattern += "grid_export_power"
        elif device_type == DEVICE_TYPE_INVERTER and device_id is not None:
            unique_id_pattern = f"{config_entry_id}_{device_type}_{device_id}_"
            if "pv_power" in source_key:
                unique_id_pattern += "inverter_pv_power"
        
        _LOGGER.debug("Looking for entity with unique ID pattern: %s", unique_id_pattern)
        
        # Search through all entities in the registry
        matching_entities = []
        for entity_id, entity in entity_registry.entities.items():
            if entity.unique_id and unique_id_pattern in entity.unique_id:
                _LOGGER.debug("Found matching entity: %s with unique ID: %s", entity_id, entity.unique_id)
                matching_entities.append(entity_id)
        
        if matching_entities:
            # If we found matches based on unique ID, prioritize them
            _LOGGER.debug("Found %d entities matching unique ID pattern", len(matching_entities))
            return matching_entities[0]
    
    # Fall back to the existing logic if no matches found by unique ID
    # ... rest of existing code ...
```

### 2. Modify the Integration Sensor Creation

Update the integration sensor creation in `async_setup_entry` to use this enhanced function:

```python
# Add plant integration sensors
for description in SCS.PLANT_INTEGRATION_SENSORS:
    # Get the source entity ID dynamically
    source_entity_id = get_source_entity_id(
        hass=hass,
        device_type=DEVICE_TYPE_PLANT,
        source_key=description.source_entity_id,
        coordinator=coordinator
    )
    
    if source_entity_id:
        _LOGGER.debug("Creating plant integration sensor with source entity ID: %s", source_entity_id)
        entities.append(
            SigenergyIntegrationSensor(
                coordinator=coordinator,
                description=description,
                name=f"{plant_name} {description.name}",
                device_type=DEVICE_TYPE_PLANT,
                device_id=None,
                device_name=plant_name,
                source_entity_id=source_entity_id,  # Use the dynamically found entity ID
                round_digits=description.round_digits,
                max_sub_interval=description.max_sub_interval,
            )
        )
    else:
        _LOGGER.warning(
            "Could not find source entity for integration sensor %s %s",
            plant_name,
            description.name
        )
```

### 3. Similar Updates for Inverter Integration Sensors

Apply the same pattern to the inverter integration sensors:

```python
# Add inverter integration sensors
for description in SCS.INVERTER_INTEGRATION_SENSORS:
    # Get the source entity ID dynamically
    source_entity_id = get_source_entity_id(
        hass=hass,
        device_type=DEVICE_TYPE_INVERTER,
        source_key=description.source_entity_id,
        device_id=inverter_id,
        coordinator=coordinator
    )
    
    if source_entity_id:
        _LOGGER.debug("Creating inverter integration sensor with source entity ID: %s", source_entity_id)
        entities.append(
            SigenergyIntegrationSensor(
                coordinator=coordinator,
                description=description,
                name=f"{inverter_name} {description.name}",
                device_type=DEVICE_TYPE_INVERTER,
                device_id=inverter_id,
                device_name=inverter_name,
                source_entity_id=source_entity_id,  # Use the dynamically found entity ID
                round_digits=description.round_digits,
                max_sub_interval=description.max_sub_interval,
            )
        )
    else:
        _LOGGER.warning(
            "Could not find source entity for integration sensor %s %s",
            inverter_name,
            description.name
        )
```

## Benefits of This Approach

1. **Reliability**: Using unique IDs provides a more reliable way to find entities, as unique IDs are designed to be stable identifiers.

2. **Flexibility**: This approach handles cases where entity IDs have suffixes or have been renamed.

3. **Debugging**: The enhanced logging will make it easier to diagnose issues with entity resolution.

4. **Backward Compatibility**: By falling back to the existing logic, we maintain compatibility with existing setups.

## Implementation Steps

1. Update the `get_source_entity_id` function to include the unique ID-based lookup.
2. Modify the integration sensor creation code to use the enhanced function.
3. Add appropriate logging to track the entity resolution process.
4. Test with various configurations to ensure it works correctly.

## Mermaid Diagram of Entity Resolution Process

```mermaid
flowchart TD
    A[Start Entity Resolution] --> B{Check if coordinator available}
    B -->|Yes| C[Get config_entry_id]
    B -->|No| G[Fall back to existing logic]
    C --> D[Build unique_id_pattern based on device_type]
    D --> E[Search entity registry for matching unique_ids]
    E --> F{Found matches?}
    F -->|Yes| H[Return first matching entity_id]
    F -->|No| G
    G --> I[Search for entities by name patterns]
    I --> J{Found exact matches?}
    J -->|Yes| K[Return first exact match]
    J -->|No| L{Found pattern matches?}
    L -->|Yes| M[Return first pattern match]
    L -->|No| N{Found fallback matches?}
    N -->|Yes| O[Return first fallback match]
    N -->|No| P[Return None]