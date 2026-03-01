# 🎬 VideoProc - Smart Video Compressor

VideoProc is a lightweight, fully automated video compression tool designed to dramatically reduce video file sizes while maintaining high quality. It utilizes full GPU acceleration (NVIDIA NVENC) to process videos blazingly fast.

Forget about complicated installations or configuring system paths—VideoProc manages itself. 

## ✨ Key Features

* **Zero-Setup Installation**: Just download the `.exe` and run it. The app automatically downloads and configures its own video engine (FFmpeg) in the background.
* **Auto-Updating**: Never worry about downloading the latest version. VideoProc checks for updates on startup and seamlessly updates itself.
* **Full GPU Acceleration**: Utilizes hardware decoding and encoding (NVIDIA NVENC) for maximum processing speed.
* **Smart Resume Queue**: If you close the app or your PC crashes, your queue is saved. Open the app again to pick up exactly where you left off.
* **Preserves Folder Structure**: Drag and drop a massive folder of videos, and the app will recreate the exact same folder tree in your output directory.
* **Target Size / Percentage Modes**: Compress videos by a specific percentage, or tell the app "make this video exactly 5MB" (perfect for Discord).

---

## 🚀 Getting Started

### 1. Download & Run
You do not need to install anything. Simply download the `VideoProc.exe` file and double-click it to run. 

> *Note: Because this is a standalone executable, Windows SmartScreen might show a "Windows protected your PC" warning. Click **More info** -> **Run anyway**.*

### 2. The First Launch (Automatic Setup)
When you open VideoProc for the very first time, it will lock the interface and say **"Downloading FFmpeg..."**. 
* The app is securely downloading the necessary video processing engines directly from official sources.
* This is a one-time process (~100MB download). Once it finishes, the app will unlock and is ready to use forever!

---

## 📖 How to Use

1. **Add Videos**: Click **Add Files** to select specific videos, or **Add Folder** to import an entire directory (this will preserve your folder structure). You can also drag and drop files directly into the window.
2. **Review the Queue**: Your added videos will appear in the queue. You can see their original size and status.
3. **Configure Settings (Optional)**: Click the **⚙️ Settings** button on the left to change:
   * Where your compressed videos are saved.
   * Your target compression size (e.g., Target Size: 8MB).
   * GPU acceleration toggles.
4. **Start Processing**: Click the big blue **▶ Start Processing** button.
5. **Done!**: Click **📂 Output Folder** to view your freshly compressed videos.

---

## ⚙️ Understanding the Settings

* **Target Size vs. Percentage**: 
  * *Percentage*: Reduces the video's bitrate by a percentage (e.g., 33% means the file will be roughly 1/3 of its original size).
  * *Target Size*: Automatically calculates the perfect bitrate to make the video fit your exact MB requirement.
* **GPU Acceleration**: If you have an NVIDIA graphics card, leave this **ON**. It shifts the heavy lifting from your CPU to your GPU, speeding up exports significantly.
* **Copy Audio**: Leaves the audio track completely untouched to preserve 100% original sound quality.

---

## 🛠️ Troubleshooting & FAQ

**Q: The app says "Missing dependency" or won't start processing.**
A: VideoProc has a self-healing feature. Simply restart the application. Upon startup, it will realize files are missing and automatically repair itself by re-downloading them.

**Q: Where are my compressed videos saving?**
A: By default, they save to `C:\Users\YourName\Videos\Processed`. You can change this anytime in the Settings menu.

**Q: Where does the app install its hidden files?**
A: All config files and background engines (FFmpeg) are safely kept out of your way in your local app data folder: `C:\Users\YourName\AppData\Local\VideoProc`. If you ever want to completely "factory reset" the app, you can delete that folder.

**Q: How do updates work?**
A: On startup, VideoProc checks for a new version. If it finds one, it will say "Downloading Update...". It will download the new `.exe`, safely replace the old one, and automatically restart the app for you. No manual downloading required!
