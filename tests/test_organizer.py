import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import organizer


def test_categorize_known_extension_case_insensitive():
    assert organizer.categorize(".PDF") == "Documents"
    assert organizer.categorize(".jpg") == "Images"


def test_categorize_unknown_extension_falls_back_to_others():
    assert organizer.categorize(".xyz") == "Others"


def test_categorize_uses_custom_categories():
    custom = {"Screenshots": {".png"}}
    assert organizer.categorize(".png", custom) == "Screenshots"
    assert organizer.categorize(".jpg", custom) == "Others"


def test_resolve_conflict_returns_same_path_when_free(tmp_path):
    target = tmp_path / "file.txt"
    assert organizer.resolve_conflict(target) == target


def test_resolve_conflict_appends_counter_on_clash(tmp_path):
    target = tmp_path / "file.txt"
    target.write_text("existing")
    assert organizer.resolve_conflict(target) == tmp_path / "file_1.txt"


def test_organize_sorts_files_into_categories(tmp_path):
    (tmp_path / "resume.pdf").write_text("resume content")
    (tmp_path / "photo.png").write_text("photo content")
    dest = tmp_path / "organized_files"

    moved, failures, duplicates, _ = organizer.organize(tmp_path, dest)

    assert failures == []
    assert duplicates == []
    assert moved == {"Documents": ["resume.pdf"], "Images": ["photo.png"]}
    assert (dest / "Documents" / "resume.pdf").exists()
    assert (dest / "Images" / "photo.png").exists()
    assert not (tmp_path / "resume.pdf").exists()


def test_organize_resolves_name_collisions(tmp_path):
    (tmp_path / "notes.txt").write_text("first")
    dest = tmp_path / "organized_files"
    (dest / "Documents").mkdir(parents=True)
    (dest / "Documents" / "notes.txt").write_text("already here")

    moved, failures, duplicates, _ = organizer.organize(tmp_path, dest)

    assert failures == []
    assert duplicates == []
    assert moved == {"Documents": ["notes.txt"]}
    assert (dest / "Documents" / "notes_1.txt").read_text() == "first"


def test_organize_dry_run_does_not_touch_filesystem(tmp_path):
    (tmp_path / "notes.txt").write_text("x")
    dest = tmp_path / "organized_files"

    moved, failures, duplicates, _ = organizer.organize(tmp_path, dest, dry_run=True)

    assert moved == {"Documents": ["notes.txt"]}
    assert failures == []
    assert duplicates == []
    assert (tmp_path / "notes.txt").exists()
    assert not dest.exists()


def test_organize_copy_mode_keeps_the_original(tmp_path):
    (tmp_path / "video.mp4").write_text("video content")
    dest = tmp_path / "organized_files"

    moved, failures, duplicates, _ = organizer.organize(tmp_path, dest, copy=True)

    assert failures == []
    assert duplicates == []
    assert (tmp_path / "video.mp4").exists()
    assert (dest / "Videos" / "video.mp4").exists()


def test_organize_non_recursive_ignores_nested_files(tmp_path):
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "archive.zip").write_text("x")
    dest = tmp_path / "organized_files"

    moved, failures, duplicates, _ = organizer.organize(tmp_path, dest, recursive=False)

    assert moved == {}
    assert failures == []
    assert duplicates == []
    assert (nested / "archive.zip").exists()


def test_organize_recursive_finds_nested_files(tmp_path):
    nested = tmp_path / "sub"
    nested.mkdir()
    (nested / "archive.zip").write_text("x")
    dest = tmp_path / "organized_files"

    moved, failures, duplicates, _ = organizer.organize(tmp_path, dest, recursive=True)

    assert failures == []
    assert duplicates == []
    assert moved == {"Archives": ["archive.zip"]}
    assert (dest / "Archives" / "archive.zip").exists()


def test_organize_by_date_nests_into_year_month_folders(tmp_path):
    import os
    from datetime import datetime

    target = tmp_path / "resume.pdf"
    target.write_text("resume content")
    mtime = datetime(2024, 3, 15).timestamp()
    os.utime(target, (mtime, mtime))
    dest = tmp_path / "organized_files"

    moved, failures, duplicates, _ = organizer.organize(tmp_path, dest, by_date=True)

    assert failures == []
    assert duplicates == []
    assert moved == {"Documents/2024/03": ["resume.pdf"]}
    assert (dest / "Documents" / "2024" / "03" / "resume.pdf").exists()


def test_organize_second_run_ignores_already_organized_files(tmp_path):
    (tmp_path / "backup.zip").write_text("x")
    dest = tmp_path / "organized_files"

    organizer.organize(tmp_path, dest, recursive=True)
    moved, failures, duplicates, _ = organizer.organize(tmp_path, dest, recursive=True)

    assert moved == {}
    assert failures == []
    assert duplicates == []


