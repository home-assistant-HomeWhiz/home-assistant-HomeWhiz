# HomeWhiz Integration for Home Assistant

![HomeWhiz icon](./icons/icon.png)

Integration for devices that can connect to HomeWhiz mobile app (Beko, Grundig, Arcelik)

## Installation

### Option 1. Using HACS (Recommended)

1. Search for `HomeWhiz` on the HACS integration page (this integration is part of the HACS default repository meaning it is not necessary to add this integration manually via custom repositories)
2. Install the integration and Restart Home Assistant

### Option 2. Manually

1. Using the tool of choice, open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory there, you need to create it.
3. In the `custom_components` directory create a new folder called `HomeWhiz`.
4. Download _all_ files from the `custom_components/HomeWhiz/` directory in this repository.
5. Place the files you downloaded in the new directory you created.
6. Restart Home Assistant

## Configuration

1. Connect the device to the HomeWhiz app on your smartphone
2. Close the app
3. In the HA UI go to "Configuration" -> "Integrations". The device should be automatically discovered. If it's not click "+" and search for "HomeWhiz"
4. Provide the HomeWhiz username and password. These will be used to fetch your device mapping from the HomeWhiz API during configuration. No internet connection is required after the initial configuration. 

## Bluetooth Compatibility

Integration should work with all devices connected via Blueooth. Remember that the range of Bluetooth can be limited. If your device is out of range, you could try using an [ESPHome Bluetooth Proxy](https://esphome.github.io/bluetooth-proxies/).  
This integration was only tested with a generic washing machine. 
If you have other device types, please let us know.
Support for other device types may be lacking.
If your device is missing some information or not working, please create an issue. 
Don't forget to include your device digital ID that can be found either in the HomeWhiz app or the integration logs.  

## Wi-Fi Compatibility

Wi-Fi devices are not yet supported. 
It's not possible do develop a working integration without having access to a physical device. 
If you have a Wi-Fi connected HomeWhiz device, your pull-request is very welcome. We will offer you technical support. 

## Additional Notes

The HomeWhiz smartphone app does not seem to be working when the integration is enabled. 
To make the app work again, you have to disable the integration, restart Home Assistant and wait a few minutes - this can be indicated on the device: E.g.,  the Bluetooth icon on a washing machine starts flashing.

## Retrieve Integration Logs

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
- Report problems by creating an issue [here](https://github.com/rowysock/home-assistant-HomeWhiz/issues)
- [Get started developing](./linux_dev.md)
- [Submit your code](https://github.com/rowysock/home-assistant-HomeWhiz/pulls)
