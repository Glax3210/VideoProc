"""
Video Processor GUI Application
GPU-accelerated video compression using FFmpeg and NVENC
FIXED VERSION - Full GPU Utilization + Smart Resume
"""

import customtkinter as ctk
from tkinter import filedialog, messagebox
import tkinter as tk
import subprocess
import threading
import json
import os
import re
import tempfile
import atexit
from pathlib import Path
from datetime import datetime
import time

# ============================================
# Configuration
# ============================================
CONFIG_FILE = "video_processor_config.json"
QUEUE_STATE_FILE = "video_processor_queue.json"

DEFAULT_CONFIG = {
    "input_folder": "",
    "output_folder": str(Path.home() / "Videos" / "Processed"),
    "ffmpeg_path": "C:/ffmpeg/bin/ffmpeg.exe",
    "ffprobe_path": "C:/ffmpeg/bin/ffprobe.exe",
    "filename_suffix": "_compressed",
    "bitrate_mode": "percentage",
    "bitrate_percentage": 33,
    "target_size_mb": 5,
    "encoder": "h264_nvenc",
    "encoder_preset": "p4",
    "gpu_acceleration": True,
    "hardware_decode": True,
    "copy_audio": True,
    "audio_bitrate": "128k",
    "max_concurrent_jobs": 1,
}


class Config:
    """Configuration manager"""
    
    def __init__(self):
        self.config = DEFAULT_CONFIG.copy()
        self.load()
    
    def load(self):
        try:
            if os.path.exists(CONFIG_FILE):
                with open(CONFIG_FILE, 'r') as f:
                    saved = json.load(f)
                    self.config.update(saved)
        except Exception as e:
            print(f"Error loading config: {e}")
    
    def save(self):
        try:
            with open(CONFIG_FILE, 'w') as f:
                json.dump(self.config, f, indent=2)
        except Exception as e:
            print(f"Error saving config: {e}")
    
    def get(self, key):
        return self.config.get(key, DEFAULT_CONFIG.get(key))
    
    def set(self, key, value):
        self.config[key] = value
        self.save()


# ============================================
# Queue State Manager
# ============================================
class QueueStateManager:
    """Saves/loads queue for resume capability"""
    
    def __init__(self):
        self.state_file = QUEUE_STATE_FILE
    
    def save(self, queue):
        """Save queue state"""
        try:
            data = {
                "timestamp": datetime.now().isoformat(),
                "files": [
                    {
                        "path": vf.path,
                        "status": vf.status,
                        "size": vf.size,
                        "duration": vf.duration,
                        "bitrate": vf.bitrate,
                        "video_bitrate": vf.video_bitrate,
                    }
                    for vf in queue
                ]
            }
            with open(self.state_file, 'w') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            print(f"Error saving queue: {e}")
    
    def load(self):
        """Load queue state"""
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading queue: {e}")
        return None
    
    def clear(self):
        """Clear saved state"""
        try:
            if os.path.exists(self.state_file):
                os.remove(self.state_file)
        except:
            pass
    
    def exists(self):
        return os.path.exists(self.state_file)


# ============================================
# Video Processing - UNCHANGED (FAST VERSION)
# ============================================
class VideoFile:
    """Represents a video file in the queue"""
    
    def __init__(self, path):
        self.path = path
        self.filename = os.path.basename(path)
        self.directory = os.path.dirname(path)
        self.format = Path(path).suffix.upper().replace(".", "")
        self.size = 0
        self.duration = 0
        self.bitrate = 0
        self.video_bitrate = 0
        self.status = "pending"
        self.progress = 0
        self.output_path = ""
        self.error = None


