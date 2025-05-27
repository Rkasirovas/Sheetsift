import os
from sheetsift.utils import cleanup_temp_files, schedule_file_deletion

def test_cleanup_temp_files(tmp_path):
    f = tmp_path / "testfile.txt"
    f.write_text("test")

    assert f.exists()

    cleanup_temp_files(str(tmp_path))

    assert not f.exists()

def test_schedule_file_deletion(tmp_path):
    f = tmp_path / "testfile.txt"
    f.write_text("test")
    schedule_file_deletion(str(f), delay=1)

    import time
    time.sleep(2)

    assert not f.exists()

def test_cleanup_temp_files_handles_exception(monkeypatch, tmp_path):
    test_file = tmp_path / "testfile.txt"
    test_file.write_text("test")

    def fake_remove(path):
        raise PermissionError("Failas užrakintas")

    monkeypatch.setattr(os, "remove", fake_remove)

    cleanup_temp_files(str(tmp_path))

def test_schedule_file_deletion_handles_exception(monkeypatch, tmp_path):
    test_file = tmp_path / "testfile.txt"
    test_file.write_text("test")

    def fake_remove(path):
        raise PermissionError("Failas užrakintas")

    monkeypatch.setattr(os, "remove", fake_remove)

    schedule_file_deletion(str(test_file), delay=1)

    import time
    time.sleep(2)

    assert test_file.exists()