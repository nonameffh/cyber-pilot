"""
Tests for commands/kit.py — kit install, update, dispatcher, helpers.

Scenario-based tests covering CLI subcommands and core kit logic.
"""

import io
import json
import os
import shutil
import sys
import unittest
from contextlib import redirect_stdout, redirect_stderr
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).parent.parent / "skills" / "cypilot" / "scripts"))


def _make_kit_source(td: Path, slug: str = "testkit") -> Path:
    """Create a minimal kit source directory (direct file package)."""
    kit_src = td / slug
    kit_src.mkdir(parents=True, exist_ok=True)
    # Content dirs
    (kit_src / "artifacts" / "FEATURE").mkdir(parents=True)
    (kit_src / "artifacts" / "FEATURE" / "template.md").write_text(
        "# Feature Spec\n", encoding="utf-8",
    )
    (kit_src / "workflows").mkdir(exist_ok=True)
    # Content files
    (kit_src / "SKILL.md").write_text(
        f"# Kit {slug}\nKit skill instructions.\n", encoding="utf-8",
    )
    (kit_src / "constraints.toml").write_text(
        "[naming]\npattern = '{slug}-*'\n", encoding="utf-8",
    )
    # conf.toml
    from cypilot.utils import toml_utils
    toml_utils.dump({"version": 1}, kit_src / "conf.toml")
    return kit_src


def _bootstrap_project(root: Path, adapter_rel: str = "cypilot") -> Path:
    """Set up a minimal initialized project for kit commands."""
    root.mkdir(parents=True, exist_ok=True)
    (root / ".git").mkdir(exist_ok=True)
    (root / "AGENTS.md").write_text(
        f'<!-- @cpt:root-agents -->\n```toml\ncypilot_path = "{adapter_rel}"\n```\n<!-- /@cpt:root-agents -->\n',
        encoding="utf-8",
    )
    adapter = root / adapter_rel
    config = adapter / "config"
    gen = adapter / ".gen"
    for d in [adapter, config, gen, adapter / ".core"]:
        d.mkdir(parents=True, exist_ok=True)
    (config / "AGENTS.md").write_text("# Test\n", encoding="utf-8")
    from cypilot.utils import toml_utils
    toml_utils.dump({
        "version": "1.0",
        "project_root": "..",
        "kits": {},
    }, config / "core.toml")
    return adapter

class TestCmdKitDispatcher(unittest.TestCase):
    """Kit CLI dispatcher: handles subcommands and errors."""

    def setUp(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(True)

    def tearDown(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(False)

    def test_no_subcommand(self):
        from cypilot.commands.kit import cmd_kit
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_kit([])
        self.assertEqual(rc, 1)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["status"], "ERROR")
        self.assertIn("subcommand", out["message"].lower())

    def test_unknown_subcommand(self):
        from cypilot.commands.kit import cmd_kit
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_kit(["frobnicate"])
        self.assertEqual(rc, 1)
        out = json.loads(buf.getvalue())
        self.assertIn("Unknown", out["message"])


class TestCmdKitUpdate(unittest.TestCase):
    """CLI kit update command scenarios."""

    def setUp(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(True)

    def tearDown(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(False)

    def test_update_source_not_found(self):
        from cypilot.commands.kit import cmd_kit_update
        with TemporaryDirectory() as td:
            buf = io.StringIO()
            with redirect_stdout(buf):
                rc = cmd_kit_update(["--path", str(Path(td) / "nonexistent")])
            self.assertEqual(rc, 2)
            out = json.loads(buf.getvalue())
            self.assertIn("not found", out["message"])

    def test_update_no_project_root(self):
        from cypilot.commands.kit import cmd_kit_update
        with TemporaryDirectory() as td:
            kit_src = _make_kit_source(Path(td), "mykit")
            cwd = os.getcwd()
            try:
                os.chdir(td)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_update(["--path", str(kit_src)])
                self.assertEqual(rc, 1)
            finally:
                os.chdir(cwd)

    def test_update_kit_not_installed_does_first_install(self):
        """update_kit handles first-install if kit is not yet installed."""
        from cypilot.commands.kit import cmd_kit_update
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td), "newkit")
            cwd = os.getcwd()
            try:
                os.chdir(str(root))
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_update(["--path", str(kit_src)])
                self.assertEqual(rc, 0)
                out = json.loads(buf.getvalue())
                self.assertEqual(out["results"][0]["action"], "created")
            finally:
                os.chdir(cwd)

    def test_update_dry_run(self):
        from cypilot.commands.kit import cmd_kit_update, install_kit
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td), "upkit")
            install_kit(kit_src, adapter, "upkit")
            cwd = os.getcwd()
            try:
                os.chdir(str(root))
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_update(["--path", str(kit_src), "--dry-run"])
                self.assertEqual(rc, 0)
                out = json.loads(buf.getvalue())
                self.assertEqual(out["status"], "PASS")
            finally:
                os.chdir(cwd)

    def test_update_auto_approve(self):
        from cypilot.commands.kit import cmd_kit_update, install_kit
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td), "autokit")
            install_kit(kit_src, adapter, "autokit")
            cwd = os.getcwd()
            try:
                os.chdir(str(root))
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_update(["--path", str(kit_src), "--no-interactive", "-y"])
                self.assertEqual(rc, 0)
                out = json.loads(buf.getvalue())
                self.assertEqual(out["status"], "PASS")
            finally:
                os.chdir(cwd)

    def test_update_same_version_skips(self):
        """Same version in source and installed → skip update."""
        from cypilot.commands.kit import cmd_kit_update, install_kit
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td), "vkit")
            install_kit(kit_src, adapter, "vkit")
            cwd = os.getcwd()
            try:
                os.chdir(str(root))
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_update(["--path", str(kit_src)])
                self.assertEqual(rc, 0)
                out = json.loads(buf.getvalue())
                self.assertEqual(out["results"][0]["action"], "current")
            finally:
                os.chdir(cwd)

    def test_update_force_bypasses_version_check(self):
        """--force skips version check even if versions match."""
        from cypilot.commands.kit import cmd_kit_update, install_kit
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td), "fkit")
            install_kit(kit_src, adapter, "fkit")
            cwd = os.getcwd()
            try:
                os.chdir(str(root))
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_update(["--path", str(kit_src), "--force"])
                self.assertEqual(rc, 0)
                out = json.loads(buf.getvalue())
                # With identical files, force still reports "current" (no actual diff)
                self.assertIn(out["results"][0]["action"], ("current", "updated"))
            finally:
                os.chdir(cwd)


