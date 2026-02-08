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
| Hob              | :heavy_check_mark: | Beko 4-zone induction hob                          |
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

#### Bluetooth Proxy
Switching to an ESPHome-based proxy helped fix issues for many. If issues persist even when using a proxy, force the proxy into active mode (`bluetooth_proxy:\n  active: true`) and re-add the integration; some users also had to declare the washer/dryer MAC under `ble_client` and keep the proxy within ~1 m of the appliance to maintain a stable connection.

### Google Login
If you signed up via Google in the HomeWhiz app, try forcing a HomeWhiz password reset inside the original app. Go to *My Account* → *Change Password* and tap *Forgot Password* to trigger the reset email for your Google address, then use the new password when adding the integration.

### Retrieve Integration Logs and Diagnostics

To help us help you, please include **debug logs and diagnostics** when you submit issues.

## Enable Debug Logging

Debug logging can be enabled directly from the Home Assistant integration page:

- Navigate to **Settings** → **Devices & Services** → **Integrations**
- Find the **HomeWhiz** integration
- Click on the three-dot menu and select **Enable debug logging**
- Reproduce the issue
- Click **Disable debug logging** to stop logging and download the debug log file

Alternatively, you can enable debug logging via `configuration.yaml`:
```yaml
logger:
  logs:
    custom_components.homewhiz: debug
```

After adding this configuration, restart Home Assistant. To retrieve logs, navigate to Settings → System → Logs and download them.

>⚠️ Please review your logs and delete personal and private information before posting ⚠️

## Download Diagnostics

Diagnostic information can help identify issues with your device:

- Navigate to Settings → Devices & Services → Integrations

- Find the HomeWhiz integration and click on it

- Select your device

- Click on Download diagnostics to download a JSON file with diagnostic information.

>⚠️ Please review the diagnostics file and delete personal and private information before posting ⚠️

## Known Issues
- For known issues and troubleshooting tips, check the Known Issues on [Github](https://github.com/home-assistant-HomeWhiz/home-assistant-HomeWhiz/issues)

- If you encounter a problem not listed there, please create a new issue [here](https://github.com/home-assistant-HomeWhiz/home-assistant-HomeWhiz/issues) with:

- Debug logs and Diagnostics file (see above)

## Contributing to the project

Contributions are welcome.
- [Get started developing](./linux_dev.md)
- [Submit your code](https://github.com/home-assistant-HomeWhiz/home-assistant-HomeWhiz/pulls)

### Contribute icon translations

You can contribute icon translations. Icon translations map entities to icons, see [here](https://developers.home-assistant.io/docs/core/entity/#icon-translations) for more details.
Feel free to open a pull request with your adjustments to the custom_components/homewhiz/icons.json file. Make sure to install pre-commit beforehand.
