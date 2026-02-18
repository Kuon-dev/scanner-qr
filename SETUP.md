# QR Scanner — Setup Guide

macOS-only tool that watches a chat app (via scrcpy) for QR codes and automatically opens them on your phone.

## Prerequisites

- macOS (uses Quartz for screen capture)
- Python 3.13+
- Homebrew
- Android phone with USB debugging enabled

## 1. Install system dependencies

```bash
brew install python@3.13 scrcpy zbar android-platform-tools
```

| Package | Purpose |
|---------|---------|
| `python@3.13` | Runtime |
| `scrcpy` | Mirror Android screen to macOS |
| `zbar` | C library for QR/barcode decoding (required by pyzbar) |
| `android-platform-tools` | ADB — opens decoded URLs on the phone |

## 2. Clone and set up the project

```bash
cd /path/to/scanner
python3.13 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## 3. Connect your phone

1. Enable **USB Debugging** on your Android phone (Settings > Developer Options)
2. Connect via USB
3. Verify connection:
   ```bash
   adb devices
   ```
   You should see your device listed. Note the serial number.

## 4. Start scrcpy

```bash
scrcpy
```

A window showing your phone screen should appear. Open the chat app you want to monitor.

## 5. Calibrate the chat region

```bash
source .venv/bin/activate
python calibration.py
```

This captures the scrcpy window and lets you click-drag to select the chat message area. Press **Enter** to confirm. The region is saved to `config.json`.

## 6. Configure

Edit `config.json`:

| Key | Description | Default |
|-----|-------------|---------|
| `adb_serial` | Your device serial from `adb devices` | `""` |
| `adb_enabled` | Open decoded URLs on phone via ADB | `true` |
| `discord_webhook_url` | Discord webhook for notifications (optional) | `""` |
| `scrcpy_window_title` | Window title to find scrcpy | `"scrcpy"` |
| `change_threshold_pct` | Pixel change % to trigger detection | `10.0` |

## 7. Run the scanner

```bash
source .venv/bin/activate
python main.py
```

The scanner will:
1. Watch the calibrated chat region for screen changes
2. Wait for the frame to stabilize (scrolling to stop)
3. Decode any QR codes in the frame
4. Open the URL on your phone via ADB and/or post to Discord

Press **Ctrl+C** to stop.

## Troubleshooting

**"scrcpy window not found"** — Make sure scrcpy is running before starting the scanner.

**"Chat region not calibrated"** — Run `python calibration.py` first.

**"adb not found in PATH"** — Install `android-platform-tools` via Homebrew or add your Android SDK `platform-tools` to PATH.

**No QR decoded** — Check that the QR code is fully visible in the chat region you calibrated. Re-run `python calibration.py` if needed to cover the full chat area.

**Permission denied (screen recording)** — macOS requires screen recording permission. Go to System Settings > Privacy & Security > Screen Recording, and allow your terminal app.
