#!/usr/bin/env python3
import argparse
import shutil
import sys
from pathlib import Path

FILE_CATEGORIES = {
    "Documents": {".pdf", ".doc", ".docx", ".txt", ".odt", ".rtf", ".xls", ".xlsx", ".ppt", ".pptx", ".csv", ".md"},
    "Images": {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".svg", ".webp", ".tiff", ".ico"},
    "Videos": {".mp4", ".mkv", ".mov", ".avi", ".wmv", ".flv", ".webm"},
    "Archives": {".zip", ".tar", ".gz", ".rar", ".7z", ".bz2", ".xz"},
    "Music": {".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a"},
}

OTHER_CATEGORY = "Others"


def categorize(extension: str) -> str:
    extension = extension.lower()
    for category, extensions in FILE_CATEGORIES.items():
        if extension in extensions:
            return category
    return OTHER_CATEGORY


def resolve_conflict(path: Path) -> Path:
    if not path.exists():
        return path
    stem, suffix = path.stem, path.suffix
    counter = 1
    candidate = path
    while candidate.exists():
        candidate = path.with_name(f"{stem}_{counter}{suffix}")
        counter += 1
    return candidate


def organize(source_dir: Path, dest_dir: Path, dry_run: bool = False) -> dict:
    moved = {}
    for entry in sorted(source_dir.iterdir()):
        if entry.is_dir():
            continue
        if dest_dir in entry.resolve().parents or entry.resolve() == dest_dir:
            continue

        category = categorize(entry.suffix)
        moved.setdefault(category, []).append(entry.name)

        if dry_run:
            continue

        target_folder = dest_dir / category
        target_folder.mkdir(parents=True, exist_ok=True)
        target_path = resolve_conflict(target_folder / entry.name)
        shutil.move(str(entry), str(target_path))

    return moved


def print_tree(dest_dir: Path, moved: dict) -> None:
    print(f"\n{dest_dir.name}/")
    categories = sorted(moved)
    for ci, category in enumerate(categories):
        cat_connector = "└──" if ci == len(categories) - 1 else "├──"
        print(f"{cat_connector} {category}/")
        files = moved[category]
        prefix = "    " if ci == len(categories) - 1 else "│   "
        for i, name in enumerate(files):
            connector = "└──" if i == len(files) - 1 else "├──"
            print(f"{prefix}{connector} {name}")


def main():
    parser = argparse.ArgumentParser(description="Organize files in a directory by type.")
    parser.add_argument("source", nargs="?", default=".", help="Directory to organize (default: current directory)")
    parser.add_argument("-o", "--output", default=None, help="Destination directory (default: <source>/organized_files)")
    parser.add_argument("--dry-run", action="store_true", help="Show what would happen without moving files")
    args = parser.parse_args()

    source_dir = Path(args.source).expanduser().resolve()
    if not source_dir.is_dir():
        print(f"Error: '{source_dir}' is not a valid directory", file=sys.stderr)
        sys.exit(1)

    dest_dir = Path(args.output).expanduser().resolve() if args.output else source_dir / "organized_files"

    moved = organize(source_dir, dest_dir, dry_run=args.dry_run)

    if not moved:
        print("No files to organize.")
        return

    total = sum(len(v) for v in moved.values())
    verb = "Would organize" if args.dry_run else "Organized"
    print(f"✓ {verb} {total} file(s) successfully!")
    print_tree(dest_dir, moved)


if __name__ == "__main__":
    main()
