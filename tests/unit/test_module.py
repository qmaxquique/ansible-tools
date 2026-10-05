import importlib
import os
import sys
from pathlib import Path

import pytest

from plugins.module_utils import xlsx_report as renderer


class ModuleExit(Exception):
    def __init__(self, result):
        self.result = result


class ModuleFailure(ModuleExit):
    pass


class FakeModule:
    def __init__(self, path, check_mode=False, **params):
        self.params = {
            "path": str(path),
            "sheets": [{"name": "Report", "columns": [{"name": "Host"}], "rows": [["server01"]]}],
            "styles": {},
            "properties": {},
            "overwrite": True,
        }
        self.params.update(params)
        self.check_mode = check_mode
        self.moves = 0

    def add_cleanup_file(self, path):
        pass

    def atomic_move(self, source, destination):
        self.moves += 1
        os.replace(source, destination)

    def exit_json(self, **result):
        raise ModuleExit(result)

    def fail_json(self, **result):
        raise ModuleFailure(result)


@pytest.fixture
def entrypoint(monkeypatch):
    monkeypatch.setitem(
        sys.modules,
        "ansible_collections.ansible_tools.reporting.plugins.module_utils.xlsx_report",
        renderer,
    )
    return importlib.import_module("plugins.modules.xlsx_report")


def invoke(entrypoint, monkeypatch, module, failure=False):
    monkeypatch.setattr(entrypoint, "AnsibleModule", lambda **options: module)
    with pytest.raises(ModuleFailure if failure else ModuleExit) as caught:
        entrypoint.run_module()
    return caught.value.result


def test_create_repeat_and_overwrite_guard(entrypoint, monkeypatch, tmp_path):
    path = tmp_path / "report.xlsx"
    module = FakeModule(path)
    created = invoke(entrypoint, monkeypatch, module)
    assert created["changed"] and module.moves == 1
    assert created["sheets"] == ["Report"] and created["row_count"] == 1
    before, modified = path.read_bytes(), path.stat().st_mtime_ns
    module.params["overwrite"] = False
    repeated = invoke(entrypoint, monkeypatch, module)
    assert not repeated["changed"] and module.moves == 1
    assert repeated["checksum"] == created["checksum"]
    assert path.stat().st_mtime_ns == modified
    module.params["sheets"][0]["rows"] = [["server02"]]
    rejected = invoke(entrypoint, monkeypatch, module, failure=True)
    assert "overwrite is false" in rejected["msg"]
    assert path.read_bytes() == before
    module.params["overwrite"] = True
    assert invoke(entrypoint, monkeypatch, module)["changed"]


def test_check_mode_never_creates_or_modifies_files(entrypoint, monkeypatch, tmp_path):
    path = tmp_path / "report.xlsx"
    module = FakeModule(path, check_mode=True)
    assert invoke(entrypoint, monkeypatch, module)["changed"]
    assert list(tmp_path.iterdir()) == [] and module.moves == 0
    module.check_mode = False
    invoke(entrypoint, monkeypatch, module)
    before, modified = path.read_bytes(), path.stat().st_mtime_ns
    module.check_mode = True
    assert not invoke(entrypoint, monkeypatch, module)["changed"]
    module.params["sheets"][0]["rows"] = [["server02"]]
    assert invoke(entrypoint, monkeypatch, module)["changed"]
    assert path.read_bytes() == before and path.stat().st_mtime_ns == modified
    assert list(tmp_path.iterdir()) == [path]


def test_corrupt_output_can_be_repaired(entrypoint, monkeypatch, tmp_path):
    path = tmp_path / "report.xlsx"
    path.write_bytes(b"corrupt")
    assert invoke(entrypoint, monkeypatch, FakeModule(path))["changed"]
    assert renderer.workbook_checksum(path.read_bytes()) is not None


def test_failed_atomic_write_preserves_output_and_removes_temporary_file(
    entrypoint, monkeypatch, tmp_path
):
    path = tmp_path / "report.xlsx"
    path.write_bytes(b"existing data")
    module = FakeModule(path)

    def fail_move(source, destination):
        raise OSError("simulated atomic move failure")

    monkeypatch.setattr(module, "atomic_move", fail_move)
    result = invoke(entrypoint, monkeypatch, module, failure=True)
    assert "simulated atomic move failure" in result["msg"]
    assert path.read_bytes() == b"existing data"
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize("target", ["directory", "symlink", "missing_parent", "blank"])
def test_invalid_paths_do_not_write(entrypoint, monkeypatch, tmp_path, target):
    if target == "directory":
        path = tmp_path
    elif target == "symlink":
        path = tmp_path / "report.xlsx"
        path.symlink_to(tmp_path / "missing.xlsx")
    elif target == "missing_parent":
        path = tmp_path / "missing" / "report.xlsx"
    else:
        path = " "
    module = FakeModule(path)
    assert "msg" in invoke(entrypoint, monkeypatch, module, failure=True)
    assert module.moves == 0


def test_missing_dependency_uses_ansible_failure(entrypoint, monkeypatch, tmp_path):
    monkeypatch.setattr(entrypoint, "HAS_OPENPYXL", False)
    result = invoke(entrypoint, monkeypatch, FakeModule(tmp_path / "report.xlsx"), failure=True)
    assert "openpyxl>=3.1,<4" in result["msg"]
    monkeypatch.setattr(entrypoint, "HAS_OPENPYXL", True)


def test_bad_schema_preserves_existing_output(entrypoint, monkeypatch, tmp_path):
    path = Path(tmp_path / "report.xlsx")
    path.write_bytes(b"existing data")
    module = FakeModule(path, sheets=[])
    result = invoke(entrypoint, monkeypatch, module, failure=True)
    assert "at least one worksheet" in result["msg"]
    assert path.read_bytes() == b"existing data"
