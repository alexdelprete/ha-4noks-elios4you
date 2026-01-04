"""Constants for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.components.switch import SwitchDeviceClass
from homeassistant.const import UnitOfEnergy, UnitOfPower

# Base component constants
NAME = "4-noks Elios4you integration"
DOMAIN = "4noks_elios4you"
VERSION = "1.2.0"
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
MAX_SCAN_INTERVAL = 600
MIN_PORT = 1
MAX_PORT = 65535
CONN_TIMEOUT = 5
# Retry configuration for transient failures
COMMAND_RETRY_COUNT: int = 3  # Retry each command up to 3 times
COMMAND_RETRY_DELAY: float = 0.3  # 300ms delay between retries

# Repair notification options
CONF_ENABLE_REPAIR_NOTIFICATION = "enable_repair_notification"
CONF_FAILURES_THRESHOLD = "failures_threshold"
CONF_RECOVERY_SCRIPT = "recovery_script"
DEFAULT_ENABLE_REPAIR_NOTIFICATION = True
DEFAULT_FAILURES_THRESHOLD = 3
DEFAULT_RECOVERY_SCRIPT = ""
MIN_FAILURES_THRESHOLD = 1
MAX_FAILURES_THRESHOLD = 10

# Notification IDs
NOTIFICATION_RECOVERY = "recovery"
MANUFACTURER = "4-noks"
MODEL = "Elios4you"
STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME} - Version {VERSION}
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
# enabled_default: True = enabled by default, False = disabled by default (user can enable manually)
# F1/F2/F3 time-of-use variants and diagnostic sensors are disabled by default to reduce clutter
SENSOR_ENTITIES = [
    {
        "name": "Produced Power",
        "key": "produced_power",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Consumed Power",
        "key": "consumed_power",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Self Consumed Power",
        "key": "self_consumed_power",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Bought Power",
        "key": "bought_power",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Sold Power",
        "key": "sold_power",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Daily Peak",
        "key": "daily_peak",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Monthly Peak",
        "key": "monthly_peak",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.POWER,
        "state_class": SensorStateClass.MEASUREMENT,
        "unit": UnitOfPower.KILO_WATT,
        "enabled_default": True,
    },
    {
        "name": "Produced Energy",
        "key": "produced_energy",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": True,
    },
    {
        "name": "Produced Energy F1",
        "key": "produced_energy_f1",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Produced Energy F2",
        "key": "produced_energy_f2",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Produced Energy F3",
        "key": "produced_energy_f3",
        "icon": "mdi:solar-power-variant-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Consumed Energy",
        "key": "consumed_energy",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": True,
    },
    {
        "name": "Consumed Energy F1",
        "key": "consumed_energy_f1",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Consumed Energy F2",
        "key": "consumed_energy_f2",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Consumed Energy F3",
        "key": "consumed_energy_f3",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Self Consumed Energy",
        "key": "self_consumed_energy",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": True,
    },
    {
        "name": "Self Consumed Energy F1",
        "key": "self_consumed_energy_f1",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Self Consumed Energy F2",
        "key": "self_consumed_energy_f2",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Self Consumed Energy F3",
        "key": "self_consumed_energy_f3",
        "icon": "mdi:home-lightning-bolt-outline",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Bought Energy",
        "key": "bought_energy",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": True,
    },
    {
        "name": "Bought Energy F1",
        "key": "bought_energy_f1",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Bought Energy F2",
        "key": "bought_energy_f2",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Bought Energy F3",
        "key": "bought_energy_f3",
        "icon": "mdi:transmission-tower-export",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Sold Energy",
        "key": "sold_energy",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": True,
    },
    {
        "name": "Sold Energy F1",
        "key": "sold_energy_f1",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Sold Energy F2",
        "key": "sold_energy_f2",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Sold Energy F3",
        "key": "sold_energy_f3",
        "icon": "mdi:transmission-tower-import",
        "device_class": SensorDeviceClass.ENERGY,
        "state_class": SensorStateClass.TOTAL_INCREASING,
        "unit": UnitOfEnergy.KILO_WATT_HOUR,
        "enabled_default": False,
    },
    {
        "name": "Alarm 1",
        "key": "alarm_1",
        "icon": "mdi:alarm-light-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Alarm 2",
        "key": "alarm_2",
        "icon": "mdi:alarm-light-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Power Alarm",
        "key": "power_alarm",
        "icon": "mdi:alarm-light-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "PWM Mode",
        "key": "pwm_mode",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Power Reducer Ssv",
        "key": "pr_ssv",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Relay Ssv",
        "key": "rel_ssv",
        "icon": "mdi:toggle-switch-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Relay Mode",
        "key": "rel_mode",
        "icon": "mdi:toggle-switch-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Relay Warning",
        "key": "rel_warning",
        "icon": "mdi:alarm-light-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "RedCap",
        "key": "rcap",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Firmware TOP Version",
        "key": "fwtop",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Firmware BOTTOM Version",
        "key": "fwbtm",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Serial Number",
        "key": "sn",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Hardware Version",
        "key": "hwver",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "BT Version",
        "key": "btver",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Wifi HW Version",
        "key": "hw_wifi",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Wifi App Version",
        "key": "s2w_app_version",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Wifi Geps Version",
        "key": "s2w_geps_version",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
    {
        "name": "Wifi Wlan Version",
        "key": "s2w_wlan_version",
        "icon": "mdi:information-outline",
        "device_class": None,
        "state_class": None,
        "unit": None,
        "enabled_default": False,
    },
]