class FFmpegProcessor:
    """Handles FFmpeg operations - FAST VERSION (unchanged)"""
    
    def __init__(self, config, log_callback=None, progress_callback=None):
        self.config = config
        self.log_callback = log_callback
        self.progress_callback = progress_callback
        self.current_process = None
        self.is_cancelled = False
        self.progress_file = None
    
    def log(self, level, message):
        if self.log_callback:
            self.log_callback(level, message)
    
    def get_video_info(self, file_path):
        """Get video information using ffprobe"""
        ffprobe_path = self.config.get("ffprobe_path")
        
        cmd = [
            ffprobe_path,
            "-v", "quiet",
            "-print_format", "json",
            "-show_format",
            "-show_streams",
            file_path
        ]
        
        try:
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True, 
                timeout=30,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            if result.returncode == 0:
                info = json.loads(result.stdout)
                
                video_stream = next(
                    (s for s in info.get("streams", []) if s.get("codec_type") == "video"),
                    None
                )
                
                format_info = info.get("format", {})
                
                return {
                    "duration": float(format_info.get("duration", 0)),
                    "size": int(format_info.get("size", 0)),
                    "bitrate": int(format_info.get("bit_rate", 0)),
                    "video_bitrate": int(video_stream.get("bit_rate", 0)) if video_stream else 0,
                    "width": video_stream.get("width", 0) if video_stream else 0,
                    "height": video_stream.get("height", 0) if video_stream else 0,
                    "codec": video_stream.get("codec_name", "unknown") if video_stream else "unknown"
                }
        except Exception as e:
            self.log("ERROR", f"FFprobe error: {e}")
        
        return None
    
    def calculate_target_bitrate(self, video_file):
        """Calculate target bitrate based on settings"""
        mode = self.config.get("bitrate_mode")
        
        if mode == "percentage":
            percentage = self.config.get("bitrate_percentage") / 100
            source_bitrate = video_file.video_bitrate or video_file.bitrate
            target_kbps = int((source_bitrate * percentage) / 1000)
        else:
            target_mb = self.config.get("target_size_mb")
            target_bytes = target_mb * 1024 * 1024
            audio_bitrate = 128000 if self.config.get("copy_audio") else int(self.config.get("audio_bitrate").replace("k", "")) * 1000
            video_bits = (target_bytes * 8) - (audio_bitrate * video_file.duration)
            target_kbps = max(100, int(video_bits / video_file.duration / 1000))
        
        return max(100, target_kbps)
    
    def process_video(self, video_file, status_callback=None):
        """Process a single video file - FAST VERSION (no extra checks)"""
        self.is_cancelled = False
        
        # Ensure output folder exists
        output_folder = self.config.get("output_folder")
        os.makedirs(output_folder, exist_ok=True)
        
        # Generate output filename
        suffix = self.config.get("filename_suffix")
        base_name = Path(video_file.filename).stem
        output_name = f"{base_name}{suffix}.mp4"
        output_path = os.path.join(output_folder, output_name)
        video_file.output_path = output_path
        
        # Calculate target bitrate
        target_bitrate = self.calculate_target_bitrate(video_file)
        
        source_bitrate = (video_file.video_bitrate or video_file.bitrate) // 1000
        self.log("INFO", f"Bitrate: {source_bitrate} kbps → {target_bitrate} kbps")
        
        # Create progress file
        progress_file = tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.txt')
        progress_file.close()
        self.progress_file = progress_file.name
        
        # Build FFmpeg command
        ffmpeg_path = self.config.get("ffmpeg_path")
        
        cmd = [ffmpeg_path, "-y"]
        
        # Hardware decoding
        if self.config.get("gpu_acceleration") and self.config.get("hardware_decode"):
            cmd.extend(["-hwaccel", "cuda", "-hwaccel_output_format", "cuda"])
        
        cmd.extend(["-i", video_file.path])
        
        # Encoder settings
        if self.config.get("gpu_acceleration"):
            encoder = self.config.get("encoder")
            preset = self.config.get("encoder_preset")
        else:
            encoder = "libx264"
            preset = "medium"
        
        cmd.extend([
            "-c:v", encoder,
            "-preset", preset,
            "-b:v", f"{target_bitrate}k",
            "-maxrate", f"{int(target_bitrate * 1.5)}k",
            "-bufsize", f"{target_bitrate * 2}k",
        ])
        
        # Audio settings
        if self.config.get("copy_audio"):
            cmd.extend(["-c:a", "copy"])
        else:
            cmd.extend(["-c:a", "aac", "-b:a", self.config.get("audio_bitrate")])
        
        # Progress to FILE
        cmd.extend(["-progress", self.progress_file])
        
        cmd.append(output_path)
        
        self.log("START", f"Processing: {video_file.filename}")
        
        try:
            # No PIPE - let FFmpeg run free!
            self.current_process = subprocess.Popen(
                cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0
            )
            
            duration = video_file.duration
            
            # Monitor progress via file
            while self.current_process.poll() is None:
                if self.is_cancelled:
                    self.current_process.terminate()
                    self.cleanup_progress_file()
                    return False
                
                progress = self.read_progress_file(duration)
                if progress > 0:
                    video_file.progress = progress
                    if self.progress_callback:
                        self.progress_callback(video_file, progress)
                
                time.sleep(0.3)
            
            # Process completed
            return_code = self.current_process.returncode
            
            if return_code == 0:
                video_file.status = "completed"
                video_file.progress = 100
                
                if os.path.exists(output_path):
                    output_size = os.path.getsize(output_path)
                    reduction = int((1 - output_size / video_file.size) * 100)
                    self.log("DONE", f"Completed: {video_file.filename} (Saved {reduction}%)")
                
                self.cleanup_progress_file()
                return True
            else:
                video_file.status = "error"
                video_file.error = f"FFmpeg exited with code {return_code}"
                self.log("ERROR", f"FFmpeg failed with code: {return_code}")
                self.cleanup_progress_file()
                return False
                
        except Exception as e:
            video_file.status = "error"
            video_file.error = str(e)
            self.log("ERROR", f"Process error: {e}")
            self.cleanup_progress_file()
            return False
        finally:
            self.current_process = None
    
    def read_progress_file(self, duration):
        """Read progress from file"""
        try:
            if not os.path.exists(self.progress_file):
                return 0
            
            with open(self.progress_file, 'r') as f:
                content = f.read()
            
            matches = re.findall(r'out_time_ms=(\d+)', content)
            if matches:
                time_ms = int(matches[-1])
                current_sec = time_ms / 1000000
                if duration > 0:
                    return min(99, int((current_sec / duration) * 100))
            
            matches = re.findall(r'out_time=(\d+):(\d+):(\d+\.?\d*)', content)
            if matches:
                h, m, s = matches[-1]
                current_sec = int(h) * 3600 + int(m) * 60 + float(s)
                if duration > 0:
                    return min(99, int((current_sec / duration) * 100))
                    
        except Exception:
            pass
        
        return 0
    
    def cleanup_progress_file(self):
        """Remove temporary progress file"""
        try:
            if self.progress_file and os.path.exists(self.progress_file):
                os.remove(self.progress_file)
        except Exception:
            pass
        self.progress_file = None
    
    def cancel(self):
        """Cancel current processing"""
        self.is_cancelled = True
        if self.current_process:
            self.current_process.terminate()
        self.cleanup_progress_file()


