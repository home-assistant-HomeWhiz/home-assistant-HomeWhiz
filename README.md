# HomeWhiz integration for Home Assistant

Integration for devices that can connect to HomeWhiz mobile app (Beko, Grundig, Arcelik).
Currently, only basic washing machines are supported. If your device doesn't work, please create an issue

## Installation

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


