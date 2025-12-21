
# Video Processor GUI

A modern, GPU-accelerated video compression tool built with Python. This application uses FFmpeg and NVENC to provide fast video processing with a smart resume feature.

## Features
- **GPU Acceleration**: Utilizes NVIDIA NVENC for high-speed encoding.
- **Smart Resume**: Saves your processing queue so you can pick up where you left off.
- **Customizable**: Adjustable bitrate, target size, and encoder presets.

## Prerequisites

### 1. Python
Ensure you have Python 3.7 or higher installed on your system.

 Install the required Python dependencies:
```bash
pip install customtkinter

```
### 2. FFmpeg & FFprobe
This application requires FFmpeg to be installed and accessible via your system's command line.
- **Windows**: [Download FFmpeg](https://www.gyan.dev/ffmpeg/builds/), extract it, and add the `bin` folder to your system Environment Variables (PATH).



