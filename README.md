To run the **Video Processor GUI Application**, you will need to install a few Python libraries and ensure that the FFmpeg multimedia framework is available on your system.

### **Required Dependencies**

1. **Python 3.7+**: Ensure you have Python installed. You can check this by running `python --version` in your terminal.
2. **CustomTkinter**: This provides the modern GUI elements used in the application.
* **Installation**: `pip install customtkinter`.


3. **FFmpeg & FFprobe**: These are external command-line tools that handle the actual video processing. They are not Python modules but must be installed on your system.
* **Windows**: Download builds from [gyan.dev](https://www.gyan.dev/ffmpeg/builds/), extract them, and add the `bin` folder to your system's PATH.
* **macOS**: Install via Homebrew using `brew install ffmpeg`.
* **Linux**: Install via your package manager, e.g., `sudo apt install ffmpeg` for Ubuntu/Debian.


4. **Tkinter**: Usually comes pre-installed with Python on Windows and macOS. On some Linux distributions, you may need to install it manually using `sudo apt-get install python3-tk`.

---

### **README.md for GitHub**

You can copy and paste the following content into a file named `README.md` in your repository:

```markdown
# Video Processor GUI

A modern, GPU-accelerated video compression tool built with Python. This application uses FFmpeg and NVENC to provide fast video processing with a smart resume feature.

## Features
- **GPU Acceleration**: Utilizes NVIDIA NVENC for high-speed encoding.
- **Smart Resume**: Saves your processing queue so you can pick up where you left off.
- **Customizable**: Adjustable bitrate, target size, and encoder presets.

## Prerequisites

### 1. Python
Ensure you have Python 3.7 or higher installed on your system.

### 2. FFmpeg & FFprobe
This application requires FFmpeg to be installed and accessible via your system's command line.
- **Windows**: [Download FFmpeg](https://www.gyan.dev/ffmpeg/builds/), extract it, and add the `bin` folder to your system Environment Variables (PATH).
- **macOS**: `brew install ffmpeg`
- **Linux**: `sudo apt install ffmpeg`

## Installation

1. Clone this repository:
   ```bash
   git clone [https://github.com/your-username/video-processor-gui.git](https://github.com/your-username/video-processor-gui.git)
   cd video-processor-gui

```

2. Install the required Python dependencies:
```bash
pip install customtkinter

```



## Usage

Run the application using Python:

```bash
python VideoProc.py

```

## Configuration

Upon first launch, you can configure the paths for `ffmpeg.exe` and `ffprobe.exe` in the settings panel if they are not automatically detected in your system PATH.

```


This [CustomTkinter tutorial](https://www.youtube.com/watch?v=Z73gosO1K1M) explains how to set up the library and build modern interfaces, which is essential for understanding how the Video Processor GUI is constructed.


http://googleusercontent.com/youtube_content/0

```
