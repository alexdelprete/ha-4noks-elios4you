# HA Custom Component for 4-noks Elios4you energy monitoring device

<!-- BEGIN SHARED:repo-sync:badges -->
<!-- Synced by repo-sync on 2026-02-10 -->
[![GitHub Release](https://img.shields.io/github/v/release/alexdelprete/ha-4noks-elios4you?style=for-the-badge)](https://github.com/alexdelprete/ha-4noks-elios4you/releases)
[![Buy Me A Coffee](https://img.shields.io/badge/Buy%20Me%20A%20Coffee-donate-yellow?style=for-the-badge&logo=buy-me-a-coffee)](https://www.buymeacoffee.com/alexdelprete)
[![Tests](https://img.shields.io/github/actions/workflow/status/alexdelprete/ha-4noks-elios4you/test.yml?style=for-the-badge&label=Tests)](https://github.com/alexdelprete/ha-4noks-elios4you/actions/workflows/test.yml)
[![Coverage](https://img.shields.io/codecov/c/github/alexdelprete/ha-4noks-elios4you?style=for-the-badge)](https://codecov.io/gh/alexdelprete/ha-4noks-elios4you)
[![GitHub Downloads](https://img.shields.io/github/downloads/alexdelprete/ha-4noks-elios4you/total?style=for-the-badge)](https://github.com/alexdelprete/ha-4noks-elios4you/releases)

<!-- END SHARED:repo-sync:badges -->

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

<!-- BEGIN SHARED:repo-sync:installation -->
<!-- Synced by repo-sync on 2026-02-10 -->
## Installation

### HACS (Recommended)

1. Open HACS in your Home Assistant instance
1. Click on "Integrations"
1. Click the three dots menu in the top right corner
1. Select "Custom repositories"
1. Add `https://github.com/alexdelprete/ha-4noks-elios4you` as an Integration
1. Click "Download" and install the integration
1. Restart Home Assistant

### Manual Installation

1. Download the latest release from [GitHub Releases](https://github.com/alexdelprete/ha-4noks-elios4you/releases)
1. Extract the `custom_components/4noks_elios4you` folder
1. Copy it to your Home Assistant `config/custom_components/` directory
1. Restart Home Assistant

<!-- END SHARED:repo-sync:installation -->

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

#### Recovery Script

You can configure a script that automatically runs when the device becomes unreachable. This is useful for automated recovery actions like restarting your WiFi router or power-cycling network equipment.

**Setup:**
1. Create a script in Home Assistant (e.g., `script.restart_wifi`)
2. In the integration's Options flow, select the script from the dropdown
3. When failures exceed the threshold, the script will execute automatically

**Available Variables:**

The script receives these variables that you can use in your automation:

| Variable | Description | Example |
|----------|-------------|---------|
| `device_name` | The configured device name | "Elios4you Pro" |
| `host` | IP address or hostname | "192.168.1.100" |
| `port` | TCP port number | 5001 |
| `serial_number` | Device serial number | "E4U123456789" |
| `mac_address` | Device MAC address | "AA:BB:CC:DD:EE:FF" |
| `failures_count` | Number of consecutive failures | 3 |

**Example Script:**

```yaml
script:
  restart_elios_wifi:
    alias: "Restart Elios WiFi AP"
    sequence:
      - service: switch.turn_off
        target:
          entity_id: switch.wifi_ap_power
      - delay:
          seconds: 10
      - service: switch.turn_on
        target:
          entity_id: switch.wifi_ap_power
      - service: notify.mobile_app
        data:
          title: "Elios4you Recovery"
          message: "Restarted WiFi AP for {{ device_name }} after {{ failures_count }} failures"
```

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

### Getting the Full Debug Log

When reporting issues, a full debug log is essential for diagnosis. Follow these steps to capture a complete log:

#### Step 1: Enable Debug Logging

Add the logger configuration above to your `configuration.yaml` file, then restart Home Assistant.

#### Step 2: Reproduce the Issue

After restart, wait for the issue to occur or manually trigger it. For connection problems, this usually happens within 1-2 polling cycles (60-120 seconds by default).

#### Step 3: Download the Full Log

**Method A: Via Home Assistant UI**

1. Go to **Settings > System > Logs**
2. Click the **Download Full Log** button (top right corner)
3. Save the `home-assistant.log` file

**Method B: Direct File Access**

Access the log file directly from your Home Assistant config directory:

- **Home Assistant OS/Supervised**: `/config/home-assistant.log`
- **Docker**: `<config_mount>/home-assistant.log`
- **Core**: `~/.homeassistant/home-assistant.log`

#### Step 4: Filter Relevant Entries

The full log contains entries from all integrations. To extract only Elios4you entries:

**Linux/macOS:**

```bash
grep "4noks_elios4you" home-assistant.log > elios4you_debug.log
```

**Windows PowerShell:**

```powershell
Select-String -Path home-assistant.log -Pattern "4noks_elios4you" | Out-File elios4you_debug.log
```

**Windows Command Prompt:**

```cmd
findstr "4noks_elios4you" home-assistant.log > elios4you_debug.log
```

#### Understanding Log Messages

The integration uses structured logging with this format:

```
(function_name) [context_key=value]: message
```

**Example log entries:**

```
DEBUG (async_get_data) [host=192.168.1.100, port=5001]: Fetching data from device
DEBUG (_async_send_command) [cmd=@dat]: Sending command
ERROR (async_get_data) [host=192.168.1.100]: TelnetConnectionError - Connection timed out
```

**Key functions to look for:**

| Function | What it logs |
|----------|--------------|
| `async_get_data` | Data polling cycles |
| `_ensure_connected` | Connection establishment |
| `_async_send_command` | Telnet command execution |
| `_safe_close` | Connection cleanup |
| `telnet_set_relay` | Relay switch commands |
| `async_setup_entry` | Integration startup |
| `async_unload_entry` | Integration shutdown |

#### Temporary Debug Logging (No Restart Required)

For quick debugging without restarting, use the **Logger** integration service:

1. Go to **Developer Tools > Services**
2. Select service: `logger.set_level`
3. Enter this YAML:

```yaml
service: logger.set_level
data:
  custom_components.4noks_elios4you: debug
```

4. Click **Call Service**

Debug logging is now enabled until the next restart. To disable:

```yaml
service: logger.set_level
data:
  custom_components.4noks_elios4you: info
```

### Repair Notifications

The integration uses Home Assistant's repair system to notify you of connection issues. If the device becomes unreachable, you'll see a repair notification in **Settings > System > Repairs** with troubleshooting steps.

### Common Issues

#### Sensors Show "Unavailable"

**Cause:** The device is not responding to telnet commands.

**Solutions:**

1. Verify the device is powered on and connected to the network
2. Check that the IP address is correct in the integration configuration
3. Ensure no firewall is blocking port 5001
4. Try pinging the device: `ping <device_ip>`
5. Verify the device's WiFi connection is stable

#### Device Becomes "Deaf" Periodically

**Cause:** The device's embedded system can become overwhelmed by too many connections.

**Solutions:**

1. Ensure only one integration instance is polling the device
2. Close the official Elios4you mobile app when not in use
3. Increase the polling interval to 120 seconds or more in Options
4. Configure a recovery script to restart your WiFi access point

#### Connection Errors After HA Restart

**Cause:** The device may have stale connections from the previous session.

**Solutions:**

1. Wait 2-3 minutes for old connections to time out
2. If issues persist, power cycle the Elios4you device
3. Check for other services polling the device (Node-RED, etc.)

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

<!-- BEGIN SHARED:repo-sync:contributing -->
<!-- Synced by repo-sync on 2026-02-10 -->
## Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
1. Create a feature branch (`git checkout -b feature/my-feature`)
1. Make your changes
1. Run linting: `uvx pre-commit run --all-files`
1. Commit your changes (`git commit -m "feat: add my feature"`)
1. Push to your branch (`git push origin feature/my-feature`)
1. Open a Pull Request

Please ensure all CI checks pass before requesting a review.

<!-- END SHARED:repo-sync:contributing -->

## Coffee

_If you like this integration, I'll gladly accept some quality coffee, but please don't feel obliged._ :)

[![BuyMeCoffee][buymecoffee-button]][buymecoffee]

<!-- BEGIN SHARED:repo-sync:license -->
<!-- Synced by repo-sync on 2026-02-10 -->
## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

<!-- END SHARED:repo-sync:license -->

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
