"""Tests for scripts/migrate_csv_schema.py.

Validates the one-off helper that walks data/<server>/<year>/*.csv and
upgrades each file's header to the current canonical schema for that
server. Idempotent.
"""

import csv
import importlib.util
from pathlib import Path

_SCRIPT = Path(__file__).resolve().parents[1] / "scripts" / "migrate_csv_schema.py"


def _load_script():
    spec = importlib.util.spec_from_file_location("migrate_csv_schema", _SCRIPT)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _write_csv(path: Path, header, rows) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="UTF8") as f:
        w = csv.writer(f)
        w.writerow(header)
        for row in rows:
            w.writerow(row)


def _read_csv(path: Path):
    with open(path, encoding="UTF8") as f:
        return list(csv.reader(f))


def test_migrate_upgrades_biorxiv_narrow_to_current(tmp_path):
    """A 7-col biorxiv file is upgraded to the 8-col current schema."""
    csv_path = tmp_path / "biorxiv" / "2026" / "21.csv"
    old_header = ["Date", "ISOWeek", "DOI", "Version", "Category", "Title", "Authors"]
    row = ["2026-05-21", 21, "10.x/a", "1", "neuro", "T", "Smith"]
    _write_csv(csv_path, old_header, [row])
    mod = _load_script()
    upgraded = mod.main(str(tmp_path))
    rows = _read_csv(csv_path)
    expected_header = [
        "Date",
        "ISOWeek",
        "DOI",
        "Version",
        "Category",
        "Title",
        "Authors",
        "Abstract",
    ]
    assert rows[0] == expected_header
    assert rows[1] == ["2026-05-21", "21", "10.x/a", "1", "neuro", "T", "Smith", ""]
    assert upgraded == 1


def test_migrate_upgrades_arxiv_2026_schema_but_skips_legacy_2024(tmp_path):
    """The 2026 7-col arxiv schema upgrades to 9 cols. The 2024 6-col legacy
    schema (Weekday at col 1) is left alone — its column 1 differs from
    the current header's prefix, so a rewrite would corrupt semantics."""
    cur = tmp_path / "arxiv" / "2026" / "13.csv"
    cur_header = ["Published", "ISOWeek", "Updated", "ID", "Version", "Title", "Categories"]
    cur_row = ["2026-03-23T17:00:00Z", 13, "2026-03-23T17:00:00Z", "2603.00001", "1", "T", "cs.CV"]
    _write_csv(cur, cur_header, [cur_row])
    legacy = tmp_path / "arxiv" / "2024" / "3.csv"
    legacy_header = ["Published", "Weekday", "Updated", "ID", "Version", "Title"]
    legacy_row = ["2024-01-15", "Mon", "2024-01-15", "2401.00001", "1", "T"]
    _write_csv(legacy, legacy_header, [legacy_row])

    mod = _load_script()
    upgraded = mod.main(str(tmp_path))

    cur_rows = _read_csv(cur)
    expected_cur_header = [
        "Published",
        "ISOWeek",
        "Updated",
        "ID",
        "Version",
        "Title",
        "Categories",
        "Authors",
        "Abstract",
    ]
    assert cur_rows[0] == expected_cur_header
    assert cur_rows[1][-2:] == ["", ""]

    legacy_rows = _read_csv(legacy)
    assert legacy_rows[0] == ["Published", "Weekday", "Updated", "ID", "Version", "Title"]
    assert legacy_rows[1] == ["2024-01-15", "Mon", "2024-01-15", "2401.00001", "1", "T"]

    assert upgraded == 1


def test_migrate_is_idempotent(tmp_path):
    """Running the migration twice produces identical bytes on the second
    pass — no double-padding, no header re-edit."""
    csv_path = tmp_path / "biorxiv" / "2026" / "21.csv"
    old_header = ["Date", "ISOWeek", "DOI", "Version", "Category", "Title", "Authors"]
    row = ["2026-05-21", 21, "10.x/a", "1", "neuro", "T", "Smith"]
    _write_csv(csv_path, old_header, [row])
    mod = _load_script()
    mod.main(str(tmp_path))
    snapshot = csv_path.read_bytes()
    upgraded_second = mod.main(str(tmp_path))
    assert csv_path.read_bytes() == snapshot
    assert upgraded_second == 0


def test_migrate_ignores_non_year_dirs_and_unknown_servers(tmp_path):
    """Subdirs that are not numeric year names, and server dirs not in
    the known set, are skipped without error."""
    notes_dir = tmp_path / "biorxiv" / "notes"
    notes_dir.mkdir(parents=True)
    (notes_dir / "stray.csv").write_text("x,y,z\n1,2,3\n", encoding="UTF8")
    unknown_dir = tmp_path / "unknown_server" / "2026"
    unknown_dir.mkdir(parents=True)
    (unknown_dir / "1.csv").write_text("a,b\n1,2\n", encoding="UTF8")
    mod = _load_script()
    upgraded = mod.main(str(tmp_path))
    assert upgraded == 0
