<p align="center">
  <img src="assets/hero_new.png" width="100%" alt="LanShare Hero">
</p>

# 🚀 LanShare

[![Python 3.8+](https://img.shields.io/badge/python-3.8+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Release](https://img.shields.io/github/v/release/Pratham200Rajbhar/LanShare)](https://github.com/Pratham200Rajbhar/LanShare/releases)
[![Platform Linux](https://img.shields.io/badge/platform-Linux-lightgrey.svg)]()
[![Platform Windows](https://img.shields.io/badge/platform-Windows-lightgrey.svg)]()

**LanShare** is a powerful, lightweight, and cross-platform LAN file sharing application. Built with **Python** and **CustomTkinter**, it provides a modern UI for seamless peer-to-peer file transfers over your local network—no internet required.

---

## ⚡ Quick Download

Get the latest version of LanShare for your operating system:

| Platform | Download Link | Quick Install |
| :--- | :--- | :--- |
| **🪟 Windows** | [**Download LanShare.exe**](https://github.com/Pratham200Rajbhar/LanShare/releases/download/v1.0.0/LanShare.exe) | Just run the `.exe` |
| **🐧 Linux** | [**Download lanshare_1.0.0.deb**](https://github.com/Pratham200Rajbhar/LanShare/releases/download/v1.0.0/lanshare_1.0.0.deb) | `sudo apt install ./lanshare_1.0.0.deb` |

> [!TIP]
> **Windows Users**: If Windows Defender shows a warning, click "More info" and "Run anyway".
> **Linux Users**: The `.deb` package will automatically add LanShare to your application menu.

---

## ✨ Features

- 📂 **High-Speed Transfers**: Direct P2P file sharing using your local network's full bandwidth.
- 🔒 **Privacy Focused**: No cloud servers. Your files stay within your local network.
- 🖥️ **Modern UI**: Clean, responsive, and dark-themed interface powered by CustomTkinter.
- 🔍 **Auto-Discovery**: Automatically find other users on the same network.
- 📦 **Zero Config**: Just run and share. No complex setup or internet connection needed.

---

## � How to Use

1. **Launch**: Open LanShare on both devices.
2. **Discover**: Wait for the devices to appear in the list (or enter IP manually).
3. **Share**: Drag and drop files to send them instantly.

💡 *Ensure both devices are on the same WiFi/Ethernet network and firewalls allow local connections.*

---

## 🛠️ Development Setup

If you want to contribute or build from source:

### 🐧 Linux (Ubuntu/Debian)
```bash
sudo apt update && sudo apt install python3-tk python3-pip
git clone https://github.com/Pratham200Rajbhar/LanShare.git
cd LanShare
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
python main.py
```

### 🪟 Windows
```powershell
git clone https://github.com/Pratham200Rajbhar/LanShare.git
cd LanShare
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
python main.py
```

---

## 📜 License
Distributed under the MIT License. See `LICENSE` for more information.

---
<p align="center">Made with ❤️ by Pratham</p>
