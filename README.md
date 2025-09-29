# 🔍 USB/Serial Sniffer

**Advanced Serial Port Monitor with Real-time Data Interception**

[![Python](https://img.shields.io/badge/Python-3.7+-blue.svg)](https://www.python.org/downloads/)
[![Platform](https://img.shields.io/badge/Platform-Windows-green.svg)](https://www.microsoft.com/windows)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![GUI](https://img.shields.io/badge/GUI-Tkinter-orange.svg)](https://docs.python.org/3/library/tkinter.html)

## Overview

USB/Serial Sniffer is a lightweight and efficient tool for monitoring communication between two serial ports in real-time.
It is designed for reverse engineering, debugging, and protocol analysis. The tool provides both hex and ASCII views in a user-friendly interface.

## Features

- **Real-time Sniffing**: between two serial ports
- **Multi-Tab Interface**: split panels, combined stream, raw hex dump
- **Live Statistics**: throughput, packet counts, average packet size
- **Logging**: export captured data to files
- **Port Scanner**: with VID/PID information
- **Baud Rate Support**: from 9600 up to 921600

### Visual Enhancements
1. **Separate Panels (Tx/Rx)**
2. **Combined Stream View**
3. **🔍 Raw Hex Dump**

### 🎨 Görsel Özellikler
- **Color-coded streams (Tx/Rx)**
- **Dark Theme**
- **Auto-Scroll**
- **Timestamp with millisecond precision**

## Installation

### Requirements
- **OS**: Windows 10 (64-bit recommended)
- **Python**: 3.10 + 
- **Virtual COM Port Driver**: ([İndir](http://com0com.sourceforge.net/))

### Setup
```bash
git clone https://github.com/icopoglu/usb-sniffer.git
cd usb-sniffer
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
Install com0com and create a virtual COM pair (e.g., COM3-COM4).


## Usage

### 1. Starting the app
```bash
python app.py
```

## License
This project is licensed under the MIT License – see the [LICENSE](LICENSE) file for details.

## Author
**İsmail Kerem Çöpoğlu**  
GitHub: [@icopoglu](https://github.com/icopoglu)

## Contributing
Contributions are welcome! Please fork the repository and open a pull request.