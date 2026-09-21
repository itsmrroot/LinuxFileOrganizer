#!/usr/bin/env python3
import argparse
import hashlib
import json
import os
import shutil
import sys
import time
from datetime import datetime
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
DEFAULT_CONFIG_PATH = Path(os.environ.get("XDG_CONFIG_HOME", "~/.config")).expanduser() / "forganize" / "config.json"
__version__ = "1.1.0"


def categorize(extension: str, categories: dict = None) -> str:
    categories = FILE_CATEGORIES if categories is None else categories
    extension = extension.lower()
    for category, extensions in categories.items():
        if extension in extensions:
            return category
    return OTHER_CATEGORY


def load_categories(path: Path) -> dict:
    try:
        raw = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"could not read config file '{path}': {exc}") from exc

    categories = {}
    for category, extensions in raw.items():
        normalized = set()
        for ext in extensions:
            ext = ext.lower()
            normalized.add(ext if ext.startswith(".") else f".{ext}")
        categories[category] = normalized
    return categories


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


def hash_file(path: Path, chunk_size: int = 65536) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(chunk_size), b""):
            digest.update(chunk)
    return digest.hexdigest()


def build_hash_index(dest_dir: Path) -> set:
    hashes = set()
    if not dest_dir.exists():
        return hashes
    for path in dest_dir.rglob("*"):
        if path.is_file() and path.name != LOG_FILENAME:
            try:
                hashes.add(hash_file(path))
            except OSError:
                continue
    return hashes


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


def organize(
    source_dir: Path,
    dest_dir: Path,
    dry_run: bool = False,
    copy: bool = False,
    recursive: bool = False,
    dedupe: bool = True,
    remove_duplicates: bool = False,
    categories: dict = None,
    skip_paths: set = None,
    min_age: float = 0,
    by_date: bool = False,
):
    moved = {}
    duplicates = []
    failures = []
    log_entries = []
    processed = set()
    skip_paths = skip_paths or set()
    seen_hashes = build_hash_index(dest_dir) if dedupe else set()

    for entry in iter_files(source_dir, dest_dir, recursive):
        resolved = str(entry.resolve())
        if resolved in skip_paths:
            continue

        if min_age > 0:
            try:
                if time.time() - entry.stat().st_mtime < min_age:
                    continue
            except OSError:
                continue

        file_hash = None
        if dedupe:
            try:
                file_hash = hash_file(entry)
            except OSError:
                file_hash = None
            if file_hash and file_hash in seen_hashes:
                duplicates.append(entry.name)
                processed.add(resolved)
                if remove_duplicates and not copy and not dry_run:
                    try:
                        entry.unlink()
                    except OSError as exc:
                        failures.append((entry.name, str(exc)))
                continue

        category = categorize(entry.suffix, categories)
        category_key = category
        if by_date:
            try:
                mtime = datetime.fromtimestamp(entry.stat().st_mtime)
                category_key = f"{category}/{mtime:%Y}/{mtime:%m}"
            except OSError:
                pass

        moved.setdefault(category_key, []).append(entry.name)
        if file_hash:
            seen_hashes.add(file_hash)

        if dry_run:
            continue

        try:
            target_folder = dest_dir / category_key
            target_folder.mkdir(parents=True, exist_ok=True)
            target_path = resolve_conflict(target_folder / entry.name)

            if copy:
                shutil.copy2(str(entry), str(target_path))
                log_entries.append({"action": "copy", "src": resolved, "dest": str(target_path.resolve())})
            else:
                shutil.move(str(entry), str(target_path))
                log_entries.append({"action": "move", "src": resolved, "dest": str(target_path.resolve())})
            processed.add(resolved)
        except (OSError, shutil.Error) as exc:
            moved[category_key].remove(entry.name)
            if not moved[category_key]:
                del moved[category_key]
            failures.append((entry.name, str(exc)))

    if log_entries:
        write_log(dest_dir, log_entries)

    return moved, failures, duplicates, processed


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


def print_duplicates(duplicates: list, removed: bool) -> None:
    verb = "Removed" if removed else "Skipped"
    print(f"\n🗂 {verb} {len(duplicates)} duplicate file(s) already present in the destination:")
    for name in duplicates:
        print(f"  - {name}")


def report(dest_dir: Path, moved: dict, failures: list, duplicates: list, dry_run: bool, copy: bool, remove_duplicates: bool) -> None:
    total = sum(len(v) for v in moved.values())
    if total:
        verb = "Would organize" if dry_run else ("Copied" if copy else "Organized")
        print(f"✓ {verb} {total} file(s) successfully!")
        print_tree(dest_dir, moved)
    if duplicates:
        print_duplicates(duplicates, removed=remove_duplicates and not copy and not dry_run)
    if failures:
        print_failures(failures)


