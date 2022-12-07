# HomeWhiz integration for Home Assistant

![HomeWhiz icon](./icons/icon.png)

Integration for devices that can connect to HomeWhiz mobile app (Beko, Grundig, Arcelik)

## Installation

### Option 1. Using HACS (Recommended)

1. Add this repository to [HACS custom repositories](https://hacs.xyz/docs/faq/custom_repositories/) 
2. Search for `home-assistant-homewhiz` on HACS integration page
3. Install the integration and Restart Home Assistant

### Option 2. Manually

1. Using the tool of choice open the directory (folder) for your HA configuration (where you find `configuration.yaml`).
2. If you do not have a `custom_components` directory (folder) there, you need to create it.
3. In the `custom_components` directory (folder) create a new folder called `HomeWhiz`.
4. Download _all_ the files from the `custom_components/HomeWhiz/` directory (folder) in this repository.
5. Place the files you downloaded in the new directory (folder) you created.
6. Restart Home Assistant

## Configuration

1. Connect the device to the HomeWhiz app on your smartphone
2. Close the app
3. In the HA UI go to "Configuration" -> "Integrations". The device should be automatically discovered. If it's not click "+" and search for "HomeWhiz"
4. Provide the HomeWhiz username and password. These will be used to fetch your device mapping from the HomeWhiz API during configuration. No internet connection is required after the initial configuration. 

## Bluetooth compatibility

Integration should work with all of the devices connected via Blueooth.
It was tested in a real life only for a generic washing machine. 
If you have other device type please let us know.
Support for other device types may be lacking
If your device is missing some info please create an issue. 
Don't forget to include your device digital ID that can be found either in the HomeWhiz app or the integration logs 

## Wi-Fi compatibility

Wi-Fi devices are not yet supported. 
It's not possible do develop a working integration without having access to a physical device. 
If you have a Wi-Fi connected HomeWhiz device, your PR is very welcome. We can offer you a technical support. 

## Additional notes

Smartphone app doesn't seem to be working when integration is enabled. 
To make the app work again you have to disable the integration, restart the HA and wait a few minutes ( In my case bluetooth icon on a washing machine starts flashing )

## Contributing to the project

Contributions are welcome. 
- Report problems by creating an issue [here](https://github.com/rowysock/home-assistant-HomeWhiz/issues)
- [Get started developing](./dev_linux.md)
- [Submit your code](https://github.com/rowysock/home-assistant-HomeWhiz/pulls)