def test_organize_flags_duplicate_content_and_leaves_it_in_place(tmp_path):
    (tmp_path / "original.txt").write_text("same content")
    dest = tmp_path / "organized_files"
    organizer.organize(tmp_path, dest)

    (tmp_path / "copy_of_original.txt").write_text("same content")
    moved, failures, duplicates, _ = organizer.organize(tmp_path, dest)

    assert failures == []
    assert moved == {}
    assert duplicates == ["copy_of_original.txt"]
    assert (tmp_path / "copy_of_original.txt").exists()


def test_organize_remove_duplicates_deletes_the_source(tmp_path):
    (tmp_path / "original.txt").write_text("same content")
    dest = tmp_path / "organized_files"
    organizer.organize(tmp_path, dest)

    (tmp_path / "copy_of_original.txt").write_text("same content")
    moved, failures, duplicates, _ = organizer.organize(tmp_path, dest, remove_duplicates=True)

    assert failures == []
    assert duplicates == ["copy_of_original.txt"]
    assert not (tmp_path / "copy_of_original.txt").exists()


def test_organize_no_dedupe_treats_duplicate_content_as_a_normal_file(tmp_path):
    (tmp_path / "original.txt").write_text("same content")
    dest = tmp_path / "organized_files"
    organizer.organize(tmp_path, dest)

    (tmp_path / "copy_of_original.txt").write_text("same content")
    moved, failures, duplicates, _ = organizer.organize(tmp_path, dest, dedupe=False)

    assert failures == []
    assert duplicates == []
    assert moved == {"Documents": ["copy_of_original.txt"]}


def test_load_categories_normalizes_extensions(tmp_path):
    config = tmp_path / "config.json"
    config.write_text(json.dumps({"Screenshots": ["PNG", ".JPG"]}))

    categories = organizer.load_categories(config)

    assert categories == {"Screenshots": {".png", ".jpg"}}


def test_load_categories_invalid_json_raises(tmp_path):
    config = tmp_path / "config.json"
    config.write_text("not valid json")

    try:
        organizer.load_categories(config)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_undo_restores_moved_files(tmp_path):
    (tmp_path / "resume.pdf").write_text("content")
    dest = tmp_path / "organized_files"
    organizer.organize(tmp_path, dest)

    restored, failures = organizer.undo(dest)

    assert restored == 1
    assert failures == []
    assert (tmp_path / "resume.pdf").read_text() == "content"
    assert not dest.exists()


def test_undo_removes_copies_without_touching_originals(tmp_path):
    (tmp_path / "photo.png").write_text("content")
    dest = tmp_path / "organized_files"
    organizer.organize(tmp_path, dest, copy=True)

    restored, failures = organizer.undo(dest)

    assert restored == 1
    assert failures == []
    assert (tmp_path / "photo.png").read_text() == "content"
    assert not (dest / "Images" / "photo.png").exists()


def test_undo_with_no_log_is_a_noop(tmp_path):
    dest = tmp_path / "organized_files"
    restored, failures = organizer.undo(dest)
    assert restored == 0
    assert failures == []


def test_watch_processes_existing_files_then_stops_on_interrupt(tmp_path, monkeypatch):
    (tmp_path / "resume.pdf").write_text("resume content")
    dest = tmp_path / "organized_files"

    def fake_sleep(_):
        raise KeyboardInterrupt

    monkeypatch.setattr(organizer.time, "sleep", fake_sleep)

    organizer.watch(
        tmp_path,
        dest,
        copy=False,
        recursive=False,
        dedupe=True,
        remove_duplicates=False,
        categories=None,
        interval=0.01,
        min_age=0,
    )

    assert (dest / "Documents" / "resume.pdf").exists()


def test_watch_does_not_reprocess_copied_files_across_polls(tmp_path, monkeypatch):
    (tmp_path / "video.mp4").write_text("video content")
    dest = tmp_path / "organized_files"

    calls = {"n": 0}

    def fake_sleep(_):
        calls["n"] += 1
        if calls["n"] >= 2:
            raise KeyboardInterrupt

    monkeypatch.setattr(organizer.time, "sleep", fake_sleep)

    organizer.watch(
        tmp_path,
        dest,
        copy=True,
        recursive=False,
        dedupe=True,
        remove_duplicates=False,
        categories=None,
        interval=0.01,
        min_age=0,
    )

    assert (tmp_path / "video.mp4").exists()
    assert (dest / "Videos" / "video.mp4").exists()
    assert not (dest / "Videos" / "video_1.mp4").exists()
