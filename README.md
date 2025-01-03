# HomeWhiz Integration for Home Assistant

![HomeWhiz icon](./icons/icon.png)

Integration for devices that support the HomeWhiz mobile app (Beko, Grundig, Arcelik)

## Installation

⚠️ This integration depends on the awscrt Python package. This package is not directly available for ARM devices with 32 bit OS. More information can be found [here](https://github.com/home-assistant-HomeWhiz/home-assistant-HomeWhiz/issues/97).

### Option 1. Using HACS (Recommended)

1. Search for `HomeWhiz` on the HACS integration page (this integration is part of the HACS default repository meaning it is not necessary to add this integration manually via custom repositories)
2. Install the integration and Restart Home Assistant

### Option 2. Manually

1. Using the tool of choice, open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory there, you need to create it.
3. In the `custom_components` directory create a new folder called `homewhiz`.
4. Download _all_ files from the `custom_components/homewhiz/` directory in this repository.
5. Place the files you downloaded in the new directory you created.
6. Restart Home Assistant

## Configuration

### Bluetooth

1. Connect the device to the HomeWhiz app on your smartphone
2. Close the app
3. In the HA UI go to "Configuration" -> "Integrations". The device should be automatically discovered. If it's not click "+" and search for "HomeWhiz"
4. Select the "Bluetooth" connection type
5. Provide the HomeWhiz username and password. These will be used to fetch your device mapping from the HomeWhiz API during configuration. No internet connection is required after the initial configuration.

### Wi-Fi

1. Connect the device to the HomeWhiz app on your smartphone
2. In the HA UI go to "Configuration" -> "Integrations". Click "+" and search for "HomeWhiz"
3. Select the "Cloud" connection type
4. Provide the HomeWhiz username and password.

Please note that the constant internet connection is required. 

## Supported device types

| Device           | Supported          | Comments                                           |
| ---------------- | ------------------ | -------------------------------------------------- |
| Washing machines | :heavy_check_mark: | Also includes washing machine / dryer combinations |
| Dryer            | :heavy_check_mark: | Also includes washing machine / dryer combinations |
| Dishwasher       | :heavy_check_mark: |                                                    |
| Air conditioner  | :heavy_check_mark: |                                                    |
| Extraction fan   | :heavy_check_mark: |                                                    |
| Oven             | :question: :x:     | Not tested                                         |

If you have other device types not listed yet, please let us know.

If your device is missing some information, translations or not working at all, please create an issue.
Don't forget to include your device digital ID that can be found either in the HomeWhiz app or the integration logs.

## Troubleshooting

### Bluetooth
The integration should work with all devices connected via Bluetooth. Remember that the range of Bluetooth is limited. If your device is out of range, try using an [ESPHome Bluetooth Proxy](https://esphome.github.io/bluetooth-proxies/).

If you are using custom Home Assistant installation method like virtual machine, please make sure your system is configured properly and Bluetooth is available within Home Assistant.

The devices can support only single Bluetooth connections at a time.
To connect the device to the original app, you have to disable the Home Assistant integration. Restart Home Assistant and wait a few minutes - this should be indicated on the device: E.g. the Bluetooth icon on a washing machine starts flashing.

### Retrieve Integration Logs

To help us help you, please include integration logs when you submit issues. The integration supports multiple logging levels of which not all are shown in the Home Assistant log by default. To enable debug logging for this integration, please add the following configuration to your Home Assistant configuration.yaml file:
```yaml
logger:
  logs:
    custom_components.homewhiz: debug
```
To retrieve logs, navigate in Home Assistant to: settings -> system -> logs and retrieve logs by e.g. pressing the download button below the logs.
> :warning: Please review your logs and **delete personal and private information before posting** :warning:

## Contributing to the project

Contributions are welcome.
- Report problems by creating an issue [here](https://github.com/home-assistant-HomeWhiz/home-assistant-HomeWhiz/issues)
- [Get started developing](./linux_dev.md)
- [Submit your code](https://github.com/home-assistant-HomeWhiz/home-assistant-HomeWhiz/pulls)

### Contribute icon translations

You can contribute icon translations. Icon translations map entities to icons, see [here](https://developers.home-assistant.io/docs/core/entity/#icon-translations) for more details.
Feel free to open a pull request with your adjustments to the custom_components/homewhiz/icons.json file. Make sure to install pre-commit beforehand.
