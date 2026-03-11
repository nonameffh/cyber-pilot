---
cypilot: true
type: project-rule
topic: project-structure
generated-by: auto-config
version: 1.0
---

# Project Structure


<!-- toc -->

- [Root Directory](#root-directory)
- [CLI Package Structure](#cli-package-structure)
- [Kit Package Structure](#kit-package-structure)
- [Key Files](#key-files)

<!-- /toc -->

## Root Directory

```
./
├── .bootstrap/                # Cypilot adapter directory (cypilot_path = ".bootstrap")
│   ├── .core/                # Read-only core (from cache, do not edit)
│   │   ├── architecture/
│   │   ├── requirements/
│   │   ├── schemas/
│   │   ├── skills/
│   │   └── workflows/
│   ├── .gen/                 # Auto-generated aggregates only (do not edit)
│   │   ├── AGENTS.md
│   │   ├── SKILL.md
│   │   └── README.md
│   ├── config/               # User-editable configuration + kit outputs
│   │   ├── AGENTS.md         # Custom navigation rules
│   │   ├── SKILL.md          # Custom skill extensions
│   │   ├── core.toml         # Project config
│   │   ├── artifacts.toml    # Artifacts registry
│   │   ├── rules/            # Project rules (per-topic, auto-config)
│   │   └── kits/sdlc/        # Kit files (artifacts/, codebase/, workflows/, scripts/)
│   │       └── conf.toml     # Kit version metadata
│
├── .github/
│   └── workflows/ci.yml      # GitHub Actions CI (single source of truth)
│
├── AGENTS.md                 # Root navigation rules
├── CONTRIBUTING.md           # Development guide
├── README.md                 # Project documentation
├── Makefile                  # Build automation + local CI
├── pyproject.toml            # PyPI package config
│
├── architecture/             # Design artifacts
│   ├── PRD.md
│   ├── DESIGN.md
│   ├── DECOMPOSITION.md
│   ├── features/             # Feature specs
│   └── specs/                # Technical specs (CDSL, CLISPEC, etc.)
│
├── kits/                     # Kit packages (canonical source, NOT used in self-hosted)
│   └── sdlc/                 # Note: self-hosted uses cyber-pilot-kit-sdlc repo directly
│
├── skills/                   # Cypilot skills (canonical source)
│   └── cypilot/
│       ├── SKILL.md
│       └── scripts/cypilot/  # CLI package (skill engine)
│
├── src/                      # Proxy package (canonical source)
│   └── cypilot_proxy/
│       ├── cli.py
│       ├── resolve.py
│       └── cache.py
│
├── tests/                    # Test suite (44 test modules)
│   ├── test_*.py
│   ├── conftest.py
│   └── _test_helpers.py
│
├── scripts/                  # Utility scripts
│   ├── check_coverage.py
│   ├── check_versions.py
│   └── score_comparison_matrix.py
│
└── guides/                   # User guides
    ├── STORY.md
    ├── TAXONOMY.md
    └── MIGRATION.md
```

## CLI Package Structure

```
skills/cypilot/scripts/cypilot/
├── __init__.py              # Package init (version info)
├── __main__.py              # Entry point for `python -m cypilot`
├── cli.py                   # Main CLI — command dispatch only
├── constants.py             # Shared constants and regex patterns
│
├── commands/                # One module per CLI subcommand (18 modules)
│   ├── adapter_info.py      # info command
│   ├── agents.py            # agents command (multi-agent integration)
│   ├── get_content.py       # get-content command
│   ├── init.py              # init command
│   ├── kit.py               # kit install/update commands
│   ├── list_id_kinds.py     # list-id-kinds command
│   ├── list_ids.py          # list-ids command
│   ├── migrate.py           # migrate/migrate-config commands
│   ├── self_check.py        # self-check command
│   ├── spec_coverage.py     # spec-coverage command
│   ├── toc.py               # toc command
│   ├── update.py            # update command
│   ├── validate.py          # validate command
│   ├── validate_kits.py     # validate-kits command
│   ├── validate_toc.py      # validate-toc command
│   ├── where_defined.py     # where-defined command
│   └── where_used.py        # where-used command
│
└── utils/                   # Shared utility modules (17 modules)
    ├── __init__.py          # Re-exports all utilities
    ├── artifacts_meta.py    # artifacts.toml parsing → ArtifactsMeta
    ├── codebase.py          # Code file parsing → CodeFile, ScopeMarker
    ├── constraints.py       # constraints.toml parsing → KitConstraints
    ├── context.py           # CypilotContext singleton
    ├── coverage.py          # Spec coverage calculation
    ├── diff_engine.py       # File-level diff for kit updates
    ├── document.py          # Document utilities
    ├── error_codes.py       # Validation error codes
    ├── files.py             # File operations, project root discovery
    ├── fixing.py            # Auto-fix suggestions
    ├── language_config.py   # Language-specific configs
    ├── manifest.py          # Kit manifest parsing
    ├── parsing.py           # Markdown parsing, section splitting
    ├── toc.py               # Table of Contents generation
    ├── toml_utils.py        # TOML read/write helpers (stdlib tomllib)
    └── ui.py                # Terminal UI helpers
```

## Kit Package Structure

```
kits/sdlc/
├── README.md
├── artifacts/
│   ├── PRD/
│   │   ├── template.md
│   │   ├── rules.md
│   │   ├── checklist.md
│   │   └── examples/
│   ├── DESIGN/              # Same structure
│   ├── DECOMPOSITION/
│   ├── FEATURE/
│   └── ADR/
├── codebase/
│   ├── rules.md
│   └── checklist.md
└── guides/
```

## Key Files

| File | Purpose |
|------|---------|
| `.bootstrap/config/artifacts.toml` | Artifact registry |
| `.bootstrap/config/AGENTS.md` | Custom navigation rules |
| `.bootstrap/.gen/AGENTS.md` | Generated navigation rules |
| `.github/workflows/ci.yml` | CI pipeline (single source of truth) |
| `AGENTS.md` | Root navigation (routes to above) |
| `Makefile` | Build/test/CI commands |
