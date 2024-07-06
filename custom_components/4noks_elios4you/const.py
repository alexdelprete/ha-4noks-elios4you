"""Constants for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfPower

# Base component constants
NAME = "4-noks Elios4you integration"
DOMAIN = "4noks_elios4you"
ATTRIBUTION = "by @alexdelprete"
ISSUE_URL = "https://github.com/alexdelprete/ha-4noks-elios4you/issues"

# Configuration and options
CONF_NAME = "name"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_NAME = "Elios4you"
DEFAULT_PORT = 5001
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30
CONN_TIMEOUT = 5
MANUFACTURER = "4-noks"
MODEL = "Elios4you"
STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
{ATTRIBUTION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# Switch definitions

SWITCH_ENTITIES = [
    {
        "name": "Relay",
        "key": "relay_state",
        "icon": "mdi:toggle-switch-outline",
        "device_class": SwitchDeviceClass.SWITCH,
    },
]

# Sensor definitions
SENSOR_ENTITIES = [
    {
        "name": "Produced Power",
        "key": "produced_power",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
    },
    {
        "name": "Consumed Power",
        "key": "consumed_power",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
    },
    {
        "name": "Self Consumed Power",
        "key": "self_consumed_power",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
    },
    {
        "name": "Bought Power",
        "key": "bought_power",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
    },
    {
        "name": "Sold Power",
        "key": "sold_power",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
    },
    {
        "name": "Daily Peak",
        "key": "daily_peak",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
    },
    {
        "name": "Monthly Peak",
        "key": "monthly_peak",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
    },
    {
        "name": "Produced Energy",
        "key": "produced_energy",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Produced Energy F1",
        "key": "produced_energy_f1",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Produced Energy F2",
        "key": "produced_energy_f2",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Produced Energy F3",
        "key": "produced_energy_f3",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Consumed Energy",
        "key": "consumed_energy",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Consumed Energy F1",
        "key": "consumed_energy_f1",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Consumed Energy F2",
        "key": "consumed_energy_f2",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Consumed Energy F3",
        "key": "consumed_energy_f3",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Self Consumed Energy",
        "key": "self_consumed_energy",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Self Consumed Energy F1",
        "key": "self_consumed_energy_f1",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Self Consumed Energy F2",
        "key": "self_consumed_energy_f2",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Self Consumed Energy F3",
        "key": "self_consumed_energy_f3",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Bought Energy",
        "key": "bought_energy",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Bought Energy F1",
        "key": "bought_energy_f1",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Bought Energy F2",
        "key": "bought_energy_f2",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Bought Energy F3",
        "key": "bought_energy_f3",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Sold Energy",
        "key": "sold_energy",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Sold Energy F1",
        "key": "sold_energy_f1",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Sold Energy F2",
        "key": "sold_energy_f2",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Sold Energy F3",
        "key": "sold_energy_f3",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
    },
    {
        "name": "Alarm 1",
        "key": "alarm_1",
        "icon": "mdi:alarm-light-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Alarm 2",
        "key": "alarm_2",
        "icon": "mdi:alarm-light-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Power Alarm",
        "key": "power_alarm",
        "icon": "mdi:alarm-light-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "PWM Mode",
        "key": "pwm_mode",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Power Reducer Ssv",
        "key": "pr_ssv",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Relay Ssv",
        "key": "rel_ssv",
        "icon": "mdi:toggle-switch-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Relay Mode",
        "key": "rel_mode",
        "icon": "mdi:toggle-switch-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Relay Warning",
        "key": "rel_warning",
        "icon": "mdi:alarm-light-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "RedCap",
        "key": "rcap",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Firmware TOP Version",
        "key": "fwtop",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Firmware BOTTOM Version",
        "key": "fwbtm",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Serial Number",
        "key": "sn",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Hardware Version",
        "key": "hwver",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "BT Version",
        "key": "btver",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Wifi HW Version",
        "key": "hw_wifi",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Wifi App Version",
        "key": "s2w_app_version",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Wifi Geps Version",
        "key": "s2w_geps_version",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
    {
        "name": "Wifi Wlan Version",
        "key": "s2w_wlan_version",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
    },
]