# ============================================
# GUI Components
# ============================================
class QueueItem(ctk.CTkFrame):
    """Single item in the queue list"""
    
    def __init__(self, parent, video_file, on_remove=None, **kwargs):
        super().__init__(parent, **kwargs)
        self.video_file = video_file
        self.on_remove = on_remove
        
        self.configure(fg_color="#1a2333", corner_radius=8)
        
        self.grid_columnconfigure(1, weight=1)
        
        # Icon
        icon_frame = ctk.CTkFrame(self, width=40, height=40, fg_color="#232f48", corner_radius=4)
        icon_frame.grid(row=0, column=0, padx=(10, 10), pady=10)
        icon_frame.grid_propagate(False)
        
        icon_label = ctk.CTkLabel(icon_frame, text="🎬", font=("Arial", 16))
        icon_label.place(relx=0.5, rely=0.5, anchor="center")
        
        # File info
        info_frame = ctk.CTkFrame(self, fg_color="transparent")
        info_frame.grid(row=0, column=1, sticky="ew", pady=10)
        
        self.name_label = ctk.CTkLabel(
            info_frame, 
            text=video_file.filename,
            font=("Arial", 12, "bold"),
            text_color="white",
            anchor="w"
        )
        self.name_label.pack(fill="x")
        
        self.path_label = ctk.CTkLabel(
            info_frame,
            text=video_file.directory,
            font=("Arial", 10),
            text_color="#586a8a",
            anchor="w"
        )
        self.path_label.pack(fill="x")
        
        # Size
        size_str = self.format_size(video_file.size)
        self.size_label = ctk.CTkLabel(
            self, 
            text=size_str,
            font=("Arial", 11),
            text_color="#92a4c9",
            width=80
        )
        self.size_label.grid(row=0, column=2, padx=10)
        
        # Status
        self.status_label = ctk.CTkLabel(
            self,
            text=video_file.status.capitalize(),
            font=("Arial", 11, "bold"),
            text_color=self.get_status_color(),
            width=80
        )
        self.status_label.grid(row=0, column=3, padx=10)
        
        # Progress bar
        self.progress_bar = ctk.CTkProgressBar(self, width=150, height=8)
        self.progress_bar.set(video_file.progress / 100)
        self.progress_bar.grid(row=0, column=4, padx=10)
        
        # Remove button
        self.remove_btn = ctk.CTkButton(
            self,
            text="✕",
            width=30,
            height=30,
            fg_color="transparent",
            hover_color="#324467",
            text_color="#92a4c9",
            command=self.remove
        )
        self.remove_btn.grid(row=0, column=5, padx=10)
    
    def format_size(self, bytes_size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"
    
    def get_status_color(self):
        colors = {
            "pending": "#9ca3af",
            "processing": "#3b82f6",
            "completed": "#10b981",
            "error": "#ef4444",
            "skipped": "#f59e0b"
        }
        return colors.get(self.video_file.status, "#9ca3af")
    
    def update_display(self):
        self.status_label.configure(
            text=self.video_file.status.capitalize(),
            text_color=self.get_status_color()
        )
        self.progress_bar.set(self.video_file.progress / 100)
        
        if self.video_file.status == "completed":
            self.progress_bar.configure(progress_color="#10b981")
        elif self.video_file.status == "error":
            self.progress_bar.configure(progress_color="#ef4444")
        elif self.video_file.status == "processing":
            self.progress_bar.configure(progress_color="#135bec")
    
    def remove(self):
        if self.on_remove:
            self.on_remove(self.video_file)


class LogConsole(ctk.CTkFrame):
    """Console/Log output panel"""
    
    def __init__(self, parent, **kwargs):
        super().__init__(parent, **kwargs)
        
        self.configure(fg_color="#090c13", corner_radius=0)
        
        # Header
        header = ctk.CTkFrame(self, fg_color="#111722", height=40, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        dots_frame = ctk.CTkFrame(header, fg_color="transparent")
        dots_frame.pack(side="left", padx=10, pady=10)
        
        for color in ["#ef4444", "#eab308", "#22c55e"]:
            dot = ctk.CTkFrame(dots_frame, width=10, height=10, fg_color=color, corner_radius=5)
            dot.pack(side="left", padx=2)
        
        title = ctk.CTkLabel(
            header,
            text="CONSOLE OUTPUT",
            font=("Consolas", 10, "bold"),
            text_color="#92a4c9"
        )
        title.pack(side="left", padx=10)
        
        clear_btn = ctk.CTkButton(
            header,
            text="Clear",
            width=60,
            height=24,
            fg_color="#232f48",
            hover_color="#324467",
            font=("Arial", 10),
            command=self.clear
        )
        clear_btn.pack(side="right", padx=10, pady=8)
        
        self.log_text = ctk.CTkTextbox(
            self,
            font=("Consolas", 11),
            fg_color="#090c13",
            text_color="#92a4c9",
            wrap="word"
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=10)
    
    def log(self, level, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        self.log_text.configure(state="normal")
        self.log_text.insert("end", f"{timestamp}  [{level}]  {message}\n")
        self.log_text.configure(state="disabled")
        self.log_text.see("end")
    
    def clear(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")


class SettingsPanel(ctk.CTkToplevel):
    """Settings window"""
    
    def __init__(self, parent, config, on_save=None):
        super().__init__(parent)
        
        self.config = config
        self.on_save = on_save
        
        self.title("Settings - VideoProc")
        self.geometry("700x850")
        self.configure(fg_color="#0d121c")
        
        self.transient(parent)
        self.grab_set()
        
        self.create_widgets()
        self.load_settings()
    
    def create_widgets(self):
        main_frame = ctk.CTkScrollableFrame(self, fg_color="#0d121c")
        main_frame.pack(fill="both", expand=True, padx=20, pady=20)
        
        # Title
        title = ctk.CTkLabel(
            main_frame,
            text="Settings",
            font=("Arial", 28, "bold"),
            text_color="white"
        )
        title.pack(anchor="w", pady=(0, 5))
        
        subtitle = ctk.CTkLabel(
            main_frame,
            text="Configure encoding, paths, and performance options.",
            font=("Arial", 12),
            text_color="#92a4c9"
        )
        subtitle.pack(anchor="w", pady=(0, 20))
        
        # ---- Storage & Output Section ----
        self.create_section_header(main_frame, "📁", "Storage & Output")
        
        storage_frame = ctk.CTkFrame(main_frame, fg_color="#111722", corner_radius=10)
        storage_frame.pack(fill="x", pady=(0, 20))
        
        self.create_path_input(storage_frame, "Output Directory", "output_folder", is_folder=True)
        
        # Filename suffix
        suffix_frame = ctk.CTkFrame(storage_frame, fg_color="transparent")
        suffix_frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(suffix_frame, text="Filename Suffix", text_color="#92a4c9").pack(anchor="w")
        self.suffix_entry = ctk.CTkEntry(suffix_frame, width=200, fg_color="#0d121c", border_color="#324467")
        self.suffix_entry.pack(anchor="w", pady=5)
        ctk.CTkLabel(suffix_frame, text="Example: video_compressed.mp4", text_color="#586a8a", font=("Arial", 10)).pack(anchor="w")
        
        self.create_path_input(storage_frame, "FFmpeg Path", "ffmpeg_path", is_folder=False)
        self.create_path_input(storage_frame, "FFprobe Path", "ffprobe_path", is_folder=False)
        
        # ---- Encoding Settings Section ----
        self.create_section_header(main_frame, "⚙️", "Encoding Settings")
        
        encoding_frame = ctk.CTkFrame(main_frame, fg_color="#111722", corner_radius=10)
        encoding_frame.pack(fill="x", pady=(0, 20))
        
        # GPU Acceleration toggle
        gpu_frame = ctk.CTkFrame(encoding_frame, fg_color="transparent")
        gpu_frame.pack(fill="x", padx=15, pady=15)
        
        gpu_label_frame = ctk.CTkFrame(gpu_frame, fg_color="transparent")
        gpu_label_frame.pack(side="left")
        ctk.CTkLabel(gpu_label_frame, text="GPU Acceleration (NVENC)", text_color="white", font=("Arial", 12, "bold")).pack(anchor="w")
        ctk.CTkLabel(gpu_label_frame, text="Use NVIDIA GPU for hardware encoding", text_color="#92a4c9", font=("Arial", 10)).pack(anchor="w")
        
        self.gpu_switch = ctk.CTkSwitch(gpu_frame, text="", onvalue=True, offvalue=False)
        self.gpu_switch.pack(side="right")
        
        # Separator
        ctk.CTkFrame(encoding_frame, height=1, fg_color="#324467").pack(fill="x", padx=15)
        
        # Hardware Decode toggle
        hwdec_frame = ctk.CTkFrame(encoding_frame, fg_color="transparent")
        hwdec_frame.pack(fill="x", padx=15, pady=15)
        
        hwdec_label_frame = ctk.CTkFrame(hwdec_frame, fg_color="transparent")
        hwdec_label_frame.pack(side="left")
        ctk.CTkLabel(hwdec_label_frame, text="Hardware Decode (CUDA)", text_color="white", font=("Arial", 12, "bold")).pack(anchor="w")
        ctk.CTkLabel(hwdec_label_frame, text="Use GPU for decoding too (faster)", text_color="#92a4c9", font=("Arial", 10)).pack(anchor="w")
        
        self.hwdec_switch = ctk.CTkSwitch(hwdec_frame, text="", onvalue=True, offvalue=False)
        self.hwdec_switch.pack(side="right")
        
        # Separator
        ctk.CTkFrame(encoding_frame, height=1, fg_color="#324467").pack(fill="x", padx=15)
        
        # Encoder selection
        encoder_frame = ctk.CTkFrame(encoding_frame, fg_color="transparent")
        encoder_frame.pack(fill="x", padx=15, pady=15)
        
        enc_left = ctk.CTkFrame(encoder_frame, fg_color="transparent")
        enc_left.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        ctk.CTkLabel(enc_left, text="Video Encoder", text_color="#92a4c9").pack(anchor="w")
        self.encoder_combo = ctk.CTkComboBox(
            enc_left,
            values=[
                "h264_nvenc (NVIDIA GPU)",
                "hevc_nvenc (NVIDIA GPU)", 
                "libx264 (CPU)",
                "libx265 (CPU)"
            ],
            width=200,
            fg_color="#0d121c",
            border_color="#324467",
            button_color="#324467",
            dropdown_fg_color="#111722"
        )
        self.encoder_combo.pack(anchor="w", pady=5)
        
        enc_right = ctk.CTkFrame(encoder_frame, fg_color="transparent")
        enc_right.pack(side="right", fill="x", expand=True, padx=(10, 0))
        
        ctk.CTkLabel(enc_right, text="Encoder Preset", text_color="#92a4c9").pack(anchor="w")
        self.preset_combo = ctk.CTkComboBox(
            enc_right,
            values=["p1 - Fastest", "p2 - Faster", "p3 - Fast", "p4 - Medium", "p5 - Slow", "p6 - Slower", "p7 - Best Quality"],
            width=200,
            fg_color="#0d121c",
            border_color="#324467",
            button_color="#324467",
            dropdown_fg_color="#111722"
        )
        self.preset_combo.pack(anchor="w", pady=5)
        
        # Separator
        ctk.CTkFrame(encoding_frame, height=1, fg_color="#324467").pack(fill="x", padx=15)
        
        # Bitrate mode
        bitrate_frame = ctk.CTkFrame(encoding_frame, fg_color="transparent")
        bitrate_frame.pack(fill="x", padx=15, pady=15)
        
        bitrate_header = ctk.CTkFrame(bitrate_frame, fg_color="transparent")
        bitrate_header.pack(fill="x")
        
        ctk.CTkLabel(bitrate_header, text="Bitrate Control", text_color="#92a4c9").pack(side="left")
        
        mode_frame = ctk.CTkFrame(bitrate_header, fg_color="#0d121c", corner_radius=5)
        mode_frame.pack(side="right")
        
        self.bitrate_mode = ctk.StringVar(value="percentage")
        
        self.pct_btn = ctk.CTkButton(
            mode_frame, text="Percentage", width=100, height=28,
            fg_color="#324467", hover_color="#324467",
            command=lambda: self.set_bitrate_mode("percentage")
        )
        self.pct_btn.pack(side="left", padx=2, pady=2)
        
        self.size_btn = ctk.CTkButton(
            mode_frame, text="Target Size", width=100, height=28,
            fg_color="transparent", hover_color="#232f48",
            command=lambda: self.set_bitrate_mode("target_size")
        )
        self.size_btn.pack(side="left", padx=2, pady=2)
        
        # Percentage slider
        self.pct_frame = ctk.CTkFrame(bitrate_frame, fg_color="transparent")
        self.pct_frame.pack(fill="x", pady=10)
        
        pct_header = ctk.CTkFrame(self.pct_frame, fg_color="transparent")
        pct_header.pack(fill="x")
        ctk.CTkLabel(pct_header, text="Bitrate Percentage:", text_color="#586a8a", font=("Arial", 10)).pack(side="left")
        self.pct_value_label = ctk.CTkLabel(pct_header, text="33%", text_color="#135bec", font=("Arial", 12, "bold"))
        self.pct_value_label.pack(side="right")
        
        self.pct_slider = ctk.CTkSlider(
            self.pct_frame, from_=5, to=100,
            command=lambda v: self.pct_value_label.configure(text=f"{int(v)}%")
        )
        self.pct_slider.pack(fill="x", pady=5)
        
        pct_labels = ctk.CTkFrame(self.pct_frame, fg_color="transparent")
        pct_labels.pack(fill="x")
        ctk.CTkLabel(pct_labels, text="5%", text_color="#586a8a", font=("Arial", 9)).pack(side="left")
        ctk.CTkLabel(pct_labels, text="33% (1/3)", text_color="#586a8a", font=("Arial", 9)).pack(side="left", expand=True)
        ctk.CTkLabel(pct_labels, text="100%", text_color="#586a8a", font=("Arial", 9)).pack(side="right")
        
        # Target size slider
        self.size_frame = ctk.CTkFrame(bitrate_frame, fg_color="transparent")
        
        size_header = ctk.CTkFrame(self.size_frame, fg_color="transparent")
        size_header.pack(fill="x")
        ctk.CTkLabel(size_header, text="Target Size:", text_color="#586a8a", font=("Arial", 10)).pack(side="left")
        self.size_value_label = ctk.CTkLabel(size_header, text="5 MB", text_color="#135bec", font=("Arial", 12, "bold"))
        self.size_value_label.pack(side="right")
        
        self.size_slider = ctk.CTkSlider(
            self.size_frame, from_=1, to=100,
            command=lambda v: self.size_value_label.configure(text=f"{int(v)} MB")
        )
        self.size_slider.pack(fill="x", pady=5)
        
        size_labels = ctk.CTkFrame(self.size_frame, fg_color="transparent")
        size_labels.pack(fill="x")
        ctk.CTkLabel(size_labels, text="1 MB", text_color="#586a8a", font=("Arial", 9)).pack(side="left")
        ctk.CTkLabel(size_labels, text="50 MB", text_color="#586a8a", font=("Arial", 9)).pack(side="left", expand=True)
        ctk.CTkLabel(size_labels, text="100 MB", text_color="#586a8a", font=("Arial", 9)).pack(side="right")
        
        # Separator
        ctk.CTkFrame(encoding_frame, height=1, fg_color="#324467").pack(fill="x", padx=15)
        
        # Audio settings
        audio_frame = ctk.CTkFrame(encoding_frame, fg_color="transparent")
        audio_frame.pack(fill="x", padx=15, pady=15)
        
        audio_label_frame = ctk.CTkFrame(audio_frame, fg_color="transparent")
        audio_label_frame.pack(side="left")
        ctk.CTkLabel(audio_label_frame, text="Copy Audio (No Re-encode)", text_color="white", font=("Arial", 12, "bold")).pack(anchor="w")
        ctk.CTkLabel(audio_label_frame, text="Preserve original audio quality", text_color="#92a4c9", font=("Arial", 10)).pack(anchor="w")
        
        self.copy_audio_switch = ctk.CTkSwitch(audio_frame, text="", onvalue=True, offvalue=False)
        self.copy_audio_switch.pack(side="right")
        
        # Audio bitrate
        self.audio_bitrate_frame = ctk.CTkFrame(encoding_frame, fg_color="transparent")
        self.audio_bitrate_frame.pack(fill="x", padx=15, pady=(0, 15))
        
        ctk.CTkLabel(self.audio_bitrate_frame, text="Audio Bitrate", text_color="#92a4c9").pack(anchor="w")
        self.audio_bitrate_combo = ctk.CTkComboBox(
            self.audio_bitrate_frame,
            values=["64k", "96k", "128k", "192k", "256k", "320k"],
            width=150,
            fg_color="#0d121c",
            border_color="#324467",
            button_color="#324467",
            dropdown_fg_color="#111722"
        )
        self.audio_bitrate_combo.pack(anchor="w", pady=5)
        
        # ---- Buttons ----
        button_frame = ctk.CTkFrame(main_frame, fg_color="transparent")
        button_frame.pack(fill="x", pady=20)
        
        ctk.CTkButton(
            button_frame,
            text="Reset Defaults",
            fg_color="#232f48",
            hover_color="#324467",
            width=120,
            command=self.reset_defaults
        ).pack(side="left")
        
        ctk.CTkButton(
            button_frame,
            text="Save Changes",
            fg_color="#135bec",
            hover_color="#1d4ed8",
            width=120,
            command=self.save_settings
        ).pack(side="right")
    
    def create_section_header(self, parent, icon, title):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", pady=(10, 5))
        
        ctk.CTkLabel(frame, text=f"{icon}  {title}", font=("Arial", 14, "bold"), text_color="white").pack(side="left")
        ctk.CTkFrame(frame, height=1, fg_color="#324467").pack(side="left", fill="x", expand=True, padx=10)
    
    def create_path_input(self, parent, label, config_key, is_folder=True):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=10)
        
        ctk.CTkLabel(frame, text=label, text_color="#92a4c9").pack(anchor="w")
        
        input_frame = ctk.CTkFrame(frame, fg_color="transparent")
        input_frame.pack(fill="x", pady=5)
        
        entry = ctk.CTkEntry(input_frame, fg_color="#0d121c", border_color="#324467")
        entry.pack(side="left", fill="x", expand=True)
        
        def browse():
            if is_folder:
                path = filedialog.askdirectory()
            else:
                path = filedialog.askopenfilename(filetypes=[("Executable", "*.exe"), ("All files", "*.*")])
            if path:
                entry.delete(0, "end")
                entry.insert(0, path)
        
        ctk.CTkButton(
            input_frame,
            text="Browse",
            width=70,
            fg_color="#232f48",
            hover_color="#324467",
            command=browse
        ).pack(side="right", padx=(10, 0))
        
        setattr(self, f"{config_key}_entry", entry)
    
    def set_bitrate_mode(self, mode):
        self.bitrate_mode.set(mode)
        
        if mode == "percentage":
            self.pct_btn.configure(fg_color="#324467")
            self.size_btn.configure(fg_color="transparent")
            self.pct_frame.pack(fill="x", pady=10)
            self.size_frame.pack_forget()
        else:
            self.size_btn.configure(fg_color="#324467")
            self.pct_btn.configure(fg_color="transparent")
            self.size_frame.pack(fill="x", pady=10)
            self.pct_frame.pack_forget()
    
    def load_settings(self):
        self.output_folder_entry.delete(0, "end")
        self.output_folder_entry.insert(0, self.config.get("output_folder"))
        
        self.suffix_entry.delete(0, "end")
        self.suffix_entry.insert(0, self.config.get("filename_suffix"))
        
        self.ffmpeg_path_entry.delete(0, "end")
        self.ffmpeg_path_entry.insert(0, self.config.get("ffmpeg_path"))
        
        self.ffprobe_path_entry.delete(0, "end")
        self.ffprobe_path_entry.insert(0, self.config.get("ffprobe_path"))
        
        if self.config.get("gpu_acceleration"):
            self.gpu_switch.select()
        else:
            self.gpu_switch.deselect()
        
        if self.config.get("hardware_decode"):
            self.hwdec_switch.select()
        else:
            self.hwdec_switch.deselect()
        
        encoder = self.config.get("encoder")
        encoder_map = {
            "h264_nvenc": "h264_nvenc (NVIDIA GPU)",
            "hevc_nvenc": "hevc_nvenc (NVIDIA GPU)",
            "libx264": "libx264 (CPU)",
            "libx265": "libx265 (CPU)"
        }
        self.encoder_combo.set(encoder_map.get(encoder, encoder_map["h264_nvenc"]))
        
        preset = self.config.get("encoder_preset")
        preset_map = {
            "p1": "p1 - Fastest", "p2": "p2 - Faster", "p3": "p3 - Fast",
            "p4": "p4 - Medium", "p5": "p5 - Slow", "p6": "p6 - Slower", "p7": "p7 - Best Quality"
        }
        self.preset_combo.set(preset_map.get(preset, preset_map["p4"]))
        
        self.set_bitrate_mode(self.config.get("bitrate_mode"))
        self.pct_slider.set(self.config.get("bitrate_percentage"))
        self.pct_value_label.configure(text=f"{self.config.get('bitrate_percentage')}%")
        self.size_slider.set(self.config.get("target_size_mb"))
        self.size_value_label.configure(text=f"{self.config.get('target_size_mb')} MB")
        
        if self.config.get("copy_audio"):
            self.copy_audio_switch.select()
        else:
            self.copy_audio_switch.deselect()
        
        self.audio_bitrate_combo.set(self.config.get("audio_bitrate"))
    
    def save_settings(self):
        self.config.set("output_folder", self.output_folder_entry.get())
        self.config.set("filename_suffix", self.suffix_entry.get())
        self.config.set("ffmpeg_path", self.ffmpeg_path_entry.get())
        self.config.set("ffprobe_path", self.ffprobe_path_entry.get())
        self.config.set("gpu_acceleration", self.gpu_switch.get())
        self.config.set("hardware_decode", self.hwdec_switch.get())
        
        encoder_text = self.encoder_combo.get()
        if "h264_nvenc" in encoder_text:
            self.config.set("encoder", "h264_nvenc")
        elif "hevc_nvenc" in encoder_text:
            self.config.set("encoder", "hevc_nvenc")
        elif "libx264" in encoder_text:
            self.config.set("encoder", "libx264")
        elif "libx265" in encoder_text:
            self.config.set("encoder", "libx265")
        
        preset_text = self.preset_combo.get()
        preset = preset_text.split(" ")[0]
        self.config.set("encoder_preset", preset)
        
        self.config.set("bitrate_mode", self.bitrate_mode.get())
        self.config.set("bitrate_percentage", int(self.pct_slider.get()))
        self.config.set("target_size_mb", int(self.size_slider.get()))
        self.config.set("copy_audio", self.copy_audio_switch.get())
        self.config.set("audio_bitrate", self.audio_bitrate_combo.get())
        
        self.config.save()
        
        if self.on_save:
            self.on_save()
        
        self.destroy()
    
    def reset_defaults(self):
        for key, value in DEFAULT_CONFIG.items():
            self.config.set(key, value)
        self.load_settings()


# ============================================
# Main Application
# ============================================
class VideoProcessorApp(ctk.CTk):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        
        self.title("VideoProc - Video Processor")
        self.geometry("1300x850")
        self.minsize(1100, 700)
        
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.configure(fg_color="#0d121c")
        
        self.config = Config()
        self.queue = []
        self.queue_items = {}
        self.is_processing = False
        self.processor = None
        self.processing_thread = None
        self.queue_state = QueueStateManager()
        
        # Setup exit handler
        self.protocol("WM_DELETE_WINDOW", self.on_close)
        atexit.register(self.save_queue_on_exit)
        
        self.create_widgets()
        
        # Check for resume on startup
        self.after(500, self.check_resume)
    
    def save_queue_on_exit(self):
        """Save queue when app closes"""
        if self.queue:
            self.queue_state.save(self.queue)
    
    def on_close(self):
        """Handle window close"""
        if self.is_processing:
            if messagebox.askyesno("Confirm", "Processing in progress. Stop and save queue?"):
                self.stop_processing()
                self.queue_state.save(self.queue)
        elif self.queue:
            self.queue_state.save(self.queue)
        
        self.destroy()
    
    def check_resume(self):
        """Check for saved queue on startup"""
        if not self.queue_state.exists():
            return
        
        data = self.queue_state.load()
        if not data or not data.get("files"):
            self.queue_state.clear()
            return
        
        files = data["files"]
        incomplete = [f for f in files if f["status"] != "completed"]
        
        if not incomplete:
            self.queue_state.clear()
            return
        
        if messagebox.askyesno(
            "Resume Queue",
            f"Found saved queue with {len(incomplete)} incomplete file(s).\n\nResume?"
        ):
            self.restore_queue(files)
        else:
            self.queue_state.clear()
    
    def restore_queue(self, files):
        """Restore queue from saved state"""
        output_folder = self.config.get("output_folder")
        suffix = self.config.get("filename_suffix")
        
        for f in files:
            path = f["path"]
            
            # Check if file still exists
            if not os.path.exists(path):
                self.console.log("WARN", f"File missing: {os.path.basename(path)}")
                continue
            
            video_file = VideoFile(path)
            video_file.size = f.get("size", 0)
            video_file.duration = f.get("duration", 0)
            video_file.bitrate = f.get("bitrate", 0)
            video_file.video_bitrate = f.get("video_bitrate", 0)
            
            # Check if output exists
            base_name = Path(path).stem
            output_path = os.path.join(output_folder, f"{base_name}{suffix}.mp4")
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                video_file.status = "completed"
                video_file.progress = 100
            else:
                video_file.status = "pending"
            
            self.queue.append(video_file)
            self.add_queue_item(video_file)
        
        self.update_stats()
        self.queue_state.clear()
        
        pending = len([vf for vf in self.queue if vf.status == "pending"])
        self.console.log("INFO", f"Restored {len(self.queue)} files, {pending} pending")
    
    def create_widgets(self):
        main_container = ctk.CTkFrame(self, fg_color="transparent")
        main_container.pack(fill="both", expand=True)
        
        self.create_sidebar(main_container)
        
        content = ctk.CTkFrame(main_container, fg_color="#0d121c")
        content.pack(side="left", fill="both", expand=True)
        
        self.create_header(content)
        self.create_stats_bar(content)
        
        self.queue_frame = ctk.CTkScrollableFrame(
            content, 
            fg_color="#111722",
            corner_radius=10
        )
        self.queue_frame.pack(fill="both", expand=True, padx=20, pady=(0, 10))
        
        self.empty_state = ctk.CTkFrame(self.queue_frame, fg_color="#1a2333", corner_radius=10)
        self.empty_state.pack(fill="both", expand=True, pady=50)
        
        empty_inner = ctk.CTkFrame(self.empty_state, fg_color="transparent")
        empty_inner.pack(expand=True)
        
        ctk.CTkLabel(empty_inner, text="📤", font=("Arial", 48)).pack(pady=10)
        ctk.CTkLabel(
            empty_inner, 
            text="Drop video files here",
            font=("Arial", 16, "bold"),
            text_color="#92a4c9"
        ).pack()
        ctk.CTkLabel(
            empty_inner,
            text="or click 'Add Files' to browse",
            font=("Arial", 12),
            text_color="#586a8a"
        ).pack(pady=5)
        ctk.CTkLabel(
            empty_inner,
            text="Supports: MP4, MKV, MOV, AVI, WMV, FLV, WebM",
            font=("Arial", 10),
            text_color="#586a8a"
        ).pack()
        
        self.console = LogConsole(content, height=180)
        self.console.pack(fill="x", padx=0, pady=0)
        
        self.console.log("INFO", "Application ready. Full GPU acceleration enabled!")
        self.console.log("INFO", "Using file-based progress (no pipe blocking)")
    
    def create_sidebar(self, parent):
        sidebar = ctk.CTkFrame(parent, width=250, fg_color="#111722", corner_radius=0)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)
        
        logo_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        logo_frame.pack(fill="x", padx=20, pady=20)
        
        ctk.CTkLabel(
            logo_frame,
            text="🎬 VideoProc",
            font=("Arial", 20, "bold"),
            text_color="white"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            logo_frame,
            text="v2.6.0 • Full GPU + Resume",
            font=("Arial", 10),
            text_color="#92a4c9"
        ).pack(anchor="w")
        
        nav_frame = ctk.CTkFrame(sidebar, fg_color="transparent")
        nav_frame.pack(fill="x", padx=15, pady=10)
        
        nav_buttons = [
            ("🎵", "Processing Queue", lambda: None, True),
            ("📂", "Output Folder", self.open_output_folder, False),
            ("🔄", "Rescan Missing", self.rescan_queue, False),
            ("⚙️", "Settings", self.open_settings, False),
        ]
        
        for icon, text, command, active in nav_buttons:
            btn = ctk.CTkButton(
                nav_frame,
                text=f"  {icon}  {text}",
                anchor="w",
                fg_color="#232f48" if active else "transparent",
                hover_color="#232f48",
                text_color="white" if active else "#92a4c9",
                height=40,
                command=command
            )
            btn.pack(fill="x", pady=2)
        
        ctk.CTkFrame(sidebar, fg_color="transparent", height=1).pack(fill="both", expand=True)
        
        controls_frame = ctk.CTkFrame(sidebar, fg_color="#0d121c", corner_radius=0)
        controls_frame.pack(fill="x", side="bottom")
        
        progress_info = ctk.CTkFrame(controls_frame, fg_color="transparent")
        progress_info.pack(fill="x", padx=15, pady=15)
        
        self.status_label = ctk.CTkLabel(
            progress_info,
            text="Status: Idle",
            font=("Arial", 11),
            text_color="#92a4c9"
        )
        self.status_label.pack(anchor="w")
        
        self.overall_progress = ctk.CTkProgressBar(progress_info, height=6)
        self.overall_progress.set(0)
        self.overall_progress.pack(fill="x", pady=10)
        
        self.start_btn = ctk.CTkButton(
            controls_frame,
            text="▶  Start Processing",
            fg_color="#135bec",
            hover_color="#1d4ed8",
            height=45,
            font=("Arial", 13, "bold"),
            command=self.start_processing
        )
        self.start_btn.pack(fill="x", padx=15, pady=(0, 10))
        
        self.stop_btn = ctk.CTkButton(
            controls_frame,
            text="⏹  Stop Processing",
            fg_color="#dc2626",
            hover_color="#b91c1c",
            height=45,
            font=("Arial", 13, "bold"),
            command=self.stop_processing
        )
        
        self.clear_btn = ctk.CTkButton(
            controls_frame,
            text="Clear Queue",
            fg_color="#232f48",
            hover_color="#324467",
            height=35,
            command=self.clear_queue
        )
        self.clear_btn.pack(fill="x", padx=15, pady=(0, 15))
    
    def create_header(self, parent):
        header = ctk.CTkFrame(parent, fg_color="#111722", height=100, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        title_frame = ctk.CTkFrame(header, fg_color="transparent")
        title_frame.pack(side="left", padx=20, pady=20)
        
        ctk.CTkLabel(
            title_frame,
            text="Video Queue",
            font=("Arial", 28, "bold"),
            text_color="white"
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            title_frame,
            text="Add videos and compress them with full GPU acceleration.",
            font=("Arial", 12),
            text_color="#92a4c9"
        ).pack(anchor="w")
        
        ctk.CTkButton(
            header,
            text="➕  Add Files",
            fg_color="white",
            text_color="black",
            hover_color="#e5e5e5",
            height=40,
            width=120,
            font=("Arial", 12, "bold"),
            command=self.add_files
        ).pack(side="right", padx=20, pady=30)
        
        ctk.CTkButton(
            header,
            text="📁  Add Folder",
            fg_color="#232f48",
            text_color="white",
            hover_color="#324467",
            height=40,
            width=120,
            font=("Arial", 12, "bold"),
            command=self.add_folder
        ).pack(side="right", padx=5, pady=30)
    
    def create_stats_bar(self, parent):
        stats_frame = ctk.CTkFrame(parent, fg_color="transparent")
        stats_frame.pack(fill="x", padx=20, pady=15)
        
        stats = [
            ("📁", "Total Files", "stat_total", "0"),
            ("💾", "Total Size", "stat_size", "0 MB"),
            ("⏳", "Pending", "stat_pending", "0"),
            ("✅", "Completed", "stat_completed", "0"),
        ]
        
        for icon, title, attr, default in stats:
            card = ctk.CTkFrame(stats_frame, fg_color="#111722", corner_radius=10)
            card.pack(side="left", fill="x", expand=True, padx=5)
            
            inner = ctk.CTkFrame(card, fg_color="transparent")
            inner.pack(padx=15, pady=15)
            
            ctk.CTkLabel(
                inner,
                text=f"{icon}  {title}",
                font=("Arial", 10, "bold"),
                text_color="#92a4c9"
            ).pack(anchor="w")
            
            label = ctk.CTkLabel(
                inner,
                text=default,
                font=("Arial", 22, "bold"),
                text_color="white"
            )
            label.pack(anchor="w")
            
            setattr(self, attr, label)
    
    def add_files(self):
        filetypes = [
            ("Video files", "*.mp4 *.mkv *.mov *.avi *.wmv *.flv *.webm"),
            ("All files", "*.*")
        ]
        
        files = filedialog.askopenfilenames(filetypes=filetypes)
        
        if files:
            self.add_to_queue(files)
    
    def add_folder(self):
        """Add all videos from a folder"""
        folder = filedialog.askdirectory()
        if not folder:
            return
        
        extensions = {'.mp4', '.mkv', '.mov', '.avi', '.wmv', '.flv', '.webm'}
        files = []
        
        for root, dirs, filenames in os.walk(folder):
            for f in filenames:
                if Path(f).suffix.lower() in extensions:
                    files.append(os.path.join(root, f))
        
        if files:
            self.add_to_queue(files)
        else:
            messagebox.showinfo("Info", "No video files found")
    
    def add_to_queue(self, file_paths):
        processor = FFmpegProcessor(self.config, self.console.log)
        
        for path in file_paths:
            if path in [vf.path for vf in self.queue]:
                continue
            
            video_file = VideoFile(path)
            
            info = processor.get_video_info(path)
            if info:
                video_file.size = info["size"]
                video_file.duration = info["duration"]
                video_file.bitrate = info["bitrate"]
                video_file.video_bitrate = info["video_bitrate"]
            else:
                video_file.status = "error"
                video_file.error = "Could not read file info"
            
            self.queue.append(video_file)
            self.add_queue_item(video_file)
        
        self.update_stats()
        self.console.log("INFO", f"Added {len(file_paths)} file(s) to queue")
    
    def add_queue_item(self, video_file):
        self.empty_state.pack_forget()
        
        item = QueueItem(
            self.queue_frame,
            video_file,
            on_remove=self.remove_from_queue
        )
        item.pack(fill="x", pady=5, padx=5)
        self.queue_items[video_file] = item
    
    def remove_from_queue(self, video_file):
        if video_file.status == "processing":
            return
        
        if video_file in self.queue:
            self.queue.remove(video_file)
        
        if video_file in self.queue_items:
            self.queue_items[video_file].destroy()
            del self.queue_items[video_file]
        
        self.update_stats()
        
        if not self.queue:
            self.empty_state.pack(fill="both", expand=True, pady=50)
    
    def clear_queue(self):
        to_remove = [vf for vf in self.queue if vf.status != "processing"]
        
        for vf in to_remove:
            self.remove_from_queue(vf)
        
        self.queue_state.clear()
        self.console.log("INFO", "Queue cleared")
    
    def rescan_queue(self):
        """Rescan queue - check which outputs exist"""
        if not self.queue:
            messagebox.showinfo("Info", "Queue is empty")
            return
        
        output_folder = self.config.get("output_folder")
        suffix = self.config.get("filename_suffix")
        
        updated = 0
        reset = 0
        
        for vf in self.queue:
            base_name = Path(vf.path).stem
            output_path = os.path.join(output_folder, f"{base_name}{suffix}.mp4")
            
            if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                if vf.status != "completed":
                    vf.status = "completed"
                    vf.progress = 100
                    updated += 1
            else:
                if vf.status == "completed":
                    vf.status = "pending"
                    vf.progress = 0
                    reset += 1
            
            if vf in self.queue_items:
                self.queue_items[vf].update_display()
        
        self.update_stats()
        self.console.log("INFO", f"Rescan: {updated} completed, {reset} reset to pending")
    
    def update_stats(self):
        total = len(self.queue)
        pending = len([vf for vf in self.queue if vf.status == "pending"])
        completed = len([vf for vf in self.queue if vf.status == "completed"])
        total_size = sum(vf.size for vf in self.queue)
        
        self.stat_total.configure(text=str(total))
        self.stat_pending.configure(text=str(pending))
        self.stat_completed.configure(text=str(completed))
        self.stat_size.configure(text=self.format_size(total_size))
        
        if total > 0:
            progress = completed / total
            self.overall_progress.set(progress)
    
    def format_size(self, bytes_size):
        for unit in ['B', 'KB', 'MB', 'GB']:
            if bytes_size < 1024:
                return f"{bytes_size:.1f} {unit}"
            bytes_size /= 1024
        return f"{bytes_size:.1f} TB"
    
    def start_processing(self):
        """Start processing - ALL CHECKS HAPPEN HERE, BEFORE PROCESSING"""
        
        # ========== PRE-PROCESSING CHECKS ==========
        
        # 1. Check FFmpeg exists
        ffmpeg_path = self.config.get("ffmpeg_path")
        if not os.path.exists(ffmpeg_path):
            messagebox.showerror("Error", f"FFmpeg not found:\n{ffmpeg_path}\n\nPlease fix in Settings.")
            return
        
        # 2. Check output folder
        output_folder = self.config.get("output_folder")
        try:
            os.makedirs(output_folder, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Error", f"Cannot create output folder:\n{e}")
            return
        
        # 3. Check which files are already done
        suffix = self.config.get("filename_suffix")
        skipped = 0
        
        for vf in self.queue:
            if vf.status == "pending":
                # Check if output already exists
                base_name = Path(vf.path).stem
                output_path = os.path.join(output_folder, f"{base_name}{suffix}.mp4")
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 0:
                    vf.status = "completed"
                    vf.progress = 100
                    vf.output_path = output_path
                    skipped += 1
                    if vf in self.queue_items:
                        self.queue_items[vf].update_display()
                
                # Check if input file still exists
                elif not os.path.exists(vf.path):
                    vf.status = "error"
                    vf.error = "File not found"
                    if vf in self.queue_items:
                        self.queue_items[vf].update_display()
        
        if skipped > 0:
            self.console.log("INFO", f"Skipped {skipped} already completed file(s)")
            self.update_stats()
        
        # 4. Check if any pending files remain
        pending = [vf for vf in self.queue if vf.status == "pending"]
        
        if not pending:
            messagebox.showinfo("Info", "No pending files to process.\n\nAll files are already completed!")
            return
        
        # ========== START PROCESSING ==========
        
        self.console.log("INFO", f"Starting processing: {len(pending)} file(s)")
        
        self.is_processing = True
        self.update_processing_ui()
        
        # Save queue state
        self.queue_state.save(self.queue)
        
        self.processing_thread = threading.Thread(target=self.process_queue, daemon=True)
        self.processing_thread.start()
    
    def process_queue(self):
        """Process queue - FAST, NO EXTRA CHECKS"""
        self.processor = FFmpegProcessor(
            self.config,
            log_callback=lambda l, m: self.after(0, lambda: self.console.log(l, m)),
            progress_callback=self.on_progress_update
        )
        
        for video_file in self.queue:
            if not self.is_processing:
                break
            
            if video_file.status != "pending":
                continue
            
            video_file.status = "processing"
            self.after(0, lambda vf=video_file: self.update_queue_item(vf))
            
            # Process video (fast, no extra checks inside)
            success = self.processor.process_video(video_file)
            
            self.after(0, lambda vf=video_file: self.update_queue_item(vf))
            self.after(0, self.update_stats)
            
            # Save state after each file
            self.queue_state.save(self.queue)
        
        self.is_processing = False
        self.after(0, self.update_processing_ui)
        self.after(0, lambda: self.console.log("INFO", "All processing complete!"))
        
        # Clear state if all done
        pending = len([vf for vf in self.queue if vf.status == "pending"])
        if pending == 0:
            self.queue_state.clear()
    
    def on_progress_update(self, video_file, progress):
        self.after(0, lambda: self.update_queue_item(video_file))
    
    def update_queue_item(self, video_file):
        if video_file in self.queue_items:
            self.queue_items[video_file].update_display()
    
    def stop_processing(self):
        self.is_processing = False
        if self.processor:
            self.processor.cancel()
        self.queue_state.save(self.queue)
        self.console.log("WARN", "Processing stopped - queue saved")
        self.update_processing_ui()
    
    def update_processing_ui(self):
        if self.is_processing:
            self.start_btn.pack_forget()
            self.stop_btn.pack(fill="x", padx=15, pady=(0, 10))
            self.status_label.configure(text="Status: Processing...")
        else:
            self.stop_btn.pack_forget()
            self.start_btn.pack(fill="x", padx=15, pady=(0, 10))
            self.status_label.configure(text="Status: Idle")
    
    def open_settings(self):
        SettingsPanel(self, self.config, on_save=self.on_settings_saved)
    
    def on_settings_saved(self):
        self.console.log("INFO", "Settings saved")
    
    def open_output_folder(self):
        output_folder = self.config.get("output_folder")
        try:
            os.makedirs(output_folder, exist_ok=True)
            if os.name == 'nt':
                os.startfile(output_folder)
            else:
                subprocess.run(['xdg-open', output_folder])
        except Exception as e:
            messagebox.showwarning("Warning", f"Cannot open folder:\n{e}")


# ============================================
# Entry Point
# ============================================
if __name__ == "__main__":
    app = VideoProcessorApp()
    app.mainloop()