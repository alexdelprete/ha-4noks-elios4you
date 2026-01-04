# HA Custom Component for 4-noks Elios4you energy monitoring device

[![GitHub Release][releases-shield]][releases]
[![BuyMeCoffee][buymecoffee-shield]][buymecoffee]
[![Community Forum][forum-shield]][forum]

[![Tests][tests-shield]][tests]
[![Code Coverage][coverage-shield]][coverage]
[![Downloads][downloads-shield]][downloads]

_This project is not endorsed by, directly affiliated with, maintained, authorized, or sponsored by 4-noks / Astrel Group_

# Introduction

HA Custom Component to integrate data from [4-noks Elios4you](https://www.4-noks.com/product-categories/solar-photovoltaic-en/elios4you-en/?lang=en) products.
Tested personally on my [Elios4you Pro](https://www.4-noks.com/shop/elios4you-en/elios4you-pro/?lang=en) to monitor tha main 3-phase 6kw line, plus my 7.5kW photovoltaic system.

![image](https://github.com/alexdelprete/ha-4noks-elios4you/assets/7027842/70bb7791-8d01-4fc2-bef6-9a9110558c0b)

Elio4you is a great product, it provides very reliable measurements, but it has no documented local API to get the energy data. Luckily, 3y ago I found [this great article](https://www.hackster.io/daveVertu/reverse-engineering-elios4you-photovoltaic-monitoring-device-458aa0) by Davide Vertuani, that reversed-engineered how the official mobile app communicated with the device to fetch data, and found out it's a tcp connection on port 5001, through which the app sent specific commands to which the device replies with data. That was a great find by Davide, and I initially used Node-RED to create a quick integration like Davide suggested in the article: I completed a full integration in 1 day and was rock solid, Node-RED is fantastic. :)

![image](https://github.com/alexdelprete/ha-4noks-elios4you/assets/7027842/46eb022f-1da0-48eb-ad70-46832bfa2f4e)

One month ago I decided to port the Node-RED integration to an HA Custom Component, because in the last 2 years I developed my first HA component to monitor ABB/FIMER inverters, and now I'm quite knowledgable on custom component developement (learned a lot thanks to the dev community and studying some excellent integrations).

So finally here we are with the first official version of the HA custom integration for Elios4you devices. :)

### Features

- Installation/Configuration through Config Flow UI
- Sensor entities for all data provided by the device (I don't even know what some of the ones in the diagnostic category specifically represent)
- Switch entity to control the device internal relay
- Configuration options: Name, hostname, tcp port, polling period
- Options flow: change polling period at runtime without restart
- Reconfigure flow: change connection settings (name, host, port) with automatic reload
- Repair notifications: connection issues are surfaced in Home Assistant's repair system
- Enhanced recovery notifications: detailed timing info (downtime, script execution) with persistent acknowledgment
- Device triggers: automate based on device connection events (unreachable, not responding, recovered)
- Diagnostics: downloadable diagnostics file for troubleshooting

### Technical Architecture

This integration uses a fully async telnet implementation via `telnetlib3` to communicate with the Elios4you device:

- **Async I/O**: All telnet operations are fully async, preventing Home Assistant event loop blocking
- **Connection Pooling**: Connections are reused for up to 25 seconds to prevent socket exhaustion on the embedded device
- **Command Retry**: Failed commands are retried up to 3 times with 300ms delay for resilience
- **Race Condition Prevention**: `asyncio.Lock` serializes all telnet operations between polling and switch commands
- **Graceful Error Handling**: Custom exceptions (`TelnetConnectionError`, `TelnetCommandError`) provide clear error context

### Known Limitations

- **Single device per integration instance**: Each Elios4you device requires a separate integration instance. To monitor multiple devices, add the integration multiple times.

# Installation through HACS

This integration is available in [HACS][hacs] official repository. Click this button to open HA directly on the integration page so you can easily install it:

[![Quick installation link](https://my.home-assistant.io/badges/hacs_repository.svg)][my-hacs]

1. Either click the button above, or navigate to HACS in Home Assistant and:
   - 'Explore & Download Repositories'
   - Search for '4-noks Elios4You'
   - Download
2. Restart Home Assistant
3. Go to Settings > Devices and Services > Add Integration
4. Search for and select '4-noks Elios4You' (if the integration is not found, do a hard-refresh (ctrl+F5) in the browser)
5. Proceed with the configuration

# Manual Installation

Download the source code archive from the release page. Unpack the archive and copy the contents of custom_components folder to your home-assistant config/custom_components folder. Restart Home Assistant, and then the integration can be added and configured through the native integration setup UI. If you don't see it in the native integrations list, press ctrl-F5 to refresh the browser while you're on that page and retry.

# Configuration

Configuration is done via config flow right after adding the integration. The integration provides two ways to modify settings after initial setup:

### Options Flow (Configure button)
Change runtime options without restarting Home Assistant:

| Option | Description | Default |
|--------|-------------|---------|
| **Recovery script** | Optional script to execute when device stops responding. Useful for automated recovery actions like restarting your WiFi router. Available variables: `device_name`, `host`, `port` | None |
| **Enable repair notifications** | Show persistent notifications when device recovers from failures | Enabled |
| **Failures before notification** | Number of consecutive failures before triggering repair notification (1-10) | 3 |
| **Polling period** | Frequency in seconds to read data and update sensors (30-600) | 60 |

#### Recovery Script Example

You can configure a script that automatically runs when the device becomes unreachable. For example, to restart your WiFi access point:

1. Create a script in Home Assistant (e.g., `script.restart_wifi`)
2. In the integration's Options flow, select the script from the dropdown
3. When failures exceed the threshold, the script will execute automatically

The script receives these variables:
- `device_name` - The configured device name
- `host` - The device IP address  
- `port` - The device TCP port

### Reconfigure Flow (3-dot menu > Reconfigure)
Change connection settings - the integration will automatically reload:
- **Custom name**: custom name for the device, used as prefix for sensors created by the component
- **IP/hostname**: IP/hostname of the device - this is used as unique_id, if you change it you will lose historical data (tip: use hostname so you can change IP without losing data)
- **TCP port**: TCP port of the device. tcp/5001 is the only known working port, but left configurable

<img style="border: 5px solid #767676;border-radius: 10px;max-width: 500px;width: 50%;box-sizing: border-box;" src="https://github.com/alexdelprete/ha-4noks-elios4you/assets/7027842/cbe045c6-8753-4c52-9d50-97de983d18b0" alt="Config">

# Sensor view
<img style="border: 5px solid #767676;border-radius: 10px;max-width: 500px;width: 75%;box-sizing: border-box;" src="https://raw.githubusercontent.com/alexdelprete/ha-4noks-elios4you/master/gfxfiles/elios4you_sensors.gif" alt="Config">

# Device Triggers

The integration provides device triggers that allow you to create automations based on device connection events. These triggers fire when the Elios4you device experiences connectivity issues or recovers from them.

### Available Triggers

| Trigger | Description |
|---------|-------------|
| **Device unreachable** | Fires when the device cannot be reached on the network (TCP connection failed) |
| **Device not responding** | Fires when the device is reachable but not responding to telnet commands |
| **Device recovered** | Fires when the device starts responding again after a failure |

### How to Use Device Triggers

1. Go to **Settings > Automations & Scenes > Create Automation**
2. Click **Add Trigger** and select **Device**
3. Select your Elios4you device
4. Choose from the available triggers (e.g., "Device unreachable")

### Device Trigger Automation Example

Get notified when your Elios4you device goes offline and comes back online:

```yaml
automation:
  - alias: "Elios4you Device Offline Alert"
    trigger:
      - platform: device
        domain: 4noks_elios4you
        device_id: YOUR_DEVICE_ID
        type: device_unreachable
    action:
      - service: notify.mobile_app
        data:
          title: "Elios4you Offline"
          message: "The Elios4you device is unreachable. Check network connection."

  - alias: "Elios4you Device Recovered"
    trigger:
      - platform: device
        domain: 4noks_elios4you
        device_id: YOUR_DEVICE_ID
        type: device_recovered
    action:
      - service: notify.mobile_app
        data:
          title: "Elios4you Online"
          message: "The Elios4you device is back online and responding."
```

### Recovery Notifications

When the device recovers from a failure, the integration creates a persistent repair notification with detailed timing information:

- **Failure started**: When the issue began
- **Script executed**: When the recovery script ran (if configured in options)
- **Recovery time**: When the device became responsive again
- **Total downtime**: Duration of the outage (e.g., "5m 23s")

These notifications appear in **Settings > System > Repairs** and require user acknowledgment to dismiss.

# Automation Examples

Here are some practical automation examples using the Elios4you sensors.

### Solar Production Alert

Get notified when your solar panels start producing energy in the morning:

```yaml
automation:
  - alias: "Solar Production Started"
    trigger:
      - platform: numeric_state
        entity_id: sensor.elios4you_produced_power
        above: 0.1
    condition:
      - condition: sun
        after: sunrise
    action:
      - service: notify.mobile_app
        data:
          title: "Solar Production"
          message: "Solar panels are now producing {{ states('sensor.elios4you_produced_power') }} kW"
```

### High Power Consumption Warning

Alert when power consumption exceeds a threshold:

```yaml
automation:
  - alias: "High Power Consumption Alert"
    trigger:
      - platform: numeric_state
        entity_id: sensor.elios4you_consumed_power
        above: 5.0
        for:
          minutes: 5
    action:
      - service: notify.mobile_app
        data:
          title: "High Power Usage"
          message: "Power consumption is {{ states('sensor.elios4you_consumed_power') }} kW for 5 minutes"
```

### Energy Dashboard Integration

Add sensors to the Home Assistant Energy Dashboard:

1. Go to **Settings > Dashboards > Energy**
2. Under "Solar Panels", add `sensor.elios4you_produced_energy`
3. Under "Grid consumption", add `sensor.elios4you_bought_energy`
4. Under "Return to grid", add `sensor.elios4you_sold_energy`

### Daily Energy Summary

Send a daily summary of energy production and consumption:

```yaml
automation:
  - alias: "Daily Energy Summary"
    trigger:
      - platform: time
        at: "21:00:00"
    action:
      - service: notify.mobile_app
        data:
          title: "Daily Energy Report"
          message: >
            Today's peak: {{ states('sensor.elios4you_daily_peak') }} kW
            Self-consumption: {{ states('sensor.elios4you_self_consumed_power') }} kW
```

### Relay Control Based on Production

Automatically enable the relay when solar production exceeds consumption:

```yaml
automation:
  - alias: "Enable Relay on Excess Solar"
    trigger:
      - platform: template
        value_template: >
          {{ states('sensor.elios4you_produced_power') | float >
             states('sensor.elios4you_consumed_power') | float + 1.0 }}
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.elios4you_relay

  - alias: "Disable Relay on Low Solar"
    trigger:
      - platform: template
        value_template: >
          {{ states('sensor.elios4you_produced_power') | float <
             states('sensor.elios4you_consumed_power') | float }}
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.elios4you_relay
```

## Troubleshooting

### Enabling Debug Logging

Add this to your `configuration.yaml` to enable debug logging:

```yaml
logger:
  default: info
  logs:
    custom_components.4noks_elios4you: debug
```

Restart Home Assistant and check the logs in **Settings > System > Logs**.

### Repair Notifications

The integration uses Home Assistant's repair system to notify you of connection issues. If the device becomes unreachable, you'll see a repair notification in **Settings > System > Repairs** with troubleshooting steps.

### Opening an Issue

If you encounter problems, please open an issue on GitHub with:

1. **Debug logs** - Enable debug logging (see above) and capture relevant log entries
2. **Diagnostics file** - Download from **Settings > Devices & Services > 4-noks Elios4you > 3-dot menu > Download diagnostics**
3. **Home Assistant version** - Found in **Settings > About**
4. **Integration version** - Found in **HACS > 4-noks Elios4you**
5. **Problem description** - What you expected vs what happened

[Open an issue on GitHub](https://github.com/alexdelprete/ha-4noks-elios4you/issues/new)

## Development

This project uses a comprehensive test suite with 98% code coverage:

```bash
# Install development dependencies
pip install -e ".[dev]"

# Run tests with coverage
pytest tests/ --cov=custom_components/4noks_elios4you --cov-report=term-missing -v

# Run linting
ruff format .
ruff check . --fix
```

**CI/CD Workflows:**

- **Tests**: Runs pytest with coverage on every push/PR to master
- **Lint**: Runs ruff format, ruff check, and ty type checker
- **Validate**: Runs hassfest and HACS validation
- **Release**: Automatically creates ZIP on GitHub release publish

## Coffee

_If you like this integration, I'll gladly accept some quality coffee, but please don't feel obliged._ :)

[![BuyMeCoffee][buymecoffee-button]][buymecoffee]

---

[buymecoffee]: https://www.buymeacoffee.com/alexdelprete
[buymecoffee-shield]: https://img.shields.io/badge/buy%20me%20a%20coffee-donate-white?style=for-the-badge&logo=buymeacoffee&logoColor=white
[buymecoffee-button]: https://img.buymeacoffee.com/button-api/?text=Buy%20me%20a%20coffee&emoji=☕&slug=alexdelprete&button_colour=FFDD00&font_colour=000000&font_family=Lato&outline_colour=000000&coffee_colour=ffffff
[hacs]: https://hacs.xyz
[my-hacs]: https://my.home-assistant.io/redirect/hacs_repository/?owner=alexdelprete&repository=ha-4noks-elios4you&category=integration
[forum-shield]: https://img.shields.io/badge/community-forum-darkred?style=for-the-badge
[forum]: https://community.home-assistant.io/t/custom-component-4-noks-elios4you-data-integration/692883?u=alexdelprete
[releases-shield]: https://img.shields.io/github/v/release/alexdelprete/ha-4noks-elios4you?style=for-the-badge&color=darkgreen
[releases]: https://github.com/alexdelprete/ha-4noks-elios4you/releases
[tests-shield]: https://img.shields.io/github/actions/workflow/status/alexdelprete/ha-4noks-elios4you/test.yml?style=for-the-badge&label=Tests
[tests]: https://github.com/alexdelprete/ha-4noks-elios4you/actions/workflows/test.yml
[coverage-shield]: https://img.shields.io/codecov/c/github/alexdelprete/ha-4noks-elios4you?style=for-the-badge&token=BWMCFFPJ9J
[coverage]: https://codecov.io/github/alexdelprete/ha-4noks-elios4you
[downloads-shield]: https://img.shields.io/github/downloads/alexdelprete/ha-4noks-elios4you/total?style=for-the-badge
[downloads]: https://github.com/alexdelprete/ha-4noks-elios4you/releases
