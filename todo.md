- Uncomment developer commented out checks for duplicates
- Check all sensors and such on yaml integration are available here.
- Check name on all sensors and such if can be same as yaml

- Add slow and fast update intervall and have slow as default while fast for acumulative values.
- Check if dc_charger_start_stop is getting right state. running state?
- Fix so no duplicate checks in dev mode.
- Add "Sigen x DC Charger y" to fileds such as Power.

- Recheck availability all sensors each 360th check. This is 30 min whith default interval of 5s.
- Slow sensors are checked every x times the normal sensors are checked 2-10
- All sensors are rechecked for data after an update to sliders, number, switch.

- Add name if Inverter, AC Charger or Unknown(111.111.1.1)
- Add setting for update interval for alarm, medium and low.
- add update frequency logic.