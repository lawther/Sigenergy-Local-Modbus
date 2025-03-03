# Plant Configuration Update Plan

## 1. Update the Initial Configuration (Plant Setup)
- **Prompt for Inverter Addresses:**  
  In the existing configuration form (e.g. in the `async_step_user` method of `config_flow.py`), add a new field to capture inverter slave IDs.
  - Use a comma-separated text input that will be parsed into an array of integers.
  - Optionally use a dynamic multi-entry approach.

- **Validation:**  
  - Ensure each submitted value is a positive integer between 1 and 246.
  - Check for duplicates and enforce validity.

- **Configuration Storage:**  
  - Save this data into a configuration attribute (e.g., `inverter_slave_ids`) as an array of integers.

## 2. Implement `async_step_reconfigure` for Dynamic Updates
- **Purpose:**  
  To allow users to add, remove, or modify inverter slave IDs after the initial setup.

- **Steps:**  
  - Create a new method `async_step_reconfigure` in `config_flow.py`.
  - Display a form pre-populated with the current `inverter_slave_ids`.
  - Allow modifications (using a comma-separated text input).
  - Parse and validate input similarly to the initial setup.
  - Use Home Assistant’s config entry update API to apply changes.

## 3. Flow Diagram of the Process

```mermaid
flowchart TD
    A[User Starts Setup (async_step_user)]
    B[Show Form with Existing Fields]
    C[Prompt for inverter_slave_ids (comma-separated list)]
    D[Parse and Validate Inverter Slave IDs]
    E[Save Initial Config Entry]
    F[User Initiates Reconfiguration (async_step_reconfigure)]
    G[Display Existing inverter_slave_ids in Form]
    H[User Adds/Removes/Modifies Inverter IDs]
    I[Parse and Validate Updated IDs]
    J[Update and Save Config Entry]

    A --> B
    B --> C
    C --> D
    D --> E
    E --> F
    F --> G
    G --> H
    H --> I
    I --> J