class TestKitHelpers(unittest.TestCase):
    def test_read_kit_version_valid(self):
        from cypilot.commands.kit import _read_kit_version
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            p = Path(td) / "conf.toml"
            toml_utils.dump({"version": 2}, p)
            self.assertEqual(_read_kit_version(p), "2")

    def test_read_kit_version_missing(self):
        from cypilot.commands.kit import _read_kit_version
        self.assertEqual(_read_kit_version(Path("/nonexistent/conf.toml")), "")

    def test_read_kit_version_no_key(self):
        from cypilot.commands.kit import _read_kit_version
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            p = Path(td) / "conf.toml"
            toml_utils.dump({"other": "data"}, p)
            self.assertEqual(_read_kit_version(p), "")

    def test_register_kit_in_core_toml(self):
        from cypilot.commands.kit import _register_kit_in_core_toml
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            config_dir = Path(td) / "config"
            config_dir.mkdir()
            toml_utils.dump({"version": "1.0", "kits": {}}, config_dir / "core.toml")
            _register_kit_in_core_toml(config_dir, "mykit", "1", Path(td))
            import tomllib
            with open(config_dir / "core.toml", "rb") as f:
                data = tomllib.load(f)
            self.assertIn("mykit", data["kits"])
            self.assertEqual(data["kits"]["mykit"]["path"], "config/kits/mykit")

    def test_register_kit_no_core_toml(self):
        """No core.toml → does nothing, no error."""
        from cypilot.commands.kit import _register_kit_in_core_toml
        with TemporaryDirectory() as td:
            _register_kit_in_core_toml(Path(td), "nokit", "1", Path(td))

    def test_register_kit_corrupt_core_toml(self):
        """Corrupt core.toml → does nothing, no error."""
        from cypilot.commands.kit import _register_kit_in_core_toml
        with TemporaryDirectory() as td:
            config_dir = Path(td)
            (config_dir / "core.toml").write_text("{{invalid", encoding="utf-8")
            _register_kit_in_core_toml(config_dir, "nokit", "1", Path(td))




class TestCmdKitInstall(unittest.TestCase):
    """Cover cmd_kit_install CLI command."""

    def setUp(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(True)

    def tearDown(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(False)

    def test_install_invalid_source(self):
        from cypilot.commands.kit import cmd_kit_install
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_kit_install(["--path", "/nonexistent/path/to/kit"])
        self.assertEqual(rc, 2)
        out = json.loads(buf.getvalue())
        self.assertEqual(out["status"], "FAIL")

    def test_install_no_project_root(self):
        from cypilot.commands.kit import cmd_kit_install
        with TemporaryDirectory() as td:
            kit_src = _make_kit_source(Path(td), "testkit")
            cwd = os.getcwd()
            try:
                os.chdir(td)
                # Remove .git so no project root is found
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_install(["--path", str(kit_src)])
                self.assertEqual(rc, 1)
            finally:
                os.chdir(cwd)

    def test_install_no_cypilot_dir(self):
        from cypilot.commands.kit import cmd_kit_install
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            root.mkdir()
            (root / ".git").mkdir()
            (root / "AGENTS.md").write_text("# nothing\n", encoding="utf-8")
            kit_src = _make_kit_source(Path(td), "testkit")
            cwd = os.getcwd()
            try:
                os.chdir(str(root))
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_install(["--path", str(kit_src)])
                self.assertEqual(rc, 1)
            finally:
                os.chdir(cwd)

    def test_install_already_exists(self):
        from cypilot.commands.kit import cmd_kit_install
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td), "testkit")
            (adapter / "config" / "kits" / "testkit").mkdir(parents=True)
            cwd = os.getcwd()
            try:
                os.chdir(str(root))
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_install(["--path", str(kit_src)])
                self.assertEqual(rc, 2)
                out = json.loads(buf.getvalue())
                self.assertIn("already installed", out["message"])
            finally:
                os.chdir(cwd)

    def test_install_dry_run(self):
        from cypilot.commands.kit import cmd_kit_install
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td), "testkit")
            cwd = os.getcwd()
            try:
                os.chdir(str(root))
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_install(["--path", str(kit_src), "--dry-run"])
                self.assertEqual(rc, 0)
                out = json.loads(buf.getvalue())
                self.assertEqual(out["status"], "DRY_RUN")
            finally:
                os.chdir(cwd)

    def test_install_success(self):
        from cypilot.commands.kit import cmd_kit_install
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td), "testkit")
            cwd = os.getcwd()
            try:
                os.chdir(str(root))
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_install(["--path", str(kit_src)])
                self.assertEqual(rc, 0)
                out = json.loads(buf.getvalue())
                self.assertEqual(out["status"], "PASS")
                self.assertEqual(out["kit"], "testkit")
            finally:
                os.chdir(cwd)

    def test_install_with_force(self):
        from cypilot.commands.kit import cmd_kit_install
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td), "testkit")
            (adapter / "config" / "kits" / "testkit").mkdir(parents=True)
            cwd = os.getcwd()
            try:
                os.chdir(str(root))
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_install(["--path", str(kit_src), "--force"])
                self.assertEqual(rc, 0)
                out = json.loads(buf.getvalue())
                self.assertEqual(out["status"], "PASS")
            finally:
                os.chdir(cwd)

    def test_install_slug_from_conf_toml(self):
        """Kit slug is read from conf.toml slug field."""
        from cypilot.commands.kit import cmd_kit_install
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td), "rawdir")
            toml_utils.dump({"slug": "custom-slug", "version": 1}, kit_src / "conf.toml")
            cwd = os.getcwd()
            try:
                os.chdir(str(root))
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_install(["--path", str(kit_src)])
                self.assertEqual(rc, 0)
                out = json.loads(buf.getvalue())
                self.assertEqual(out["kit"], "custom-slug")
            finally:
                os.chdir(cwd)


