<p align="center">
  <img src="https://raw.githubusercontent.com/home-assistant-HomeWhiz/home-assistant-HomeWhiz/main/icons/icon.png" alt="HomeWhiz icon">
</p>

<div align="center">

# HomeWhiz Integration for Home Assistant

[![HACS Default](https://img.shields.io/badge/HACS-Default-41BDF5.svg?style=flat-square)](https://github.com/hacs/integration)
[![Home Assistant](https://img.shields.io/badge/Home%20Assistant-Integration-41BDF5?style=flat-square&logo=home-assistant&logoColor=white)](https://www.home-assistant.io/)
[![Version](https://img.shields.io/github/v/release/home-assistant-HomeWhiz/home-assistant-HomeWhiz?style=flat-square&logo=github&color=41BDF5&logoColor=white&cacheSeconds=15600)](https://github.com/home-assistant-HomeWhiz/home-assistant-HomeWhiz/releases)

[![HA installs](https://img.shields.io/badge/dynamic/json?url=https%3A%2F%2Fanalytics.home-assistant.io%2Fcustom_integrations.json&query=%24.homewhiz.total&label=HA%20installs&color=41BDF5&style=flat-square&logo=home-assistant&logoColor=white&cacheSeconds=15600)](https://analytics.home-assistant.io/)
[![GitHub stars](https://img.shields.io/github/stars/home-assistant-HomeWhiz/home-assistant-HomeWhiz?style=flat-square&cacheSeconds=15600)](https://github.com/home-assistant-HomeWhiz/home-assistant-HomeWhiz/stargazers)
[![Open issues](https://img.shields.io/github/issues/home-assistant-HomeWhiz/home-assistant-HomeWhiz?style=flat-square&cacheSeconds=15600)](https://github.com/home-assistant-HomeWhiz/home-assistant-HomeWhiz/issues)

</div>

Integration for devices that support the HomeWhiz mobile app (Beko, Grundig, Bauknecht, Arcelik).<br />
Monitor and control them in Home Assistant, over local Bluetooth or the HomeWhiz cloud (Wi-Fi) depending on the model.

## Installation

### Option 1. Using HACS (recommended)

- Search for `HomeWhiz` on the HACS integration page. The integration is part of the HACS default repository, so you do not need to add it manually as a custom repository.
- Install the integration and restart Home Assistant.

### Option 2. Manually

- Open the directory for your HA configuration (where `configuration.yaml` lives).
- If there is no `custom_components` directory, create it.
- Inside `custom_components`, create a new folder called `homewhiz`.
- Download _all_ files from the `custom_components/homewhiz/` directory in this repository.
- Place the downloaded files in the folder you created.
- Restart Home Assistant.

## Configuration

### <img src="https://cdn.simpleicons.org/bluetooth/0082FC" height="20" align="absmiddle" alt="" /> Bluetooth

- Connect the device to the HomeWhiz app on your smartphone.
- Close the app.
- In Home Assistant go to **Settings** → **Devices & Services**. The device should be discovered automatically. If it is not, click **+ Add Integration** and search for **HomeWhiz**.
- Select the **Bluetooth** connection type.
- Provide your HomeWhiz username and password. These are used to fetch your device mapping from the HomeWhiz API during configuration.

**No internet connection is required after the initial configuration.**

### 📶 Wi-Fi

- Connect the device to the HomeWhiz app on your smartphone.
- In Home Assistant go to **Settings** → **Devices & Services**. Click **+ Add Integration** and search for **HomeWhiz**.
- Select the **Cloud** connection type.
- Provide your HomeWhiz username and password.

**A constant internet connection is required.**

## Supported device types

| Device | Status | Notes |
| :--- | :---: | :--- |
| 🧺 Washing machine | ✅ | Also includes washing machine / dryer combinations |
| 🌀 Dryer | ✅ | Also includes washing machine / dryer combinations |
| 🍽️ Dishwasher | ✅ | |
| ❄️ Air conditioner | ✅ | |
| 💨 Extraction fan | ✅ | |
| 🔥 Hob | ✅ | Beko 4-zone induction hob |
| 🧊 Refrigerator / Freezer | ✅ | Bauknecht freezer with convertible compartment (tested via cloud) |
| 🍪 Oven | ❓ | Not tested |

If you have other device types not listed yet, please let us know.

If your device is missing some information or translations, or is not working at all, please create an issue. Don't forget to include your device digital ID, which can be found either in the HomeWhiz app or the integration logs.

## Troubleshooting

### Bluetooth

The integration should work with all devices connected via Bluetooth. Bluetooth range is limited, so if your device is out of range, try an [ESPHome Bluetooth Proxy](https://esphome.github.io/bluetooth-proxies/).

If you use a custom Home Assistant installation method such as a virtual machine, make sure your system is configured properly and Bluetooth is available within Home Assistant.

A device supports only a **single Bluetooth connection at a time**. To connect the device to the original app, disable the Home Assistant integration, restart Home Assistant, and wait a few minutes. The device should indicate this, for example the Bluetooth icon on a washing machine starts flashing.

<details>
<summary><b>Bluetooth Proxy</b></summary>

Switching to an ESPHome-based proxy helped fix issues for many users. If issues persist even when using a proxy, force the proxy into active mode and re-add the integration:

```yaml
bluetooth_proxy:
  active: true
```

Some users also had to declare the washer/dryer MAC under `ble_client` and keep the proxy within ~1 m of the appliance to maintain a stable connection.

</details>

<details>
<summary><b>Google Login</b></summary>

If you signed up via Google in the HomeWhiz app, try forcing a HomeWhiz password reset inside the original app. Go to *My Account* → *Change Password* and tap *Forgot Password* to trigger the reset email for your Google address, then use the new password when adding the integration.

</details>

## Retrieve logs and diagnostics

To help us help you, please include **debug logs and diagnostics** when you submit issues.

<details>
<summary><b>Enable debug logging</b></summary>

Debug logging can be enabled directly from the Home Assistant integration page:

- Navigate to **Settings** → **Devices & Services** → **Integrations**
- Find the **HomeWhiz** integration
- Click the three-dot menu and select **Enable debug logging**
- Reproduce the issue
- Click **Disable debug logging** to stop logging and download the debug log file

Alternatively, enable debug logging via `configuration.yaml`:

```yaml
logger:
  logs:
    custom_components.homewhiz: debug
```

After adding this, restart Home Assistant. To retrieve logs, navigate to **Settings** → **System** → **Logs** and download them.

> ⚠️ Please review your logs and delete personal and private information before posting ⚠️

</details>

<details>
<summary><b>Download diagnostics</b></summary>

Diagnostic information can help identify issues with your device:

- Navigate to **Settings** → **Devices & Services** → **Integrations**
- Find the **HomeWhiz** integration and click on it
- Select your device
- Click **Download diagnostics** to download a JSON file with diagnostic information

> ⚠️ Please review the diagnostics file and delete personal and private information before posting ⚠️

</details>

## Known issues

For known issues and troubleshooting tips, check the [open issues on GitHub](https://github.com/home-assistant-HomeWhiz/home-assistant-HomeWhiz/issues).

If you encounter a problem that is not listed there, please [create a new issue](https://github.com/home-assistant-HomeWhiz/home-assistant-HomeWhiz/issues) and include your debug logs and diagnostics file (see above).

## Contributing to the project

Contributions are welcome.

- [Get started developing](./linux_dev.md)
- [Submit your code](https://github.com/home-assistant-HomeWhiz/home-assistant-HomeWhiz/pulls)

### Contribute icon translations

You can contribute icon translations. Icon translations map entities to icons, see [the Home Assistant docs](https://developers.home-assistant.io/docs/core/entity/#icon-translations) for more details. Feel free to open a pull request with your adjustments to the `custom_components/homewhiz/icons.json` file. Make sure to install pre-commit beforehand.
