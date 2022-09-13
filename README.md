# HomeWhiz integration for Home Assistant

[![HomeWhiz icon](./icons/icon.svg)]

Integration for devices that can connect to HomeWhiz mobile app (Beko, Grundig, Arcelik).
Currently, only basic washing machines are supported. If your device doesn't work, please create an issue

## Installation

### Option 1. Using HACS
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
3. In the HA UI go to "Configuration" -> "Integrations" click "+" and search for "HomeWhiz"
4. Optionally rename the device 


## Additional notes

Smartphone app doesn't seem to be working when integration is enabled. 
To make the app work again you have to disable the integration, restart the HA and wait a few minutes ( In my case bluetooth icon on a washing machine starts flashing )

