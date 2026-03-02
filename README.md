# 🎬 VideoProc - Smart Video Compressor
### 1. Download & Run


<img width="653" height="662" alt="image" src="https://github.com/user-attachments/assets/6ce50cc7-dbcf-4b20-8ba8-81dffa71d8bd" />


# Encoding Settings Guide

This section explains what each setting does in a simple way.

---

## 1. GPU Acceleration NVENC

Uses your NVIDIA graphics card to encode the video.

ON  
Faster export  
Less CPU usage  

OFF  
Uses CPU  
Slower

Recommended: ON if you have NVIDIA GPU.

---

## 2. Hardware Decode CUDA

Uses GPU to read and decode the video before encoding.

ON  
Faster processing  
Better performance for large videos  

OFF  
CPU handles decoding  

Recommended: ON for modern GPUs.

---

## 3. Video Encoder

This is the compression method used to create the final video.

### h264 nvenc
Most compatible format  
Works on almost all devices  
Good balance of quality and size  

### hevc nvenc
Smaller file size  
Better compression  
Not supported on some older devices  

If you want maximum compatibility choose h264.  
If you want smaller files choose hevc.

---

## 4. Encoder Preset

Controls speed versus quality.

Lower preset number  
Faster encoding  
Slightly larger file  
Slightly lower quality  

Higher preset number  
Slower encoding  
Better compression  
Better quality  

Example  
p4 is balanced  
p6 or p7 gives better quality but slower  

Recommended  
p4 for normal use  
p6 for higher quality exports

---

## 5. Bitrate Control

Controls final file size and quality.

### Percentage Mode
Reduces original bitrate by percent.  
Simple and fast.  

Example  
33 percent means file becomes about one third of original size.

### Target Size Mode
You choose exact final file size.  
More precise but slower.

---

## 6. Target Size

Only works in Target Size mode.  
Set final size like 100 MB or 500 MB.

---

## 7. Copy Audio No Re encode

Keeps original audio without compressing again.

ON  
Faster export  
No audio quality loss  

OFF  
Audio will be recompressed  

Recommended: ON unless you need smaller audio size.

---

## 8. Audio Bitrate

Controls audio quality.

128k  
Normal quality  

192k  
Good quality  

320k  
Very high quality  

Recommended  
128k for normal videos  
192k for higher quality content

---

# Recommended Settings For Most Users

GPU Acceleration: ON  
Hardware Decode: ON  
Encoder: h264 nvenc  
Preset: p4  
Bitrate Mode: Percentage 30 to 40 percent  
Copy Audio: ON  
Audio Bitrate: 128k or 192k
