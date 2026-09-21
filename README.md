<div align="center">

# 📁 File Organizer

**Automatically sort files into folders by type — right from the terminal.**

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Bash](https://img.shields.io/badge/Bash-shell-4EAA25?logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)
[![Linux](https://img.shields.io/badge/Linux-ready-FCC624?logo=linux&logoColor=black)](https://www.linux.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](#license)

</div>

---

## ✨ What it does

Point it at a messy directory and it sorts every file into `organized_files/` by category — no more digging through a Downloads folder full of clutter.

| Category | Extensions |
|---|---|
| 📄 **Documents** | `pdf` `doc` `docx` `txt` `odt` `rtf` `xls` `xlsx` `ppt` `pptx` `csv` `md` |
| 🖼️ **Images** | `jpg` `jpeg` `png` `gif` `bmp` `svg` `webp` `tiff` `ico` |
| 🎬 **Videos** | `mp4` `mkv` `mov` `avi` `wmv` `flv` `webm` |
| 🗜️ **Archives** | `zip` `tar` `gz` `rar` `7z` `bz2` `xz` |
| 🎵 **Music** | `mp3` `wav` `flac` `aac` `ogg` `m4a` |
| 📦 **Others** | anything that doesn't match above |

Existing subfolders are left untouched, and name collisions are resolved automatically (`file_1.ext`, `file_2.ext`, ...).

## 🚀 Usage

```bash
# Organize the current directory
./organizer.sh

# Organize a specific directory
./organizer.sh ~/Downloads

# Preview what would happen — nothing is moved
./organizer.sh ~/Downloads --dry-run

# Send organized files to a custom destination
./organizer.sh ~/Downloads -o ~/Sorted
```

Or run the Python script directly:

```bash
python3 organizer.py ~/Downloads
```

## 🧪 Try the demo

A [`demo/`](demo) folder with sample empty files is included so you can see it in action:

```bash
./organizer.sh demo
```

<details>
<summary>Expected output</summary>

```
✓ Organized 6 file(s) successfully!

organized_files/
├── Archives/
│   └── backup.zip
├── Documents/
│   ├── notes.docx
│   └── resume.pdf
├── Images/
│   ├── photo1.jpg
│   └── photo2.png
└── Videos/
    └── video1.mp4
```

</details>

## 🛠️ Built with

Bash · Python · Linux