def watch(
    source_dir: Path,
    dest_dir: Path,
    copy: bool,
    recursive: bool,
    dedupe: bool,
    remove_duplicates: bool,
    categories: dict,
    interval: float,
    min_age: float,
    by_date: bool = False,
) -> None:
    print(f"👀 Watching '{source_dir}' every {interval:g}s — press Ctrl+C to stop.")
    skip_paths = set()
    try:
        while True:
            moved, failures, duplicates, processed = organize(
                source_dir,
                dest_dir,
                dry_run=False,
                copy=copy,
                recursive=recursive,
                dedupe=dedupe,
                remove_duplicates=remove_duplicates,
                categories=categories,
                skip_paths=skip_paths,
                min_age=min_age,
                by_date=by_date,
            )
            skip_paths |= processed
            if moved or failures or duplicates:
                report(dest_dir, moved, failures, duplicates, dry_run=False, copy=copy, remove_duplicates=remove_duplicates)
            time.sleep(interval)
    except KeyboardInterrupt:
        print("\nStopped watching.")


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
            "  forganize ~/Downloads -w        watch and organize new files continuously\n"
            "  forganize ~/Downloads -d        organize into Category/YYYY/MM folders\n"
            "  forganize --print-config        print the active categories as JSON\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("source", nargs="?", default=".", help="directory to organize (default: current directory)")
    parser.add_argument("-o", "--output", default=None, help="destination directory (default: <source>/organized_files)")
    parser.add_argument("-n", "--dry-run", action="store_true", help="show what would happen without moving files")
    parser.add_argument("-c", "--copy", action="store_true", help="copy files instead of moving them")
    parser.add_argument("-r", "--recursive", action="store_true", help="also organize files inside subdirectories")
    parser.add_argument("-u", "--undo", action="store_true", help="undo a previous organize run into the destination directory")
    parser.add_argument("-f", "--config", default=None, help="JSON file defining custom categories (default: ~/.config/forganize/config.json if present)")
    parser.add_argument("--print-config", action="store_true", help="print the active categories as JSON and exit")
    parser.add_argument("--no-dedupe", dest="dedupe", action="store_false", default=True, help="disable duplicate detection (matches by content hash)")
    parser.add_argument("--remove-duplicates", action="store_true", help="delete source files that duplicate a file already organized (move mode only)")
    parser.add_argument("-w", "--watch", action="store_true", help="watch the directory and organize new files as they appear")
    parser.add_argument("-i", "--interval", type=float, default=5.0, help="seconds between scans in watch mode (default: 5)")
    parser.add_argument("-d", "--by-date", action="store_true", help="organize into Category/YYYY/MM folders using each file's modified date")
    parser.add_argument("-v", "--version", action="version", version=f"%(prog)s {__version__}")
    args = parser.parse_args()

    config_path = Path(args.config).expanduser().resolve() if args.config else DEFAULT_CONFIG_PATH
    categories = FILE_CATEGORIES
    if config_path.exists():
        try:
            categories = load_categories(config_path)
        except ValueError as exc:
            print(f"Error: {exc}", file=sys.stderr)
            sys.exit(1)
    elif args.config:
        print(f"Error: config file '{config_path}' not found", file=sys.stderr)
        sys.exit(1)

    if args.print_config:
        print(json.dumps({k: sorted(v) for k, v in categories.items()}, indent=2))
        return

    if args.watch and args.undo:
        print("Error: --watch and --undo cannot be used together", file=sys.stderr)
        sys.exit(1)
    if args.watch and args.dry_run:
        print("Error: --watch and --dry-run cannot be used together", file=sys.stderr)
        sys.exit(1)

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

    if args.watch:
        watch(
            source_dir,
            dest_dir,
            copy=args.copy,
            recursive=args.recursive,
            dedupe=args.dedupe,
            remove_duplicates=args.remove_duplicates,
            categories=categories,
            interval=args.interval,
            min_age=min(2.0, args.interval),
            by_date=args.by_date,
        )
        return

    moved, failures, duplicates, _ = organize(
        source_dir,
        dest_dir,
        dry_run=args.dry_run,
        copy=args.copy,
        recursive=args.recursive,
        dedupe=args.dedupe,
        remove_duplicates=args.remove_duplicates,
        categories=categories,
        by_date=args.by_date,
    )

    if not moved and not failures and not duplicates:
        print("No files to organize.")
        return

    report(dest_dir, moved, failures, duplicates, dry_run=args.dry_run, copy=args.copy, remove_duplicates=args.remove_duplicates)

    if failures:
        sys.exit(1)


if __name__ == "__main__":
    main()
