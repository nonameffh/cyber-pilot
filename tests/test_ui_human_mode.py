"""Tests for human-mode output: ui.py functions, _human_* formatters, cli help."""

import io
import json
import sys
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch

from cypilot.utils.ui import (
    set_json_mode,
    is_json_mode,
    header,
    step,
    substep,
    success,
    error,
    warn,
    info,
    detail,
    hint,
    blank,
    divider,
    table,
    file_action,
    result,
    _has_color,
    _c,
    ui,
)


class _HumanModeBase(unittest.TestCase):
    """Base that switches to human mode for each test."""

    def setUp(self):
        set_json_mode(False)

    def tearDown(self):
        set_json_mode(True)


# ---------------------------------------------------------------------------
# ui.py core functions
# ---------------------------------------------------------------------------

class TestUIFunctions(_HumanModeBase):
    """Test all ui.py output functions in human (non-JSON) mode."""

    def test_header(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            header("Test Header")
        self.assertIn("Test Header", buf.getvalue())

    def test_step(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            step("Doing something")
        self.assertIn("Doing something", buf.getvalue())

    def test_substep(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            substep("sub item")
        self.assertIn("sub item", buf.getvalue())

    def test_success(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            success("All good")
        self.assertIn("All good", buf.getvalue())

    def test_error(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            error("Something broke")
        self.assertIn("Something broke", buf.getvalue())

    def test_warn(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            warn("Watch out")
        self.assertIn("Watch out", buf.getvalue())

    def test_info(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            info("FYI")
        self.assertIn("FYI", buf.getvalue())

    def test_detail(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            detail("Key", "Value")
        out = buf.getvalue()
        self.assertIn("Key", out)
        self.assertIn("Value", out)

    def test_hint(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            hint("Try this")
        self.assertIn("Try this", buf.getvalue())

    def test_blank(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            blank()
        self.assertEqual(buf.getvalue(), "\n")

    def test_divider(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            divider()
        self.assertIn("─", buf.getvalue())

    def test_table_with_rows(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            table(["Name", "Value"], [["foo", "bar"], ["baz", "qux"]])
        out = buf.getvalue()
        self.assertIn("Name", out)
        self.assertIn("foo", out)
        self.assertIn("baz", out)

    def test_table_empty_rows(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            table(["Name"], [])
        self.assertEqual(buf.getvalue(), "")

    def test_table_extra_columns_in_row(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            table(["A"], [["x", "y"]])
        out = buf.getvalue()
        self.assertIn("x", out)
        self.assertIn("y", out)

    def test_file_action_created(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            file_action("foo.py", "created")
        out = buf.getvalue()
        self.assertIn("foo.py", out)
        self.assertIn("created", out)

    def test_file_action_updated(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            file_action("bar.py", "updated")
        self.assertIn("updated", buf.getvalue())

    def test_file_action_deleted(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            file_action("baz.py", "deleted")
        self.assertIn("deleted", buf.getvalue())

    def test_file_action_unknown(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            file_action("x.py", "unknown_action")
        self.assertIn("x.py", buf.getvalue())

    def test_file_action_skipped(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            file_action("s.py", "skipped")
        self.assertIn("skipped", buf.getvalue())

    def test_file_action_missing_in_cache(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            file_action("m.py", "missing_in_cache")
        self.assertIn("missing_in_cache", buf.getvalue())

    def test_file_action_preserved(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            file_action("p.py", "preserved")
        self.assertIn("preserved", buf.getvalue())

    def test_file_action_dry_run(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            file_action("d.py", "dry_run")
        self.assertIn("dry_run", buf.getvalue())

    def test_file_action_unchanged(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            file_action("u.py", "unchanged")
        self.assertIn("unchanged", buf.getvalue())


class TestUIColorHelpers(_HumanModeBase):
    """Test _has_color and _c helpers."""

    def test_has_color_false_in_test(self):
        self.assertFalse(_has_color())

    def test_c_no_color(self):
        self.assertEqual(_c("\033[1m", "text"), "text")


class TestUIResult(_HumanModeBase):
    """Test result() in human mode — generic fallback and custom fn."""

    def test_result_pass_status(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            result({"status": "PASS"})
        self.assertIn("Done", buf.getvalue())

    def test_result_ok_status(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            result({"status": "OK", "message": "fine"})
        self.assertIn("fine", buf.getvalue())

    def test_result_dry_run_status(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            result({"status": "DRY_RUN"})
        self.assertIn("DRY_RUN", buf.getvalue())

    def test_result_fail_status(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            result({"status": "FAIL", "message": "broken"})
        self.assertIn("broken", buf.getvalue())

    def test_result_error_status_no_message(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            result({"status": "ERROR"})
        self.assertIn("ERROR", buf.getvalue())

    def test_result_aborted_status(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            result({"status": "ABORTED", "message": "user cancelled"})
        self.assertIn("Aborted", buf.getvalue())
        self.assertIn("user cancelled", buf.getvalue())

    def test_result_aborted_no_message(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            result({"status": "ABORTED"})
        self.assertIn("Aborted", buf.getvalue())

    def test_result_unknown_status(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            result({"status": "WEIRD"})
        self.assertIn("WEIRD", buf.getvalue())

    def test_result_unknown_status_with_message(self):
        buf = io.StringIO()
        with redirect_stderr(buf):
            result({"status": "CUSTOM", "message": "hello"})
        self.assertIn("hello", buf.getvalue())

    def test_result_custom_human_fn(self):
        called = []

        def my_fn(d):
            called.append(d)

        result({"status": "PASS"}, human_fn=my_fn)
        self.assertEqual(len(called), 1)
        self.assertEqual(called[0]["status"], "PASS")

    def test_result_json_mode(self):
        set_json_mode(True)
        buf = io.StringIO()
        with redirect_stdout(buf):
            result({"status": "OK"})
        out = json.loads(buf.getvalue())
        self.assertEqual(out["status"], "OK")
        set_json_mode(False)


class TestUISingleton(unittest.TestCase):
    """Test the ui singleton exposes all methods."""

    def test_ui_has_all_methods(self):
        for attr in ["header", "step", "substep", "success", "error", "warn",
                      "info", "detail", "hint", "blank", "divider", "table",
                      "file_action", "result", "is_json"]:
            self.assertTrue(hasattr(ui, attr), f"ui missing {attr}")


# ---------------------------------------------------------------------------
# Human formatters from commands
# ---------------------------------------------------------------------------

class TestHumanValidate(_HumanModeBase):
    """Test _human_validate formatter."""

    def test_validate_pass(self):
        from cypilot.commands.validate import _human_validate
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_validate({
                "status": "PASS",
                "artifacts_validated": 5,
                "error_count": 0,
                "warning_count": 0,
                "code_files_scanned": 10,
                "coverage": "50/50",
                "next_step": "Review content",
            })
        out = buf.getvalue()
        self.assertIn("Validate", out)
        self.assertIn("passed", out)

    def test_validate_fail_with_errors(self):
        from cypilot.commands.validate import _human_validate
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_validate({
                "status": "FAIL",
                "artifacts_validated": 3,
                "error_count": 2,
                "warning_count": 1,
                "errors": [
                    {"message": "Missing section", "path": "DESIGN.md", "line": "10"},
                    {"message": "Bad ref"},
                ] + [{"message": f"err{i}"} for i in range(25)],
                "warnings": [{"message": f"w{i}"} for i in range(15)],
            })
        out = buf.getvalue()
        self.assertIn("failed", out)
        self.assertIn("DESIGN.md:10", out)
        self.assertIn("more error", out)
        self.assertIn("more warning", out)

    def test_validate_other_status(self):
        from cypilot.commands.validate import _human_validate
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_validate({"status": "PARTIAL", "artifact_count": 1, "error_count": 0, "warning_count": 0})
        self.assertIn("PARTIAL", buf.getvalue())

    def test_validate_string_errors(self):
        from cypilot.commands.validate import _human_validate
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_validate({
                "status": "FAIL", "error_count": 1, "warning_count": 1,
                "errors": ["simple error string"],
                "warnings": ["simple warning"],
            })
        out = buf.getvalue()
        self.assertIn("simple error string", out)
        self.assertIn("simple warning", out)


class TestHumanSelfCheck(_HumanModeBase):
    """Test _human_self_check formatter."""

    def test_self_check_pass(self):
        from cypilot.commands.self_check import _human_self_check
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_self_check({
                "status": "PASS",
                "kits_checked": 1,
                "templates_checked": 3,
                "results": [
                    {"kit": "sdlc", "kind": "PRD", "status": "PASS"},
                ],
            })
        out = buf.getvalue()
        self.assertIn("Self-Check", out)
        self.assertIn("consistent", out)

    def test_self_check_fail(self):
        from cypilot.commands.self_check import _human_self_check
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_self_check({
                "status": "FAIL",
                "kits_checked": 1,
                "templates_checked": 1,
                "results": [
                    {"kit": "sdlc", "kind": "PRD", "status": "FAIL", "error_count": 2,
                     "errors": [{"message": "oops"}, "plain error"]},
                ],
            })
        out = buf.getvalue()
        self.assertIn("failed", out)
        self.assertIn("oops", out)


class TestHumanValidateKits(_HumanModeBase):
    """Test _human_validate_kits formatter."""

    def test_pass(self):
        from cypilot.commands.validate_kits import _human_validate_kits
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_validate_kits({
                "status": "PASS", "kits_validated": 1,
                "error_count": 0,
                "kits": [{"kit": "sdlc", "status": "PASS"}],
            })
        out = buf.getvalue()
        self.assertIn("all passed", out)
        self.assertIn("sdlc", out)

    def test_fail_with_errors(self):
        from cypilot.commands.validate_kits import _human_validate_kits
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_validate_kits({
                "status": "FAIL", "kits_validated": 1,
                "error_count": 3,
                "kits": [{"kit": "sdlc", "status": "FAIL", "error_count": 3}],
                "failed_kits": [{"kit": "sdlc", "error_count": 3}],
            })
        out = buf.getvalue()
        self.assertIn("error(s)", out)
        self.assertIn("sdlc", out)


class TestHumanValidateToc(_HumanModeBase):
    """Test _human_validate_toc formatter."""

    def test_pass(self):
        from cypilot.commands.validate_toc import _human_validate_toc
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_validate_toc({
                "status": "PASS", "files_validated": 2,
                "error_count": 0, "warning_count": 0,
                "results": [{"file": "a.md", "status": "PASS"}],
            })
        out = buf.getvalue()
        self.assertIn("all TOCs correct", out)

    def test_fail_with_errors_and_warnings(self):
        from cypilot.commands.validate_toc import _human_validate_toc
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_validate_toc({
                "status": "FAIL", "files_validated": 1,
                "error_count": 1, "warning_count": 1,
                "results": [
                    {"file": "README.md", "status": "FAIL", "error_count": 1, "warning_count": 1,
                     "errors": ["missing toc"], "warnings": ["stale toc"]},
                ],
            })
        out = buf.getvalue()
        self.assertIn("error(s) found", out)
        self.assertIn("README.md", out)
        self.assertIn("stale toc", out)


class TestHumanToc(_HumanModeBase):
    """Test _human_toc formatter."""

    def test_pass(self):
        from cypilot.commands.toc import _human_toc
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_toc({
                "status": "PASS", "files_processed": 2,
                "results": [
                    {"file": "a.md", "status": "UPDATED"},
                    {"file": "b.md", "status": "UNCHANGED"},
                    {"file": "c.md", "status": "CREATED"},
                    {"file": "d.md", "status": "ERROR", "message": "bad file"},
                    {"file": "e.md", "status": "CUSTOM"},
                    {"file": "f.md", "status": "OK", "validation": {"status": "FAIL", "details": ["stale entry"]}},
                ],
            })
        out = buf.getvalue()
        self.assertIn("updated", out)
        self.assertIn("unchanged", out)
        self.assertIn("created", out)
        self.assertIn("bad file", out)
        self.assertIn("CUSTOM", out)
        self.assertIn("stale entry", out)

    def test_validation_fail_status(self):
        from cypilot.commands.toc import _human_toc
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_toc({
                "status": "VALIDATION_FAIL", "files_processed": 1,
                "results": [],
            })
        self.assertIn("validation errors", buf.getvalue())

    def test_other_status(self):
        from cypilot.commands.toc import _human_toc
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_toc({
                "status": "PARTIAL", "files_processed": 1,
                "results": [],
            })
        self.assertIn("PARTIAL", buf.getvalue())


class TestHumanSpecCoverage(_HumanModeBase):
    """Test _human_spec_coverage formatter."""

    def test_pass(self):
        from cypilot.commands.spec_coverage import _human_spec_coverage
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_spec_coverage({
                "status": "PASS",
                "summary": {
                    "covered_files": 8,
                    "total_files": 10,
                    "coverage_pct": 95.0,
                    "granularity_score": 0.88,
                },
            })
        out = buf.getvalue()
        self.assertIn("95.0%", out)
        self.assertIn("thresholds met", out)

    def test_fail(self):
        from cypilot.commands.spec_coverage import _human_spec_coverage
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_spec_coverage({
                "status": "FAIL",
                "summary": {
                    "covered_files": 2,
                    "total_files": 10,
                    "coverage_pct": 50.0,
                    "granularity_score": 0.3,
                },
                "threshold_failures": ["coverage below 80%"],
            })
        out = buf.getvalue()
        self.assertIn("Threshold check failed", out)
        self.assertIn("coverage below 80%", out)

    def test_other_status(self):
        from cypilot.commands.spec_coverage import _human_spec_coverage
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_spec_coverage({"status": "PARTIAL", "summary": {}})
        self.assertIn("PARTIAL", buf.getvalue())


class TestHumanInfo(_HumanModeBase):
    """Test _human_info formatter."""

    def test_full_info(self):
        from cypilot.commands.adapter_info import _human_info
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_info({
                "status": "FOUND",
                "project_name": "MyProject",
                "project_root": "/tmp/myproject",
                "relative_path": ".bootstrap",
                "config_version": "1.0",
                "has_config": True,
                "directories": {".core": True, ".gen": True, "config": True, "kits": False},
                "kit_details": {
                    "sdlc": {
                        "name": "SDLC Kit", "slug": "sdlc",
                        "ref_version": 4, "config_version": 3, "drift": True,
                        "blueprints": ["PRD", "DESIGN"],
                        "artifact_kinds": ["PRD", "DESIGN"],
                        "workflows": ["pr-review"],
                    },
                },
                "autodetect_registry": {
                    "systems": [
                        {"name": "Main", "slug": "main", "kit": "sdlc",
                         "children": [{"name": "Sub", "slug": "sub"}]},
                    ],
                },
                "artifacts_registry": {
                    "systems": [
                        {
                            "name": "Main", "slug": "main", "kit": "sdlc",
                            "artifacts": [
                                {"path": "arch/PRD.md", "kind": "PRD", "traceability": "FULL"},
                                {"path": "arch/DESIGN.md", "kind": "DESIGN", "traceability": "DOCS-ONLY"},
                            ],
                            "codebase": [
                                {"path": "src/", "extensions": [".py", ".ts"]},
                                {"path": "lib/"},
                            ],
                            "children": [
                                {
                                    "name": "Sub", "slug": "sub",
                                    "artifacts": [{"path": "sub/PRD.md", "kind": "PRD"}],
                                    "codebase": [{"path": "sub/src", "extensions": [".py"]}],
                                },
                            ],
                        },
                    ],
                },
                "rules": ["conventions", "testing"],
                "agent_integrations": ["windsurf", "cursor"],
                "artifacts_registry_error": None,
            })
        out = buf.getvalue()
        self.assertIn("MyProject", out)
        self.assertIn(".bootstrap", out)
        self.assertIn("1.0", out)
        self.assertIn("Missing directories: kits", out)
        self.assertIn("SDLC Kit", out)
        self.assertIn("migration needed", out)
        self.assertIn("PRD, DESIGN", out)
        self.assertIn("pr-review", out)
        self.assertIn("Main (main)", out)
        self.assertIn("arch/PRD.md", out)
        self.assertIn("FULL", out)
        self.assertIn("Sub (sub)", out)
        self.assertIn("conventions", out)
        self.assertIn("windsurf", out)

    def test_minimal_info(self):
        from cypilot.commands.adapter_info import _human_info
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_info({
                "status": "FOUND",
                "project_root": "/tmp/x",
                "cypilot_dir": "/tmp/x/cypilot",
                "has_config": False,
                "directories": {".core": True, ".gen": True, "config": True, "kits": True},
                "rules": [],
                "kit_details": {},
                "agent_integrations": [],
            })
        out = buf.getvalue()
        self.assertIn("Project root", out)
        self.assertNotIn("Missing", out)

    def test_info_with_registry_error(self):
        from cypilot.commands.adapter_info import _human_info
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_info({
                "status": "FOUND",
                "project_root": "/tmp/x",
                "has_config": True,
                "directories": {},
                "rules": [],
                "kit_details": {},
                "agent_integrations": [],
                "artifacts_registry_error": "MISSING",
            })
        self.assertIn("MISSING", buf.getvalue())

    def test_info_kit_no_drift(self):
        from cypilot.commands.adapter_info import _human_info
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_info({
                "status": "FOUND",
                "project_root": "/tmp",
                "has_config": True,
                "directories": {},
                "kit_details": {
                    "sdlc": {"name": "Kit", "ref_version": 4, "config_version": 4, "drift": False},
                },
                "rules": [],
                "agent_integrations": [],
            })
        out = buf.getvalue()
        self.assertIn("v4", out)
        self.assertNotIn("migration", out)

    def test_info_autodetect_systems_fallback(self):
        """When artifacts_registry has no systems, falls back to autodetect_registry."""
        from cypilot.commands.adapter_info import _human_info
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_info({
                "status": "FOUND",
                "project_root": "/tmp",
                "has_config": True,
                "directories": {},
                "kit_details": {},
                "rules": [],
                "agent_integrations": [],
                "autodetect_registry": {
                    "systems": [{"name": "Sys", "slug": "sys"}],
                },
                "artifacts_registry": {},
            })
        self.assertIn("Sys (sys)", buf.getvalue())


class TestReadKitConf(unittest.TestCase):
    """Test _read_kit_conf helper."""

    def test_reads_valid_conf(self):
        from cypilot.commands.adapter_info import _read_kit_conf
        with TemporaryDirectory() as td:
            conf = Path(td) / "conf.toml"
            conf.write_text('version = 4\nslug = "sdlc"\nname = "SDLC Kit"\n')
            result = _read_kit_conf(conf)
            self.assertEqual(result["version"], 4)
            self.assertEqual(result["slug"], "sdlc")
            self.assertEqual(result["name"], "SDLC Kit")

    def test_missing_file(self):
        from cypilot.commands.adapter_info import _read_kit_conf
        result = _read_kit_conf(Path("/nonexistent/conf.toml"))
        self.assertEqual(result, {})

    def test_invalid_toml(self):
        from cypilot.commands.adapter_info import _read_kit_conf
        with TemporaryDirectory() as td:
            conf = Path(td) / "conf.toml"
            conf.write_text("not valid toml {{{")
            result = _read_kit_conf(conf)
            self.assertEqual(result, {})


# ---------------------------------------------------------------------------
# CLI help branch
# ---------------------------------------------------------------------------

class TestCLIHelpHumanMode(_HumanModeBase):
    """Test CLI help in human mode."""

    def test_help_human_mode(self):
        from cypilot.cli import main
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = main(["--help"])
        self.assertEqual(rc, 0)
        out = buf.getvalue()
        self.assertIn("Cypilot CLI", out)
        self.assertIn("validate", out)
        self.assertIn("--json", out)

    def test_empty_command_human_mode(self):
        from cypilot.cli import main
        buf = io.StringIO()
        with redirect_stderr(buf):
            rc = main([])
        self.assertEqual(rc, 0)
        self.assertIn("Cypilot CLI", buf.getvalue())


# ---------------------------------------------------------------------------
# init.py human formatters + _inject_root_claude
# ---------------------------------------------------------------------------

class TestHumanInitOk(_HumanModeBase):
    """Test _human_init_ok formatter."""

    def test_normal_init(self):
        from cypilot.commands.init import _human_init_ok
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_init_ok(
                {"status": "PASS", "dry_run": False, "actions": {}},
                Path("/tmp/proj"),
                Path("/tmp/proj/cypilot"),
                "cypilot",
                "MyProject",
                {"sdlc": {"files_written": 10, "artifact_kinds": ["PRD", "DESIGN"]}},
            )
        out = buf.getvalue()
        self.assertIn("Cypilot Init", out)
        self.assertIn("MyProject", out)
        self.assertIn("Core files", out)
        self.assertIn("sdlc", out)
        self.assertIn("initialized", out)
        self.assertIn("Next steps", out)

    def test_dry_run_init(self):
        from cypilot.commands.init import _human_init_ok
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_init_ok(
                {"status": "PASS", "dry_run": True, "actions": {}},
                Path("/tmp/proj"),
                Path("/tmp/proj/cypilot"),
                "cypilot",
                "Proj",
                {},
            )
        out = buf.getvalue()
        self.assertIn("dry-run", out)
        self.assertIn("Dry run complete", out)

    def test_no_kits(self):
        from cypilot.commands.init import _human_init_ok
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_init_ok(
                {"status": "PASS", "dry_run": False, "actions": {}},
                Path("/tmp/proj"),
                Path("/tmp/proj/cypilot"),
                "cypilot",
                "Proj",
                {},
            )
        out = buf.getvalue()
        self.assertNotIn("Kits installed", out)


class TestHumanInitError(_HumanModeBase):
    """Test _human_init_error formatter."""

    def test_dict_errors(self):
        from cypilot.commands.init import _human_init_error
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_init_error({
                "status": "ERROR",
                "errors": [
                    {"path": "core.toml", "error": "permission denied"},
                    "simple error string",
                ],
            })
        out = buf.getvalue()
        self.assertIn("failed", out)
        self.assertIn("core.toml", out)
        self.assertIn("simple error string", out)

    def test_empty_errors(self):
        from cypilot.commands.init import _human_init_error
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_init_error({"status": "ERROR", "errors": []})
        self.assertIn("failed", buf.getvalue())


class TestInjectRootClaude(unittest.TestCase):
    """Test _inject_root_claude update/insert paths."""

    def test_update_existing_block(self):
        from cypilot.commands.init import _inject_root_claude, _compute_claude_block, MARKER_START, MARKER_END
        with TemporaryDirectory() as td:
            root = Path(td)
            claude = root / "CLAUDE.md"
            # Write a stale block
            claude.write_text(f"Before\n{MARKER_START}\nOLD CONTENT\n{MARKER_END}\nAfter\n")
            action = _inject_root_claude(root, "cypilot")
            self.assertEqual(action, "updated")
            content = claude.read_text()
            self.assertIn(MARKER_START, content)
            self.assertIn("After", content)

    def test_insert_into_existing_no_markers(self):
        from cypilot.commands.init import _inject_root_claude
        with TemporaryDirectory() as td:
            root = Path(td)
            claude = root / "CLAUDE.md"
            claude.write_text("Existing content\n")
            action = _inject_root_claude(root, "cypilot")
            self.assertEqual(action, "updated")
            content = claude.read_text()
            self.assertIn("Existing content", content)

    def test_unchanged_block(self):
        from cypilot.commands.init import _inject_root_claude, _compute_claude_block
        with TemporaryDirectory() as td:
            root = Path(td)
            claude = root / "CLAUDE.md"
            claude.write_text(_compute_claude_block() + "\n")
            action = _inject_root_claude(root, "cypilot")
            self.assertEqual(action, "unchanged")

    def test_create_new(self):
        from cypilot.commands.init import _inject_root_claude
        with TemporaryDirectory() as td:
            root = Path(td)
            action = _inject_root_claude(root, "cypilot")
            self.assertEqual(action, "created")
            self.assertTrue((root / "CLAUDE.md").exists())


class TestReadExistingInstall(unittest.TestCase):
    """Test _read_existing_install edge cases."""

    def test_returns_none_when_dir_missing(self):
        from cypilot.commands.init import _read_existing_install, MARKER_START
        with TemporaryDirectory() as td:
            root = Path(td)
            agents = root / "AGENTS.md"
            agents.write_text(f"{MARKER_START}\n```toml\ncypilot_path = \"missing\"\n```\n")
            result = _read_existing_install(root)
            self.assertIsNone(result)

    def test_returns_none_for_invalid_toml(self):
        from cypilot.commands.init import _read_existing_install, MARKER_START
        with TemporaryDirectory() as td:
            root = Path(td)
            agents = root / "AGENTS.md"
            agents.write_text(f"{MARKER_START}\n```toml\n{{{{invalid\n```\n")
            result = _read_existing_install(root)
            self.assertIsNone(result)


# ---------------------------------------------------------------------------
# agents.py human formatter
# ---------------------------------------------------------------------------

class TestHumanAgentsOk(_HumanModeBase):
    """Test _human_agents_ok formatter."""

    def test_pass_with_workflows_and_skills(self):
        from cypilot.commands.agents import _human_agents_ok
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_agents_ok(
                {"status": "PASS"},
                ["windsurf", "cursor"],
                {
                    "windsurf": {
                        "status": "PASS",
                        "workflows": {
                            "created": [".windsurf/workflows/gen.md"],
                            "updated": [".windsurf/workflows/analyze.md"],
                            "counts": {"created": 1, "updated": 1},
                        },
                        "skills": {
                            "created": [".windsurf/skills/cypilot/SKILL.md"],
                            "updated": [],
                            "counts": {"created": 1, "updated": 0},
                        },
                    },
                    "cursor": {
                        "status": "WARN",
                        "workflows": {"created": [], "updated": [], "counts": {}},
                        "skills": {"created": [], "updated": [], "counts": {}},
                        "errors": ["Missing config"],
                    },
                },
                dry_run=False,
            )
        out = buf.getvalue()
        self.assertIn("windsurf", out)
        self.assertIn("cursor", out)
        self.assertIn("gen.md", out)
        self.assertIn("created", out)
        self.assertIn("updated", out)
        self.assertIn("SKILL.md", out)
        self.assertIn("workflow(s)", out)
        self.assertIn("Missing config", out)
        self.assertIn("Agent integration complete", out)

    def test_dry_run(self):
        from cypilot.commands.agents import _human_agents_ok
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_agents_ok(
                {"status": "PASS"},
                ["windsurf"],
                {"windsurf": {
                    "status": "PASS",
                    "workflows": {"created": [], "updated": [], "counts": {}},
                    "skills": {"created": [], "updated": [], "counts": {}},
                }},
                dry_run=True,
            )
        self.assertIn("Dry run complete", buf.getvalue())

    def test_errors_status(self):
        from cypilot.commands.agents import _human_agents_ok
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_agents_ok(
                {"status": "PARTIAL"},
                ["windsurf"],
                {"windsurf": {
                    "status": "ERROR",
                    "workflows": {"created": [], "updated": [], "counts": {}},
                    "skills": {"created": [], "updated": [], "counts": {}},
                }},
                dry_run=False,
            )
        self.assertIn("errors", buf.getvalue())


class TestEnsureCypilotLocal(unittest.TestCase):
    """Test _ensure_cypilot_local copy paths."""

    def test_already_local(self):
        from cypilot.commands.agents import _ensure_cypilot_local
        with TemporaryDirectory() as td:
            root = Path(td)
            cypilot = root / "cypilot"
            cypilot.mkdir()
            result_path, report = _ensure_cypilot_local(cypilot, root, dry_run=False)
            self.assertEqual(result_path, cypilot)
            self.assertEqual(report["action"], "none")

    def test_copy_into_project(self):
        from cypilot.commands.agents import _ensure_cypilot_local
        with TemporaryDirectory() as td:
            root = Path(td) / "project"
            root.mkdir()
            ext_cypilot = Path(td) / "external_cypilot"
            ext_cypilot.mkdir()
            # Create minimal structure so _is_cypilot_root passes
            (ext_cypilot / ".core").mkdir()
            (ext_cypilot / ".core" / "requirements").mkdir(parents=True)
            result_path, report = _ensure_cypilot_local(ext_cypilot, root, dry_run=False)
            self.assertIn(report["action"], ("copied", "error"))


# ---------------------------------------------------------------------------
# update.py human formatter
# ---------------------------------------------------------------------------

class TestHumanUpdateOk(_HumanModeBase):
    """Test _human_update_ok formatter."""

    def test_pass_no_errors(self):
        from cypilot.commands.update import _human_update_ok
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_update_ok(
                {"status": "PASS", "dry_run": False},
                errors=[],
                warnings=[],
            )
        out = buf.getvalue()
        self.assertIn("Update complete", out)

    def test_dry_run(self):
        from cypilot.commands.update import _human_update_ok
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_update_ok(
                {"status": "PASS", "dry_run": True},
                errors=[],
                warnings=[],
            )
        self.assertIn("Dry run complete", buf.getvalue())

    def test_with_errors(self):
        from cypilot.commands.update import _human_update_ok
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_update_ok(
                {"status": "WARN", "dry_run": False},
                errors=[
                    {"path": "sdlc", "error": "some issue"},
                    "plain error",
                ],
                warnings=["kit drift detected"],
            )
        out = buf.getvalue()
        self.assertIn("sdlc", out)
        self.assertIn("some issue", out)
        self.assertIn("plain error", out)
        self.assertIn("kit drift", out)
        self.assertIn("warnings", out)

    def test_warn_status(self):
        from cypilot.commands.update import _human_update_ok
        buf = io.StringIO()
        with redirect_stderr(buf):
            _human_update_ok(
                {"status": "WARN", "dry_run": False},
                errors=[],
                warnings=[],
            )
        self.assertIn("warnings", buf.getvalue())


if __name__ == "__main__":
    unittest.main()
