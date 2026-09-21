#!/usr/bin/env python3
import argparse
import json
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
LOG_FILENAME = ".organizer_log.json"
__version__ = "1.0.0"


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


def iter_files(source_dir: Path, dest_dir: Path, recursive: bool):
    if recursive:
        candidates = sorted(p for p in source_dir.rglob("*") if p.is_file())
    else:
        candidates = sorted(p for p in source_dir.iterdir() if p.is_file())

    dest_resolved = dest_dir.resolve()
    for entry in candidates:
        resolved = entry.resolve()
        if resolved == dest_resolved or dest_resolved in resolved.parents:
            continue
        yield entry


def write_log(dest_dir: Path, entries: list) -> None:
    log_path = dest_dir / LOG_FILENAME
    existing = []
    if log_path.exists():
        try:
            existing = json.loads(log_path.read_text())
        except (json.JSONDecodeError, OSError):
            existing = []
    existing.extend(entries)
    log_path.write_text(json.dumps(existing, indent=2))


def organize(source_dir: Path, dest_dir: Path, dry_run: bool = False, copy: bool = False, recursive: bool = False):
    moved = {}
    failures = []
    log_entries = []

    for entry in iter_files(source_dir, dest_dir, recursive):
        category = categorize(entry.suffix)
        moved.setdefault(category, []).append(entry.name)

        if dry_run:
            continue

        try:
            target_folder = dest_dir / category
            target_folder.mkdir(parents=True, exist_ok=True)
            target_path = resolve_conflict(target_folder / entry.name)
            src_resolved = str(entry.resolve())

            if copy:
                shutil.copy2(str(entry), str(target_path))
                log_entries.append({"action": "copy", "src": src_resolved, "dest": str(target_path.resolve())})
            else:
                shutil.move(str(entry), str(target_path))
                log_entries.append({"action": "move", "src": src_resolved, "dest": str(target_path.resolve())})
        except (OSError, shutil.Error) as exc:
            moved[category].remove(entry.name)
            if not moved[category]:
                del moved[category]
            failures.append((entry.name, str(exc)))

    if log_entries:
        write_log(dest_dir, log_entries)

    return moved, failures


def undo(dest_dir: Path):
    log_path = dest_dir / LOG_FILENAME
    if not log_path.exists():
        return 0, []

    try:
        entries = json.loads(log_path.read_text())
    except (json.JSONDecodeError, OSError):
        entries = []

    restored = 0
    failures = []
    for entry in reversed(entries):
        dest = Path(entry["dest"])
        src = Path(entry["src"])
        try:
            if not dest.exists():
                continue
            if entry["action"] == "move":
                src.parent.mkdir(parents=True, exist_ok=True)
                target = resolve_conflict(src) if src.exists() else src
                shutil.move(str(dest), str(target))
            else:  # copy
                dest.unlink()
            restored += 1
        except OSError as exc:
            failures.append((dest.name, str(exc)))

    log_path.unlink(missing_ok=True)

    if dest_dir.exists():
        for child in sorted(dest_dir.iterdir()):
            if child.is_dir():
                try:
                    child.rmdir()
                except OSError:
                    pass
        try:
            dest_dir.rmdir()
        except OSError:
            pass

    return restored, failures


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


def print_failures(failures: list) -> None:
    print(f"\n⚠ {len(failures)} file(s) failed:", file=sys.stderr)
    for name, err in failures:
        print(f"  - {name}: {err}", file=sys.stderr)


def main():
    parser = argparse.ArgumentParser(
        description="Organize files in a directory by type.",
        epilog=(
            "examples:\n"
            "  forganize                       organize the current directory\n"
            "  forganize ~/Downloads           organize a specific directory\n"
            "  forganize ~/Downloads -n        preview only, nothing is moved\n"
            "  forganize ~/Downloads -c        copy instead of move\n"
            "  forganize ~/Downloads -r        also organize subdirectories\n"
            "  forganize ~/Downloads -o ~/Tidy send output to a custom folder\n"
            "  forganize ~/Downloads -u        undo the last organize run\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", nargs="?", default=".", help="directory to organize (default: current directory)")
    parser.add_argument("-o", "--output", default=None, help="destination directory (default: <source>/organized_files)")
    parser.add_argument("-n", "--dry-run", action="store_true", help="show what would happen without moving files")
    parser.add_argument("-c", "--copy", action="store_true", help="copy files instead of moving them")
    parser.add_argument("-r", "--recursive", action="store_true", help="also organize files inside subdirectories")
    parser.add_argument("-u", "--undo", action="store_true", help="undo a previous organize run into the destination directory")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    source_dir = Path(args.source).expanduser().resolve()
    if not source_dir.is_dir():
        print(f"Error: '{source_dir}' is not a valid directory", file=sys.stderr)
        sys.exit(1)

    dest_dir = Path(args.output).expanduser().resolve() if args.output else source_dir / "organized_files"

    if args.undo:
        restored, failures = undo(dest_dir)
        if restored == 0 and not failures:
            print("Nothing to undo.")
        else:
            print(f"✓ Restored {restored} file(s).")
        if failures:
            print_failures(failures)
            sys.exit(1)
        return

    moved, failures = organize(source_dir, dest_dir, dry_run=args.dry_run, copy=args.copy, recursive=args.recursive)

    if not moved and not failures:
        print("No files to organize.")
        return

    total = sum(len(v) for v in moved.values())
    if total:
        verb = "Would organize" if args.dry_run else ("Copied" if args.copy else "Organized")
        print(f"✓ {verb} {total} file(s) successfully!")
        print_tree(dest_dir, moved)

    if failures:
        print_failures(failures)
        sys.exit(1)


if __name__ == "__main__":
    main()
