"""Constants for 4-noks Elios4You.

https://github.com/alexdelprete/ha-4noks-elios4you
"""

from homeassistant.components.sensor import SensorDeviceClass, SensorStateClass
from homeassistant.const import (
    UnitOfPower,
)

# Base component constants
NAME = "4-noks Elios4you integration"
DOMAIN = "4noks_elios4you"
DOMAIN_DATA = f"{DOMAIN}_data"
VERSION = "1.0.0"
ATTRIBUTION = "by @alexdelprete"
ISSUE_URL = "https://github.com/alexdelprete/ha-4noks-elios4you/issues"

# Icons
ICON = "mdi:format-quote-close"

# Device classes
BINARY_SENSOR_DEVICE_CLASS = "connectivity"

# Platforms
SENSOR = "sensor"
PLATFORMS = [
    "sensor",
]
UPDATE_LISTENER = "update_listener"
DATA = "data"

# Configuration and options
CONF_NAME = "name"
CONF_HOST = "host"
CONF_PORT = "port"
CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_NAME = "Elios4you"
DEFAULT_PORT = 5001
DEFAULT_SCAN_INTERVAL = 60
MIN_SCAN_INTERVAL = 30
STARTUP_MESSAGE = f"""
-------------------------------------------------------------------
{NAME}
Version: {VERSION}
{ATTRIBUTION}
This is a custom integration!
If you have any issues with this you need to open an issue here:
{ISSUE_URL}
-------------------------------------------------------------------
"""

# Sensors for all inverters
SENSOR_TYPES = {
    "Produced_Power": [
        "Produced Power",
        "produced_power",
        UnitOfPower.WATT,
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ],
    "Consumed_Power": [
        "Consumed Power",
        "consumed_power",
        UnitOfPower.WATT,
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ],
    "Bought_Power": [
        "Bought Power",
        "bought_power",
        UnitOfPower.WATT,
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ],
    "Sold_Power": [
        "Sold Power",
        "sold_power",
        UnitOfPower.WATT,
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ],
    "Daily_Peak": [
        "Daily Peak",
        "daily_peak",
        UnitOfPower.WATT,
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ],
    "Monthly_Peak": [
        "Monthly Peak",
        "monthly_peak",
        UnitOfPower.WATT,
        "mdi:solar-power",
        SensorDeviceClass.POWER,
        SensorStateClass.MEASUREMENT,
    ],
    "Produced_Energy": [
        "Produced Energy",
        "produced_energy",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Produced_Energy_F1": [
        "Produced Energy F1",
        "produced_energy_f1",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Produced_Energy_F2": [
        "Produced Energy F2",
        "produced_energy_f2",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Produced_Energy_F3": [
        "Produced Energy F3",
        "produced_energy_f3",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Consumed_Energy": [
        "Consumed Energy",
        "consumed_energy",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Consumed_Energy_F1": [
        "Consumed Energy F1",
        "consumed_energy_f1",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Consumed_Energy_F2": [
        "Consumed Energy F2",
        "consumed_energy_f2",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Consumed_Energy_F3": [
        "Consumed Energy F3",
        "consumed_energy_f3",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Bought_Energy": [
        "Bought Energy",
        "bought_energy",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Bought_Energy_F1": [
        "Bought Energy F1",
        "bought_energy_f1",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Bought_Energy_F2": [
        "Bought Energy F2",
        "bought_energy_f2",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Bought_Energy_F3": [
        "Bought Energy F3",
        "bought_energy_f3",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Sold_Energy": [
        "Sold Energy",
        "sold_energy",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Sold_Energy_F1": [
        "Sold Energy F1",
        "sold_energy_f1",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Sold_Energy_F2": [
        "Sold Energy F2",
        "sold_energy_f2",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Sold_Energy_F3": [
        "Sold Energy F3",
        "sold_energy_f3",
        UnitOfPower.WATT_HOUR,
        "mdi:solar-power",
        SensorDeviceClass.ENERGY,
        SensorStateClass.TOTAL_INCREASING,
    ],
    "Alarm_1": [
        "Alarm 1",
        "alarm_1",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Alarm_2": [
        "Alarm 2",
        "alarm_2",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Power_Alarm": [
        "Power Alarm",
        "power_alarm",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Relay_State": [
        "Relay State",
        "relay_state",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "PWM_Mode": [
        "PWM Mode",
        "pwm_mode",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Power_Reducer_Ssv": [
        "Power Reducer Ssv",
        "pr_ssv",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Relay_Ssv": [
        "Relay Ssv",
        "rel_ssv",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Relay_Mode": [
        "Relay Mode",
        "rel_mode",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Relay_Warning": [
        "Relay Warning",
        "rel_warning",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "RedCap": [
        "RedCap",
        "rcap",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Firmware_Top_Version": [
        "Firmware TOP Version",
        "fwtop",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Firmware_Bottom_Version": [
        "Firmware BOTTOM Version",
        "fwbtm",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Serial_Number": [
        "Serial Number",
        "sn",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Hardware_Version": [
        "Hardware Version",
        "hwver",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "BT_Version": [
        "BT Version",
        "btver",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Wifi_HW_Version": [
        "Wifi HW Version",
        "hw_wifi",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Wifi_App_Version": [
        "Wifi App Version",
        "s2w_app_version",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Wifi_Geps_Version": [
        "Wifi Geps Version",
        "s2w_geps_version",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
    "Wifi_Wlan_Version": [
        "Wifi Wlan Version",
        "s2w_wlan_version",
        None,
        "mdi:information-outline",
        None,
        None,
    ],
}
