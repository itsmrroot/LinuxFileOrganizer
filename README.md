<div align="center">

# 📁 File Organizer

**Automatically sort files into folders by type — right from the terminal.**

[![Python](https://img.shields.io/badge/Python-3.8+-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Bash](https://img.shields.io/badge/Bash-shell-4EAA25?logo=gnubash&logoColor=white)](https://www.gnu.org/software/bash/)
[![Linux](https://img.shields.io/badge/Linux-ready-FCC624?logo=linux&logoColor=black)](https://www.linux.org/)
[![License](https://img.shields.io/badge/license-MIT-blue)](LICENSE)

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

Existing subfolders are left untouched, and name collisions are resolved automatically (`file_1.ext`, `file_2.ext`, ...). Files that are byte-for-byte duplicates of something already organized are detected by content hash and skipped instead of renamed.

## 📦 Installation

Install it like any other command-line tool. [pipx](https://pipx.pypa.io) is recommended since it keeps CLI tools isolated from your system Python:

```bash
git clone https://github.com/itsmrroot/LinuxFileOrganizer.git
cd LinuxFileOrganizer
pipx install .
```

No pipx? Plain pip works too:

```bash
pip install --user .
```

Either way, this puts a `forganize` command on your `$PATH`. Run `forganize -h` to confirm it worked.

### Uninstalling

```bash
pipx uninstall file-organizer
# or, if installed with pip
pip uninstall file-organizer
```

This removes the `forganize` command. If you also cloned the repo, delete that folder separately (e.g. `rm -rf LinuxFileOrganizer`).

## 🚀 Usage

```bash
forganize -h                        # show all options
forganize                           # organize the current directory
forganize ~/Downloads               # organize a specific directory
forganize ~/Downloads -n            # preview only — nothing is moved (--dry-run)
forganize ~/Downloads -c            # copy instead of move (--copy)
forganize ~/Downloads -r            # also organize subdirectories (--recursive)
forganize ~/Downloads -o ~/Sorted   # send output to a custom destination (--output)
forganize ~/Downloads -u            # undo the last organize run (--undo)
forganize ~/Downloads -w            # watch and organize new files continuously (--watch)
forganize -v                        # print the installed version
```

Prefer not to install anything? Run it straight from a clone:

```bash
./organizer.sh ~/Downloads
# or
python3 organizer.py ~/Downloads
```

Every real run (not `-n`/`--dry-run`) writes a `.organizer_log.json` manifest into the destination folder, which is what `-u`/`--undo` reads to reverse the operation. A single failed file (e.g. a permission error) is reported without aborting the rest of the run.

## 🔁 Duplicate detection

Every real run hashes new files with SHA-256 and compares them against everything already in the destination. An exact content match is reported as a duplicate and left where it is — it's never silently renamed alongside a copy of itself.

```bash
forganize ~/Downloads --no-dedupe          # disable hashing (faster on huge folders)
forganize ~/Downloads --remove-duplicates  # also delete duplicate sources (move mode only)
```

## 🗂️ Custom categories

Don't like the built-in categories? Point `forganize` at your own JSON file:

```bash
forganize --print-config > ~/.config/forganize/config.json   # start from the defaults
$EDITOR ~/.config/forganize/config.json                      # edit categories/extensions
forganize ~/Downloads                                        # picked up automatically
```

`~/.config/forganize/config.json` is used automatically when present. Pass `-f/--config path/to/file.json` to use a different file for a single run. The format is `{"Category": ["ext1", "ext2"]}` — the leading dot on extensions is optional.

## 👀 Watch mode

Leave it running and it organizes new files as they land, skipping anything still mid-write:

```bash
forganize ~/Downloads --watch                # poll every 5s (default)
forganize ~/Downloads --watch --interval 30  # poll every 30s instead
```

Press `Ctrl+C` to stop. To run it permanently in the background, install it as a [systemd](https://www.freedesktop.org/wiki/Software/systemd/) user service:

```bash
mkdir -p ~/.config/systemd/user
cp packaging/forganize@.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable --now forganize@$(systemd-escape -p ~/Downloads).service
```

Check on it with `systemctl --user status forganize@*.service` or `journalctl --user -u 'forganize@*' -f`, and stop it with `systemctl --user disable --now forganize@$(systemd-escape -p ~/Downloads).service`.

## 🧪 Try the demo

A [`demo/`](demo) folder with sample files is included so you can see it in action:

```bash
forganize demo
# or, without installing:
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

## 🧰 Development

Tests are written with [pytest](https://pytest.org):

```bash
pip install pytest
pytest tests/
```

## 🛠️ Built with

Bash · Python · Linux

## 📄 License

Released under the [MIT License](LICENSE).
