# Contributing to Cypilot


<!-- toc -->

- [Contributing to Cypilot](#contributing-to-cypilot)
  - [Thank you for your interest in contributing to Cypilot! This guide covers the development workflow, versioning scheme, bootstrap architecture, commit requirements, and CI pipeline.](#thank-you-for-your-interest-in-contributing-to-cypilot-this-guide-covers-the-development-workflow-versioning-scheme-bootstrap-architecture-commit-requirements-and-ci-pipeline)
  - [Prerequisites](#prerequisites)
  - [Development Setup](#development-setup)
  - [Project Architecture (Self-Hosted Bootstrap)](#project-architecture-self-hosted-bootstrap)
    - [Critical Rule](#critical-rule)
  - [Versioning](#versioning)
    - [Version Locations](#version-locations)
    - [Releasing a New Version](#releasing-a-new-version)
  - [Branch and Release Workflow](#branch-and-release-workflow)
  - [Commit Requirements (DCO)](#commit-requirements-dco)
    - [How to sign off](#how-to-sign-off)
    - [Retroactive sign-off](#retroactive-sign-off)
    - [Why DCO?](#why-dco)
  - [CI Pipeline](#ci-pipeline)
    - [Running CI Locally](#running-ci-locally)
    - [Makefile Targets](#makefile-targets)
    - [GitHub Actions](#github-actions)
  - [Making Changes](#making-changes)
    - [Code Changes](#code-changes)
    - [Architecture / Spec Changes](#architecture--spec-changes)
  - [Pull Request Process](#pull-request-process)
  - [Code Style and Conventions](#code-style-and-conventions)
  - [Questions?](#questions)

<!-- /toc -->

Thank you for your interest in contributing to Cypilot! This guide covers the development workflow, versioning scheme, bootstrap architecture, commit requirements, and CI pipeline.
---

## Prerequisites

- **Python 3.11+** (uses `tomllib` from stdlib)
- **Git**
- **pipx** (recommended for global CLI and test tooling)
- **make**
- **Docker** (for local CI via `act`)
- **[act](https://github.com/nektos/act)** (runs GitHub Actions locally)
- **[actionlint](https://github.com/rhysd/actionlint)** (lints workflow files)

## Development Setup

```bash
# Clone the repo
git clone https://github.com/cyberfabric/cyber-pilot.git
cd cyber-pilot

# Install the cpt/cypilot CLI proxy from local source
make install-proxy

# Bootstrap: sync .bootstrap/ from local source
make update

# Run full CI locally (mirrors GitHub Actions exactly)
make ci
```

---

## Project Architecture (Self-Hosted Bootstrap)

Cypilot builds itself. The repo is simultaneously the **source code** and a **Cypilot-managed project** with its own `.bootstrap/` adapter directory.

```
cypilot/                          # Project root
├── skills/cypilot/               # CANONICAL source: skill engine + scripts
├── src/cypilot_proxy/            # CANONICAL source: CLI proxy (thin shell)
├── schemas/                      # CANONICAL source: JSON schemas
├── architecture/                 # CANONICAL source: PRD, DESIGN, DECOMPOSITION, features
├── requirements/                 # CANONICAL source: checklists
├── .bootstrap/                   # Adapter directory (cypilot_path = ".bootstrap")
│   ├── .core/                    #   READ-ONLY mirror of skills/, schemas/, architecture/, etc.
│   ├── .gen/                     #   AUTO-GENERATED aggregates (AGENTS.md, SKILL.md, README.md)
│   └── config/                   #   User-editable config + kit outputs (core.toml, artifacts.toml, kits/)
├── tests/                        # Test suite
└── Makefile                      # CI targets
```

### Critical Rule

> **NEVER edit files inside `.bootstrap/.core/` or `.bootstrap/.gen/`.**
> These are read-only copies. Always edit the canonical source files under project root
> (`skills/`, `kits/`, `schemas/`, etc.) and then run `make update` to sync.

The `make update` command runs `cpt update --source . --force`, which:
1. Copies canonical sources into `.bootstrap/.core/`
2. Regenerates `.bootstrap/.gen/` aggregates
3. Updates kit files in `.bootstrap/config/kits/`

---

## Versioning

Cypilot has **two independent version tracks**.

### Version Locations

| File | Example | What it versions | When to bump |
|------|---------|------------------|--------------|
| `skills/cypilot/scripts/cypilot/__init__.py` | `v3.0.6-beta` | **Skill engine** — the core validation/generation logic | Any change to skill engine code |
| `src/cypilot_proxy/__init__.py` | `v3.0.2-beta` | **CLI proxy** — the thin routing shell | Changes to proxy routing, caching, or resolution |
| `pyproject.toml` (`version`) | `3.0.2-beta` | **PyPI package** — installed via `pipx` | Must match `src/cypilot_proxy/__init__.py` (without `v` prefix) |

### Releasing a New Version

1. **Create a release branch** from `main`:
   ```bash
   git checkout main && git pull --rebase
   git checkout -b v3.0.6-beta
   ```

2. **Bump the skill engine version** in `skills/cypilot/scripts/cypilot/__init__.py`:
   ```python
   __version__ = "v3.0.6-beta"
   ```

3. **If proxy changed**, bump both proxy files **in sync**:
   ```python
   # src/cypilot_proxy/__init__.py
   __version__ = "v3.0.6-beta"
   ```
   ```toml
   # pyproject.toml
   version = "3.0.6-beta"   # same value, no 'v' prefix
   ```

4. **Sync bootstrap**:
   ```bash
   make update
   ```

5. **Verify** everything passes:
   ```bash
   make test
   make validate
   make self-check
   ```

6. **Tag and release** after merge to `main`:
   ```bash
   git tag v3.0.6-beta
   git push origin v3.0.6-beta
   ```

---

## Branch and Release Workflow

```
main                          # Stable, all CI must pass
└── v3.0.6-beta               # Feature/release branch
```

- Branch from `main` for each version
- All work happens on the version branch
- Merge to `main` via PR after CI passes
- Tag `main` after merge

---

## Commit Requirements (DCO)

All commits **must** include a `Signed-off-by` line — the [Developer Certificate of Origin](https://developercertificate.org/) (DCO).

### How to sign off

```bash
# Every commit must use -s
git commit -s -m "feat(validate): add cross-reference checking"
```

This appends:
```
Signed-off-by: Your Name <your.email@example.com>
```

### Retroactive sign-off

If you forgot `-s`, amend the last commit:
```bash
git commit --amend -s --no-edit
```

For multiple commits:
```bash
git rebase --signoff HEAD~N
```

### Why DCO?

The project uses Apache-2.0 license. DCO certifies that you wrote the contribution (or have the right to submit it) and agree to the project's license terms.

---

## CI Pipeline

### Running CI Locally

`make ci` runs the **exact same workflow** as GitHub Actions, locally via [act](https://github.com/nektos/act) in Docker. Single source of truth — `.github/workflows/ci.yml`.

```bash
# Run full CI (auto-detects arm64/amd64)
make ci

# Override act flags if needed
make ci ACT_FLAGS="--container-architecture linux/amd64"
```

Jobs run sequentially and stop on first failure. On Apple Silicon, containers run natively as arm64. Matrix jobs are limited to Python 3.13 by default to avoid Docker resource exhaustion.

`make lint-ci` lints the workflow files with `actionlint` (also runs as part of `make ci`).

### Makefile Targets

All CI is driven through `make`. No virtual environment required — tools run via `pipx`.

| Target | What it does | CI? |
|--------|-------------|-----|
| `make ci` | Run full CI locally via act (mirrors GitHub Actions) | — |
| `make lint-ci` | Lint GitHub Actions workflow files | — |
| `make test` | Run full test suite via `pipx run pytest` | Yes |
| `make test-verbose` | Tests with verbose output | — |
| `make test-quick` | Fast tests only (skip `@pytest.mark.slow`) | — |
| `make test-coverage` | Tests + coverage report (≥90% required) | Yes |
| `make validate` | Run `cpt validate` — deterministic artifact validation | Yes |
| `make self-check` | Validate SDLC kit examples against their own templates | Yes |
| `make check-versions` | Check version consistency across components | Yes |
| `make spec-coverage` | Check spec coverage (≥80% overall, ≥70% per file) | Yes |
| `make vulture` | Dead code scan (report only) | — |
| `make vulture-ci` | Dead code scan (fails on findings) | Yes |
| `make install` | Install pytest + pytest-cov via pipx | — |
| `make install-proxy` | Reinstall `cpt`/`cypilot` CLI from local source | — |
| `make update` | Sync `.bootstrap/` from local source | — |
| `make clean` | Remove `__pycache__`, `.pyc`, `.pytest_cache` | — |

### GitHub Actions

CI runs on every push to `main` and every PR targeting `main`. Seven parallel jobs:

1. **Test** — `make test` on Python 3.11, 3.12, 3.13, 3.14
2. **Coverage** — `make test-coverage` on Python 3.14 (≥90% gate)
3. **Vulture** — `make vulture-ci` dead code scan
4. **Versions** — `make check-versions` (proxy sync, bootstrap sync)
5. **Spec Coverage** — `make spec-coverage` (≥80% overall, ≥70% per file)
6. **Validate** — `make validate` + `make self-check` on Python 3.11–3.14
7. **Validate Kits** — `make validate-kits` on Python 3.11–3.14

All seven must pass before merge.

---

## Making Changes

### Code Changes

1. Edit files under `skills/cypilot/scripts/cypilot/` (skill engine) or `src/cypilot_proxy/` (CLI proxy)
2. Run `make update` to sync into `.bootstrap/.core/`
3. Add or update tests in `tests/`
4. Verify: `make test && make validate`

### Architecture / Spec Changes

1. Edit files under `architecture/` (PRD, DESIGN, DECOMPOSITION, features)
2. If adding new CDSL entries, run `cpt toc <file>` to regenerate the table of contents
3. If adding `@cpt-*` code markers, run `cpt validate` to verify traceability (138/138 coverage)
4. Verify: `make validate`

---

## Pull Request Process

1. Ensure all CI checks pass locally:
   ```bash
   make ci
   ```

2. Every commit is signed off (DCO):
   ```bash
   git commit -s -m "type(scope): description"
   ```

3. PR description should include:
   - What changed and why
   - Version bumps (if any)
   - Which `make` targets were run

4. For spec changes, include `cpt validate` output showing PASS status

---

## Code Style and Conventions

- **Zero third-party dependencies** — Python stdlib only (skill engine and proxy)
- **Python 3.11+** — use `tomllib`, `pathlib`, type hints
- **No comments or docstrings added/removed** unless explicitly requested
- **Existing code style** — follow patterns in surrounding code
- **Tests** — add tests for new functionality; never delete or weaken existing tests
- **Traceability** — new algorithms/flows in feature specs should have corresponding `@cpt-*` markers in code

---

## Questions?

Open an issue on GitHub or start a discussion. We're happy to help!