class TestDetectAndMigrateLayout(unittest.TestCase):
    """Cover _detect_and_migrate_layout — legacy layout migration."""

    def test_no_migration_needed(self):
        from cypilot.commands.kit import _detect_and_migrate_layout
        with TemporaryDirectory() as td:
            adapter = Path(td) / "cypilot"
            (adapter / "config" / "kits" / "sdlc").mkdir(parents=True)
            result = _detect_and_migrate_layout(adapter)
            self.assertEqual(result, {})

    def test_dry_run_kits_dir(self):
        from cypilot.commands.kit import _detect_and_migrate_layout
        with TemporaryDirectory() as td:
            adapter = Path(td) / "cypilot"
            kits_dir = adapter / "kits" / "sdlc"
            kits_dir.mkdir(parents=True)
            (kits_dir / "conf.toml").write_text("version = 1\n", encoding="utf-8")
            result = _detect_and_migrate_layout(adapter, dry_run=True)
            self.assertIn("sdlc", result)
            self.assertEqual(result["sdlc"], "would_migrate")
            # Verify kits/ dir still exists (dry run)
            self.assertTrue(kits_dir.is_dir())

    def test_migrate_kits_dir(self):
        from cypilot.commands.kit import _detect_and_migrate_layout
        with TemporaryDirectory() as td:
            adapter = Path(td) / "cypilot"
            kits_dir = adapter / "kits" / "sdlc"
            kits_dir.mkdir(parents=True)
            (kits_dir / "conf.toml").write_text("version = 1\n", encoding="utf-8")
            (kits_dir / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
            # Legacy artifacts to skip
            bp_dir = kits_dir / "blueprints"
            bp_dir.mkdir()
            (bp_dir / "DESIGN.md").write_text("blueprint\n", encoding="utf-8")
            result = _detect_and_migrate_layout(adapter)
            self.assertEqual(result["sdlc"], "migrated")
            config_kit = adapter / "config" / "kits" / "sdlc"
            self.assertTrue((config_kit / "conf.toml").is_file())
            self.assertTrue((config_kit / "SKILL.md").is_file())
            # Blueprints should NOT be copied
            self.assertFalse((config_kit / "blueprints").exists())
            # Old kits/ dir should be removed
            self.assertFalse((adapter / "kits").is_dir())

    def test_migrate_gen_kits_dir(self):
        from cypilot.commands.kit import _detect_and_migrate_layout
        with TemporaryDirectory() as td:
            adapter = Path(td) / "cypilot"
            gen_kit = adapter / ".gen" / "kits" / "sdlc"
            gen_kit.mkdir(parents=True)
            (gen_kit / "SKILL.md").write_text("# Gen Skill\n", encoding="utf-8")
            result = _detect_and_migrate_layout(adapter)
            self.assertIn("sdlc", result)
            config_kit = adapter / "config" / "kits" / "sdlc"
            self.assertTrue((config_kit / "SKILL.md").is_file())
            # .gen/kits/ should be removed
            self.assertFalse((adapter / ".gen" / "kits").is_dir())

    def test_migrate_updates_core_toml_paths(self):
        from cypilot.commands.kit import _detect_and_migrate_layout
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            adapter = Path(td) / "cypilot"
            kits_dir = adapter / "kits" / "sdlc"
            kits_dir.mkdir(parents=True)
            (kits_dir / "conf.toml").write_text("version = 1\n", encoding="utf-8")
            config_dir = adapter / "config"
            config_dir.mkdir(parents=True)
            toml_utils.dump({
                "kits": {"sdlc": {"path": "kits/sdlc", "format": "Cypilot"}},
            }, config_dir / "core.toml")
            _detect_and_migrate_layout(adapter)
            import tomllib
            with open(config_dir / "core.toml", "rb") as f:
                data = tomllib.load(f)
            self.assertEqual(data["kits"]["sdlc"]["path"], "config/kits/sdlc")

    def test_migrate_with_subdir(self):
        """Migration copies subdirectories from kits/{slug}/."""
        from cypilot.commands.kit import _detect_and_migrate_layout
        with TemporaryDirectory() as td:
            adapter = Path(td) / "cypilot"
            kits_dir = adapter / "kits" / "sdlc"
            (kits_dir / "artifacts" / "DESIGN").mkdir(parents=True)
            (kits_dir / "artifacts" / "DESIGN" / "template.md").write_text("# T\n", encoding="utf-8")
            (kits_dir / "conf.toml").write_text("version = 1\n", encoding="utf-8")
            _detect_and_migrate_layout(adapter)
            config_kit = adapter / "config" / "kits" / "sdlc"
            self.assertTrue((config_kit / "artifacts" / "DESIGN" / "template.md").is_file())

    def test_dry_run_gen_kits(self):
        from cypilot.commands.kit import _detect_and_migrate_layout
        with TemporaryDirectory() as td:
            adapter = Path(td) / "cypilot"
            gen_kit = adapter / ".gen" / "kits" / "sdlc"
            gen_kit.mkdir(parents=True)
            (gen_kit / "SKILL.md").write_text("# S\n", encoding="utf-8")
            result = _detect_and_migrate_layout(adapter, dry_run=True)
            self.assertEqual(result["sdlc"], "would_migrate")
            # .gen/kits/ should still exist (dry run)
            self.assertTrue(gen_kit.is_dir())


class TestCmdKitMigrateDeprecated(unittest.TestCase):
    """cmd_kit_migrate redirects to cmd_kit_update."""

    def setUp(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(True)

    def tearDown(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(False)

    def test_migrate_warns_and_returns_error(self):
        from cypilot.commands.kit import cmd_kit_migrate
        err = io.StringIO()
        with redirect_stderr(err):
            rc = cmd_kit_migrate([])
        self.assertEqual(rc, 1)
        self.assertIn("deprecated", err.getvalue().lower())
        self.assertIn("kit update", err.getvalue())


class TestCmdKitDispatcherRoutes(unittest.TestCase):
    """Cover cmd_kit routing to install, update, migrate subcommands."""

    def setUp(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(True)

    def tearDown(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(False)

    def test_route_install(self):
        from cypilot.commands.kit import cmd_kit
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_kit(["install", "--path", "/nonexistent"])
        self.assertEqual(rc, 2)

    def test_route_update(self):
        from cypilot.commands.kit import cmd_kit
        buf = io.StringIO()
        with redirect_stdout(buf):
            rc = cmd_kit(["update", "--path", "/nonexistent"])
        self.assertEqual(rc, 2)

    def test_route_migrate(self):
        from cypilot.commands.kit import cmd_kit
        with TemporaryDirectory() as td:
            cwd = os.getcwd()
            try:
                os.chdir(td)
                err = io.StringIO()
                buf = io.StringIO()
                with redirect_stderr(err), redirect_stdout(buf):
                    rc = cmd_kit(["migrate"])
                self.assertIn("deprecated", err.getvalue().lower())
            finally:
                os.chdir(cwd)


class TestUpdateKitExistingBranch(unittest.TestCase):
    """Cover update_kit when kit already exists (file-level diff path)."""

    def setUp(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(True)

    def tearDown(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(False)

    def test_update_existing_kit_auto_approve(self):
        from cypilot.commands.kit import update_kit, install_kit
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td), "ukit")
            install_kit(kit_src, adapter, "ukit")
            # Modify source to create a diff
            (kit_src / "SKILL.md").write_text("# Updated Skill\n", encoding="utf-8")
            result = update_kit("ukit", kit_src, adapter, auto_approve=True)
            self.assertEqual(result["kit"], "ukit")
            self.assertIn(result["version"]["status"], ("updated", "current"))

    def test_update_existing_kit_non_interactive(self):
        from cypilot.commands.kit import update_kit, install_kit
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td), "ukit2")
            install_kit(kit_src, adapter, "ukit2")
            (kit_src / "SKILL.md").write_text("# Changed\n", encoding="utf-8")
            result = update_kit("ukit2", kit_src, adapter, interactive=False)
            # Non-interactive declines changes
            self.assertIn(result["version"]["status"], ("partial", "current"))

    def test_update_kit_dry_run(self):
        from cypilot.commands.kit import update_kit
        with TemporaryDirectory() as td:
            adapter = Path(td) / "cypilot"
            adapter.mkdir()
            result = update_kit("test", Path(td), adapter, dry_run=True)
            self.assertEqual(result["version"]["status"], "dry_run")

    def test_update_existing_with_declined(self):
        from cypilot.commands.kit import update_kit, install_kit
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td), "dkit")
            install_kit(kit_src, adapter, "dkit")
            # Modify source
            (kit_src / "constraints.toml").write_text("[changed]\nx = 1\n", encoding="utf-8")
            result = update_kit("dkit", kit_src, adapter, interactive=False)
            if result.get("gen_rejected"):
                self.assertIsInstance(result["gen_rejected"], list)

    def test_update_kit_not_installed_coverage(self):
        """cmd_kit_update with valid source but kit not installed."""
        from cypilot.commands.kit import cmd_kit_update
        from cypilot.utils.ui import set_json_mode
        set_json_mode(True)
        try:
            with TemporaryDirectory() as td:
                root = Path(td) / "proj"
                _bootstrap_project(root)
                kit_src = _make_kit_source(Path(td), "notinstalled")
                cwd = os.getcwd()
                try:
                    os.chdir(str(root))
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        rc = cmd_kit_update(["--path", str(kit_src)])
                    self.assertEqual(rc, 0)
                    out = json.loads(buf.getvalue())
                    self.assertEqual(out["results"][0]["action"], "created")
                finally:
                    os.chdir(cwd)
        finally:
            set_json_mode(False)


class TestHumanKitInstall(unittest.TestCase):
    """Cover _human_kit_install display function (runs with JSON mode OFF)."""

    def setUp(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(False)

    def test_pass(self):
        from cypilot.commands.kit import _human_kit_install
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_kit_install({"status": "PASS", "kit": "sdlc", "version": "1", "action": "installed", "files_written": 5})
        self.assertIn("sdlc", buf.getvalue())

    def test_dry_run(self):
        from cypilot.commands.kit import _human_kit_install
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_kit_install({"status": "DRY_RUN", "kit": "sdlc", "version": "1", "source": "/a", "target": "/b"})
        self.assertIn("Dry run", buf.getvalue())

    def test_fail(self):
        from cypilot.commands.kit import _human_kit_install
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_kit_install({"status": "FAIL", "kit": "sdlc", "message": "not found", "hint": "check path"})
        self.assertIn("not found", buf.getvalue())

    def test_with_errors(self):
        from cypilot.commands.kit import _human_kit_install
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_kit_install({"status": "WARN", "kit": "sdlc", "version": "1", "errors": ["err1"]})
        self.assertIn("err1", buf.getvalue())


class TestHumanKitUpdate(unittest.TestCase):
    """Cover _human_kit_update display function."""

    def setUp(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(False)

    def test_pass_with_results(self):
        from cypilot.commands.kit import _human_kit_update
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_kit_update({
                "status": "PASS",
                "kits_updated": 1,
                "results": [
                    {"kit": "sdlc", "action": "updated", "accepted": ["a.md", "b.md"], "declined": ["c.md"], "unchanged": 5},
                ],
            })
        out = buf.getvalue()
        self.assertIn("sdlc", out)
        self.assertIn("2 accepted", out)
        self.assertIn("1 declined", out)
        self.assertIn("5 unchanged", out)
        self.assertIn("complete", out)

    def test_warn_with_errors(self):
        from cypilot.commands.kit import _human_kit_update
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_kit_update({
                "status": "WARN",
                "kits_updated": 1,
                "results": [{"kit": "sdlc", "action": "current"}],
                "errors": ["oops", "fail"],
            })
        out = buf.getvalue()
        self.assertIn("oops", out)
        self.assertIn("fail", out)
        self.assertIn("warnings", out.lower())

    def test_unknown_status(self):
        from cypilot.commands.kit import _human_kit_update
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_kit_update({"status": "CUSTOM", "results": []})
        self.assertIn("CUSTOM", buf.getvalue())

    def test_no_results(self):
        from cypilot.commands.kit import _human_kit_update
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_kit_update({"status": "PASS", "kits_updated": 0, "results": []})
        self.assertIn("0", buf.getvalue())


class TestSeedKitConfigFiles(unittest.TestCase):
    """Cover _seed_kit_config_files."""

    def test_seeds_missing_files(self):
        from cypilot.commands.kit import _seed_kit_config_files
        with TemporaryDirectory() as td:
            scripts_dir = Path(td) / "scripts"
            scripts_dir.mkdir()
            (scripts_dir / "run.sh").write_text("#!/bin/sh\n", encoding="utf-8")
            config_dir = Path(td) / "config"
            config_dir.mkdir()
            actions = {}
            _seed_kit_config_files(scripts_dir, config_dir, actions)
            # Function should copy scripts content to config if missing


class TestReadConfVersion(unittest.TestCase):
    """Cover _read_conf_version edge cases."""

    def test_valid(self):
        from cypilot.commands.kit import _read_conf_version
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            p = Path(td) / "conf.toml"
            toml_utils.dump({"version": 3}, p)
            self.assertEqual(_read_conf_version(p), 3)

    def test_missing_file(self):
        from cypilot.commands.kit import _read_conf_version
        self.assertEqual(_read_conf_version(Path("/nonexistent/conf.toml")), 0)

    def test_no_version_key(self):
        from cypilot.commands.kit import _read_conf_version
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            p = Path(td) / "conf.toml"
            toml_utils.dump({"slug": "sdlc"}, p)
            self.assertEqual(_read_conf_version(p), 0)

    def test_corrupt(self):
        from cypilot.commands.kit import _read_conf_version
        with TemporaryDirectory() as td:
            p = Path(td) / "conf.toml"
            p.write_text("{{invalid", encoding="utf-8")
            self.assertEqual(_read_conf_version(p), 0)


# ---------------------------------------------------------------------------
# GitHub source parsing
# ---------------------------------------------------------------------------

class TestParseGithubSource(unittest.TestCase):
    def test_basic(self):
        from cypilot.commands.kit import _parse_github_source
        o, r, v = _parse_github_source("owner/repo")
        self.assertEqual((o, r, v), ("owner", "repo", ""))

    def test_with_version(self):
        from cypilot.commands.kit import _parse_github_source
        o, r, v = _parse_github_source("owner/repo@v1.2.3")
        self.assertEqual((o, r, v), ("owner", "repo", "v1.2.3"))

    def test_invalid(self):
        from cypilot.commands.kit import _parse_github_source
        with self.assertRaises(ValueError):
            _parse_github_source("invalid-no-slash")


# ---------------------------------------------------------------------------
# GitHub download (mocked)
# ---------------------------------------------------------------------------

class TestDownloadKitFromGithub(unittest.TestCase):
    def test_success(self):
        """Mocked download: creates tarball, extracts to temp dir."""
        import tarfile, tempfile
        from cypilot.commands.kit import _download_kit_from_github

        # Build a real tarball in memory
        tar_bytes = io.BytesIO()
        with tarfile.open(fileobj=tar_bytes, mode="w:gz") as tar:
            # GitHub tarballs have one top-level dir
            info = tarfile.TarInfo(name="owner-repo-abc123/")
            info.type = tarfile.DIRTYPE
            tar.addfile(info)
            data = b"version = 1\n"
            info2 = tarfile.TarInfo(name="owner-repo-abc123/conf.toml")
            info2.size = len(data)
            tar.addfile(info2, io.BytesIO(data))
        tar_bytes.seek(0)

        class FakeResp:
            def read(self, n=-1):
                return tar_bytes.read(n)
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        with patch("cypilot.commands.kit.urllib.request.urlopen", return_value=FakeResp()):
            result_dir, ver = _download_kit_from_github("owner", "repo", "v1.0")
            self.assertTrue(result_dir.is_dir())
            self.assertEqual(ver, "v1.0")
            # Cleanup
            shutil.rmtree(result_dir.parent, ignore_errors=True)

    def test_network_error(self):
        from cypilot.commands.kit import _download_kit_from_github
        with patch("cypilot.commands.kit.urllib.request.urlopen", side_effect=Exception("timeout")):
            with self.assertRaises(RuntimeError):
                _download_kit_from_github("owner", "repo", "v1")

    def test_bad_archive(self):
        """Download succeeds but tarball is corrupt."""
        from cypilot.commands.kit import _download_kit_from_github

        class FakeResp:
            def __init__(self):
                self._data = io.BytesIO(b"not a tarball")
            def read(self, n=-1):
                return self._data.read(n)
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        with patch("cypilot.commands.kit.urllib.request.urlopen", return_value=FakeResp()):
            with self.assertRaises(RuntimeError):
                _download_kit_from_github("owner", "repo", "v1")


class TestGithubHeaders(unittest.TestCase):
    def test_no_token(self):
        from cypilot.commands.kit import _github_headers
        with patch.dict("os.environ", {}, clear=True):
            h = _github_headers()
            self.assertEqual(h["User-Agent"], "cypilot-kit-installer")
            self.assertNotIn("Authorization", h)

    def test_with_token(self):
        from cypilot.commands.kit import _github_headers
        with patch.dict("os.environ", {"GITHUB_TOKEN": "ghp_test123"}):
            h = _github_headers()
            self.assertEqual(h["Authorization"], "Bearer ghp_test123")


class TestResolveLatestRelease(unittest.TestCase):
    def test_success(self):
        from cypilot.commands.kit import _resolve_latest_github_release

        class FakeResp:
            def read(self):
                return json.dumps({"tag_name": "v2.0"}).encode()
            def __enter__(self):
                return self
            def __exit__(self, *a):
                pass

        with patch("cypilot.commands.kit.urllib.request.urlopen", return_value=FakeResp()):
            tag = _resolve_latest_github_release("o", "r")
            self.assertEqual(tag, "v2.0")

    def test_no_releases_404(self):
        import urllib.error
        from cypilot.commands.kit import _resolve_latest_github_release

        exc = urllib.error.HTTPError("url", 404, "Not Found", {}, None)
        with patch("cypilot.commands.kit.urllib.request.urlopen", side_effect=exc):
            tag = _resolve_latest_github_release("o", "r")
            self.assertEqual(tag, "")

    def test_api_error_raises(self):
        import urllib.error
        from cypilot.commands.kit import _resolve_latest_github_release

        exc = urllib.error.HTTPError("url", 403, "rate limit", {}, None)
        with patch("cypilot.commands.kit.urllib.request.urlopen", side_effect=exc):
            with self.assertRaises(RuntimeError):
                _resolve_latest_github_release("o", "r")

    def test_network_error_raises(self):
        from cypilot.commands.kit import _resolve_latest_github_release
        with patch("cypilot.commands.kit.urllib.request.urlopen", side_effect=OSError("dns")):
            with self.assertRaises(RuntimeError):
                _resolve_latest_github_release("o", "r")


# ---------------------------------------------------------------------------
# Layout migration
# ---------------------------------------------------------------------------

class TestDetectAndMigrateLayout(unittest.TestCase):
    def test_no_legacy_dirs(self):
        from cypilot.commands.kit import _detect_and_migrate_layout
        with TemporaryDirectory() as td:
            cypilot = Path(td) / "cypilot"
            cypilot.mkdir()
            result = _detect_and_migrate_layout(cypilot)
            self.assertEqual(result, {})

    def test_migrate_kits_dir(self):
        """kits/{slug}/ content migrates to config/kits/{slug}/."""
        from cypilot.commands.kit import _detect_and_migrate_layout
        with TemporaryDirectory() as td:
            cypilot = Path(td) / "cypilot"
            # Create old layout: kits/sdlc/ with content
            kits_dir = cypilot / "kits" / "sdlc"
            kits_dir.mkdir(parents=True)
            (kits_dir / "conf.toml").write_text("version = 1\n", encoding="utf-8")
            (kits_dir / "artifacts").mkdir()
            (kits_dir / "artifacts" / "PRD.md").write_text("# PRD\n", encoding="utf-8")
            # blueprints should be skipped
            (kits_dir / "blueprints").mkdir()
            (kits_dir / "blueprints" / "old.md").write_text("old", encoding="utf-8")

            result = _detect_and_migrate_layout(cypilot)

            self.assertEqual(result.get("sdlc"), "migrated")
            config_kit = cypilot / "config" / "kits" / "sdlc"
            self.assertTrue((config_kit / "conf.toml").is_file())
            self.assertTrue((config_kit / "artifacts" / "PRD.md").is_file())
            # blueprints should NOT be copied
            self.assertFalse((config_kit / "blueprints").exists())
            # Old kits/ dir should be removed
            self.assertFalse((cypilot / "kits").exists())

    def test_migrate_gen_kits(self):
        """.gen/kits/{slug}/ content migrates to config/kits/{slug}/."""
        from cypilot.commands.kit import _detect_and_migrate_layout
        with TemporaryDirectory() as td:
            cypilot = Path(td) / "cypilot"
            gen_kit = cypilot / ".gen" / "kits" / "sdlc"
            gen_kit.mkdir(parents=True)
            (gen_kit / "SKILL.md").write_text("# Skill\n", encoding="utf-8")

            result = _detect_and_migrate_layout(cypilot)

            self.assertIn("sdlc", result)
            config_kit = cypilot / "config" / "kits" / "sdlc"
            self.assertTrue((config_kit / "SKILL.md").is_file())
            # .gen/kits/ should be removed
            self.assertFalse((cypilot / ".gen" / "kits").exists())

    def test_dry_run(self):
        from cypilot.commands.kit import _detect_and_migrate_layout
        with TemporaryDirectory() as td:
            cypilot = Path(td) / "cypilot"
            kits_dir = cypilot / "kits" / "sdlc"
            kits_dir.mkdir(parents=True)
            (kits_dir / "conf.toml").write_text("v=1\n", encoding="utf-8")

            result = _detect_and_migrate_layout(cypilot, dry_run=True)
            self.assertEqual(result.get("sdlc"), "would_migrate")
            # Files should NOT be moved
            self.assertTrue(kits_dir.exists())

    def test_updates_core_toml_paths(self):
        from cypilot.commands.kit import _detect_and_migrate_layout
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            cypilot = Path(td) / "cypilot"
            kits_dir = cypilot / "kits" / "sdlc"
            kits_dir.mkdir(parents=True)
            (kits_dir / "conf.toml").write_text("v=1\n", encoding="utf-8")
            config_dir = cypilot / "config"
            config_dir.mkdir(parents=True, exist_ok=True)
            toml_utils.dump({
                "kits": {"sdlc": {"path": "kits/sdlc", "format": "Cypilot"}},
            }, config_dir / "core.toml")

            _detect_and_migrate_layout(cypilot)

            import tomllib
            with open(config_dir / "core.toml", "rb") as f:
                data = tomllib.load(f)
            self.assertEqual(data["kits"]["sdlc"]["path"], "config/kits/sdlc")

    def test_overwrite_existing_dir(self):
        """When config/kits/{slug}/artifacts/ already exists, it gets overwritten."""
        from cypilot.commands.kit import _detect_and_migrate_layout
        with TemporaryDirectory() as td:
            cypilot = Path(td) / "cypilot"
            # Old layout
            kits_dir = cypilot / "kits" / "sdlc"
            (kits_dir / "artifacts").mkdir(parents=True)
            (kits_dir / "artifacts" / "new.md").write_text("new", encoding="utf-8")
            # Existing config
            config_art = cypilot / "config" / "kits" / "sdlc" / "artifacts"
            config_art.mkdir(parents=True)
            (config_art / "old.md").write_text("old", encoding="utf-8")

            _detect_and_migrate_layout(cypilot)
            # artifacts dir should have the NEW content
            self.assertTrue((config_art / "new.md").is_file())


# ---------------------------------------------------------------------------
# install_kit validation
# ---------------------------------------------------------------------------

class TestInstallKitValidation(unittest.TestCase):
    def test_nonexistent_source(self):
        from cypilot.commands.kit import install_kit
        result = install_kit(Path("/no/such/dir"), Path("/tmp"), "x")
        self.assertEqual(result["status"], "FAIL")


# ---------------------------------------------------------------------------
# _copy_kit_content overwrite path
# ---------------------------------------------------------------------------

class TestCopyKitContentOverwrite(unittest.TestCase):
    def test_existing_dir_overwritten(self):
        from cypilot.commands.kit import _copy_kit_content
        with TemporaryDirectory() as td:
            src = Path(td) / "src"
            dst = Path(td) / "dst"
            (src / "artifacts" / "PRD").mkdir(parents=True)
            (src / "artifacts" / "PRD" / "new.md").write_text("new", encoding="utf-8")
            # Existing target with different content
            (dst / "artifacts" / "PRD").mkdir(parents=True)
            (dst / "artifacts" / "PRD" / "old.md").write_text("old", encoding="utf-8")

            actions = _copy_kit_content(src, dst)
            self.assertEqual(actions.get("artifacts"), "copied")
            # new.md should exist, old.md should NOT (dir was replaced)
            self.assertTrue((dst / "artifacts" / "PRD" / "new.md").is_file())
            self.assertFalse((dst / "artifacts" / "PRD" / "old.md").exists())


# ---------------------------------------------------------------------------
# _collect_kit_metadata OSError
# ---------------------------------------------------------------------------

class TestCollectKitMetadataOsError(unittest.TestCase):
    def test_agents_read_oserror(self):
        from cypilot.commands.kit import _collect_kit_metadata
        with TemporaryDirectory() as td:
            kit_dir = Path(td) / "sdlc"
            kit_dir.mkdir()
            agents = kit_dir / "AGENTS.md"
            agents.mkdir()  # directory, not file — read will fail
            meta = _collect_kit_metadata(kit_dir, "sdlc")
            self.assertEqual(meta["agents_content"], "")


# ---------------------------------------------------------------------------
# _read_project_name_from_registry
# ---------------------------------------------------------------------------

class TestReadProjectNameFromRegistry(unittest.TestCase):
    def test_missing_file(self):
        from cypilot.commands.kit import _read_project_name_from_registry
        self.assertIsNone(_read_project_name_from_registry(Path("/nonexistent")))

    def test_corrupt_toml(self):
        from cypilot.commands.kit import _read_project_name_from_registry
        with TemporaryDirectory() as td:
            p = Path(td) / "artifacts.toml"
            p.write_text("{{bad", encoding="utf-8")
            self.assertIsNone(_read_project_name_from_registry(Path(td)))

    def test_empty_name(self):
        from cypilot.commands.kit import _read_project_name_from_registry
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            toml_utils.dump({"systems": [{"name": "  "}]}, Path(td) / "artifacts.toml")
            self.assertIsNone(_read_project_name_from_registry(Path(td)))

    def test_reads_first_system_name(self):
        from cypilot.commands.kit import _read_project_name_from_registry
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            toml_utils.dump(
                {"systems": [{"name": "MyProject", "slug": "myproject", "kit": "sdlc"}]},
                Path(td) / "artifacts.toml",
            )
            self.assertEqual(_read_project_name_from_registry(Path(td)), "MyProject")


# ---------------------------------------------------------------------------
# _read_kits_from_core_toml edge cases
# ---------------------------------------------------------------------------

class TestReadKitsFromCoreToml(unittest.TestCase):
    def test_missing_file(self):
        from cypilot.commands.kit import _read_kits_from_core_toml
        self.assertEqual(_read_kits_from_core_toml(Path("/nonexistent")), {})

    def test_corrupt(self):
        from cypilot.commands.kit import _read_kits_from_core_toml
        with TemporaryDirectory() as td:
            (Path(td) / "core.toml").write_text("{{bad", encoding="utf-8")
            self.assertEqual(_read_kits_from_core_toml(Path(td)), {})

    def test_non_dict_kits(self):
        from cypilot.commands.kit import _read_kits_from_core_toml
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            toml_utils.dump({"kits": "not_a_dict"}, Path(td) / "core.toml")
            self.assertEqual(_read_kits_from_core_toml(Path(td)), {})

    def test_filters_non_dict_entries(self):
        from cypilot.commands.kit import _read_kits_from_core_toml
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            toml_utils.dump({
                "kits": {"good": {"path": "x"}, "bad": "string_val"},
            }, Path(td) / "core.toml")
            result = _read_kits_from_core_toml(Path(td))
            self.assertIn("good", result)
            self.assertNotIn("bad", result)


# ---------------------------------------------------------------------------
# _register_kit_in_core_toml
# ---------------------------------------------------------------------------

class TestRegisterKitInCoreToml(unittest.TestCase):
    def test_new_kit(self):
        from cypilot.commands.kit import _register_kit_in_core_toml
        from cypilot.utils import toml_utils
        import tomllib
        with TemporaryDirectory() as td:
            config = Path(td)
            toml_utils.dump({"kits": {}}, config / "core.toml")
            _register_kit_in_core_toml(config, "mykit", "1.0", Path(td) / "cyp")
            with open(config / "core.toml", "rb") as f:
                data = tomllib.load(f)
            self.assertEqual(data["kits"]["mykit"]["version"], "1.0")
            self.assertEqual(data["kits"]["mykit"]["format"], "Cypilot")
            self.assertEqual(data["kits"]["mykit"]["path"], "config/kits/mykit")

    def test_with_source(self):
        from cypilot.commands.kit import _register_kit_in_core_toml
        from cypilot.utils import toml_utils
        import tomllib
        with TemporaryDirectory() as td:
            config = Path(td)
            toml_utils.dump({"kits": {}}, config / "core.toml")
            _register_kit_in_core_toml(config, "mykit", "2.0", Path(td), source="github:o/r")
            with open(config / "core.toml", "rb") as f:
                data = tomllib.load(f)
            self.assertEqual(data["kits"]["mykit"]["source"], "github:o/r")

    def test_missing_core_toml(self):
        from cypilot.commands.kit import _register_kit_in_core_toml
        # Should not raise
        _register_kit_in_core_toml(Path("/nonexistent"), "k", "1", Path("/x"))


# ---------------------------------------------------------------------------
# _read_kit_version_from_core
# ---------------------------------------------------------------------------

class TestReadKitVersionFromCore(unittest.TestCase):
    def test_missing(self):
        from cypilot.commands.kit import _read_kit_version_from_core
        self.assertEqual(_read_kit_version_from_core(Path("/nonexistent"), "x"), "")

    def test_found(self):
        from cypilot.commands.kit import _read_kit_version_from_core
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            toml_utils.dump({"kits": {"sdlc": {"version": "3"}}}, Path(td) / "core.toml")
            self.assertEqual(_read_kit_version_from_core(Path(td), "sdlc"), "3")


# ---------------------------------------------------------------------------
# cmd_kit_install CLI GitHub path (mocked)
# ---------------------------------------------------------------------------

class TestCmdKitInstallGithubPath(unittest.TestCase):
    def setUp(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(True)

    def tearDown(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(False)

    def test_install_from_github_mocked(self):
        from cypilot.commands.kit import cmd_kit_install
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td) / "dl", "sdlc")

            cwd = os.getcwd()
            try:
                os.chdir(root)
                with patch(
                    "cypilot.commands.kit._download_kit_from_github",
                    return_value=(kit_src, "1.0"),
                ):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        rc = cmd_kit_install(["cyberfabric/cyber-pilot-kit-sdlc"])
                self.assertEqual(rc, 0)
                out = json.loads(buf.getvalue())
                self.assertIn(out["status"], ["PASS", "OK"])
            finally:
                os.chdir(cwd)

    def test_invalid_source_format(self):
        from cypilot.commands.kit import cmd_kit_install
        buf = io.StringIO()
        with redirect_stdout(buf), redirect_stderr(io.StringIO()):
            rc = cmd_kit_install(["bad-no-slash"])
        self.assertEqual(rc, 2)

    def test_download_failure(self):
        from cypilot.commands.kit import cmd_kit_install
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            _bootstrap_project(root)
            cwd = os.getcwd()
            try:
                os.chdir(root)
                with patch(
                    "cypilot.commands.kit._download_kit_from_github",
                    side_effect=RuntimeError("rate limit"),
                ):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        rc = cmd_kit_install(["owner/repo"])
                self.assertEqual(rc, 1)
            finally:
                os.chdir(cwd)


# ---------------------------------------------------------------------------
# cmd_kit_update CLI paths
# ---------------------------------------------------------------------------

class TestCmdKitUpdateCli(unittest.TestCase):
    def setUp(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(True)

    def tearDown(self):
        from cypilot.utils.ui import set_json_mode
        set_json_mode(False)

    def test_update_local_path(self):
        from cypilot.commands.kit import cmd_kit_update
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td) / "src", "testkit")
            # Register kit in core.toml so it's installed
            from cypilot.utils import toml_utils
            toml_utils.dump({
                "version": "1.0",
                "project_root": "..",
                "kits": {"testkit": {"format": "Cypilot", "path": "config/kits/testkit"}},
            }, adapter / "config" / "core.toml")
            # Create installed kit dir
            config_kit = adapter / "config" / "kits" / "testkit"
            config_kit.mkdir(parents=True)
            (config_kit / "SKILL.md").write_text("old\n", encoding="utf-8")

            cwd = os.getcwd()
            try:
                os.chdir(root)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_update(["--path", str(kit_src), "--force", "-y"])
                self.assertEqual(rc, 0)
            finally:
                os.chdir(cwd)

    def test_update_local_path_not_found(self):
        from cypilot.commands.kit import cmd_kit_update
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            _bootstrap_project(root)
            cwd = os.getcwd()
            try:
                os.chdir(root)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_update(["--path", "/no/such/dir"])
                self.assertEqual(rc, 2)
            finally:
                os.chdir(cwd)

    def test_update_no_kits_registered(self):
        from cypilot.commands.kit import cmd_kit_update
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            # core.toml with empty kits
            from cypilot.utils import toml_utils
            toml_utils.dump({
                "version": "1.0",
                "project_root": "..",
                "kits": {},
            }, adapter / "config" / "core.toml")
            cwd = os.getcwd()
            try:
                os.chdir(root)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_update([])
                self.assertEqual(rc, 2)
            finally:
                os.chdir(cwd)

    def test_update_slug_not_found(self):
        from cypilot.commands.kit import cmd_kit_update
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            from cypilot.utils import toml_utils
            toml_utils.dump({
                "version": "1.0",
                "project_root": "..",
                "kits": {"sdlc": {"format": "Cypilot", "path": "config/kits/sdlc", "source": "github:o/r"}},
            }, adapter / "config" / "core.toml")
            cwd = os.getcwd()
            try:
                os.chdir(root)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_update(["nosuchkit"])
                self.assertEqual(rc, 2)
            finally:
                os.chdir(cwd)

    def test_update_from_github_source(self):
        from cypilot.commands.kit import cmd_kit_update
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            kit_src = _make_kit_source(Path(td) / "dl", "sdlc")
            from cypilot.utils import toml_utils
            toml_utils.dump({
                "version": "1.0",
                "project_root": "..",
                "kits": {"sdlc": {"format": "Cypilot", "path": "config/kits/sdlc", "source": "github:cyberfabric/cyber-pilot-kit-sdlc"}},
            }, adapter / "config" / "core.toml")

            cwd = os.getcwd()
            try:
                os.chdir(root)
                with patch(
                    "cypilot.commands.kit._download_kit_from_github",
                    return_value=(kit_src, "1.0"),
                ):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        rc = cmd_kit_update(["sdlc", "--force", "-y"])
                self.assertEqual(rc, 0)
            finally:
                os.chdir(cwd)

    def test_update_github_download_failure(self):
        from cypilot.commands.kit import cmd_kit_update
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            from cypilot.utils import toml_utils
            toml_utils.dump({
                "version": "1.0",
                "project_root": "..",
                "kits": {"sdlc": {"format": "Cypilot", "path": "config/kits/sdlc", "source": "github:o/r"}},
            }, adapter / "config" / "core.toml")
            cwd = os.getcwd()
            try:
                os.chdir(root)
                with patch(
                    "cypilot.commands.kit._download_kit_from_github",
                    side_effect=RuntimeError("rate limit"),
                ):
                    buf = io.StringIO()
                    with redirect_stdout(buf):
                        rc = cmd_kit_update([])
                self.assertEqual(rc, 2)
            finally:
                os.chdir(cwd)

    def test_update_unsupported_source(self):
        from cypilot.commands.kit import cmd_kit_update
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            from cypilot.utils import toml_utils
            toml_utils.dump({
                "version": "1.0",
                "project_root": "..",
                "kits": {"mykit": {"format": "Cypilot", "path": "config/kits/mykit", "source": "ftp://bad"}},
            }, adapter / "config" / "core.toml")
            cwd = os.getcwd()
            try:
                os.chdir(root)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_update([])
                self.assertEqual(rc, 2)
            finally:
                os.chdir(cwd)

    def test_update_no_source_skipped(self):
        from cypilot.commands.kit import cmd_kit_update
        with TemporaryDirectory() as td:
            root = Path(td) / "proj"
            adapter = _bootstrap_project(root)
            from cypilot.utils import toml_utils
            toml_utils.dump({
                "version": "1.0",
                "project_root": "..",
                "kits": {"mykit": {"format": "Cypilot", "path": "config/kits/mykit"}},
            }, adapter / "config" / "core.toml")
            cwd = os.getcwd()
            try:
                os.chdir(root)
                buf = io.StringIO()
                with redirect_stdout(buf):
                    rc = cmd_kit_update([])
                self.assertEqual(rc, 2)
            finally:
                os.chdir(cwd)


# ---------------------------------------------------------------------------
# update_kit version-check + partial/declined paths
# ---------------------------------------------------------------------------

class TestUpdateKitVersionPaths(unittest.TestCase):
    def test_dry_run(self):
        from cypilot.commands.kit import update_kit
        with TemporaryDirectory() as td:
            src = _make_kit_source(Path(td) / "src", "tk")
            cyp = Path(td) / "cyp"
            (cyp / "config" / "kits" / "tk").mkdir(parents=True)
            r = update_kit("tk", src, cyp, dry_run=True)
            self.assertEqual(r["version"]["status"], "dry_run")

    def test_version_current_skips(self):
        from cypilot.commands.kit import update_kit
        from cypilot.utils import toml_utils
        with TemporaryDirectory() as td:
            src = _make_kit_source(Path(td) / "src", "tk")
            cyp = Path(td) / "cyp"
            config_kit = cyp / "config" / "kits" / "tk"
            config_kit.mkdir(parents=True)
            (config_kit / "SKILL.md").write_text("# Skill\n", encoding="utf-8")
            toml_utils.dump({
                "kits": {"tk": {"version": "1", "path": "config/kits/tk"}},
            }, cyp / "config" / "core.toml")
            # Source has version=1 via conf.toml
            r = update_kit("tk", src, cyp, force=False)
            self.assertEqual(r["version"]["status"], "current")
            self.assertIn("skill_nav", r)


if __name__ == "__main__":
    unittest.main()
