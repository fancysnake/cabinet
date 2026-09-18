# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

A [vekna](https://vekna.fancysnake.dev) **tome**: pull request maintenance
rituals (`refresh`, `cover`, `review`, `labels`) packaged under `src/cabinet`
and cast from other repositories via `vekna cast <ritual>`. The repo is also
a Claude Code plugin marketplace (`.claude-plugin/marketplace.json`) whose
plugins live under `plugins/<name>/` as skills only, no Python. README.md
holds the user-facing docs; keep it in step with code and config changes.

## Commands

Python 3.14 via mise; never call python tools directly, always `mise run`.
`mise tasks` lists everything. Task definitions come from the shared
`fancysnake/shared-configs` include in `mise.toml`, so `mise tasks info <task>`
shows what one actually runs.

```bash
mise run fullcheck            # the commit gate: format, lint, deptry, hk, tests + diff coverage
mise run test:unit            # tests/unit  (pure: mills, pacts)
mise run test:int             # tests/integration (links, rituals — via vekna's trial)
mise run test:py              # both
mise run test:unit -- tests/unit/mills/test_pulls.py -k wanted   # one file / one case
mise run lint:py              # every linter (black, ruff, mypy, pylint, vulture, import-linter, codespell, taplo)
mise run lint:mypy            # or lint:ruff, lint:import-linter, ... one at a time
mise run lint:tingle          # advisory: suppression debt vs main; not in fullcheck
vekna rituals show refresh    # draw a ritual's step graph
```

Tests use `pytest -n auto`; `.env.test` is loaded for test and mypy tasks.
The pre-commit hook (`hk`, installed by the mise enter hook) runs black,
ruff, codespell, taplo, yamllint, actionlint on staged files.

## Strictness

mypy runs fully strict including `disallow_any_expr`/`disallow_any_explicit`
(one override: `links/config/vekna_toml.py`). ruff selects `ALL`. tingle
counts every `noqa`, `type: ignore`, `pragma`, `cast`, `Any`, `object`
symbol use and `TODO` as debt against main. Fix the code rather than
suppress; a new suppression needs a comment saying why.

## Architecture: GLIMPSE layers

Layer import rules are enforced by import-linter contracts in `pyproject.toml`
(`mise run lint:import-linter`). Load the `glimpse` skill before adding or
moving modules.

| layer      | holds                                                         | may import               |
| ---------- | ------------------------------------------------------------- | ------------------------ |
| `pacts/`   | pydantic payloads, `Project` config, protocols (forge/scm/tasks/agent/services) | nothing internal |
| `specs.py` | numeric invariants (`BUDGET`, `VERDICT_LINES`, `WHOLE`)       | pacts                    |
| `mills/`   | pure logic: `Pulls`, `Verdicts`, `Prompts`, `Repairs`, `Report` | pacts, specs           |
| `links/`   | adapters: `forge/{github,gitlab}`, `scm/git`, `tasks/mise`, `agent/claude`, `config/vekna_toml` | pacts only; `links/*` subpackages independent of each other |
| `gates/`   | `@step` bodies (`gates/ritual/vekna/{sweep,review,labels,marking}.py`) | pacts only            |
| `inits/`   | `Services` binds concrete adapters, `wire()`                   | everything               |
| `rituals/` | one facade per ritual: the `@ritual` entrypoint + re-exported steps | layers; nothing imports it back |
| `edges/`   | reserved, empty, excluded from coverage                        | nothing                  |

### The services seam

vekna discovers steps by sweeping a module and routes by reference, so
nothing constructs a step and nothing can inject into one. Every step reaches
its collaborators through `services()` in `pacts/services.py`: a single slot
filled once by `bind()`. `rituals/__init__.py` imports `rituals/wiring.py`,
which calls `inits.services.wire()` at import, so the slot is bound before any
facade body runs, exactly once. Calling `wire()` from a facade is a bug (each
call discards the previous `Services` caches).

`Services.project()` reads `[cabinet]` from `.vekna.toml` at `Path.cwd()`;
`forge()` picks GitHub or GitLab from `project.forge`.

### Facades

`rituals/refresh.py` and `rituals/cover.py` both wrap the shared sweep steps
in `gates/ritual/vekna/sweep.py` and each re-export the **full** step list,
deliberately copied, because vekna registers only what it finds in the named
module's namespace. A new sweep step must be added to both `__all__` lists.
`rituals/review.py` wraps `gates/ritual/vekna/review.py`; `rituals/labels.py`
wraps `gates/ritual/vekna/labels.py`.

### Who runs what

Agents (`links/agent/claude.py`) run under `dontAsk` with per-role
allowlists (reader / writer / resolver, plus `project.agent.may_run`). Every
commit, push, task run and forge write is the ritual's own, through vekna's
`shell` medium in the `links` adapters. Keep it that way: no new agent
permission that commits, pushes, or talks to the forge.

## Tests

- `tests/unit/`: mills and pacts, plain pytest, no shell.
- `tests/integration/`: vekna's `trial` fixture (pytest plugin from
  `vekna[trial]`) walks steps with a scripted shell (`trial.shell.replies(...)`)
  and agent double. `tests/conftest.py` binds real `Services`, provides
  `project`, `pull`, `work`, `branch`, `here` fixtures and the `gh`/`git`
  command strings steps are expected to issue. `falling.py` swaps in an agent
  that dies, for the abort paths.
- A test asserts on transitions: `trial.walk(step, payload) == goto(next, payload)`.

## Config that is code

- `.vekna.toml`: this repo casting its rituals on itself; `[cabinet]` keys
  are validated by `pacts/project.py` (extra keys refused). A new setting
  means `Project` + `README.md` `[cabinet]` block + `CHANGELOG.md`.
- `CHANGELOG.md` is Keep a Changelog; user-visible changes go under
  `Unreleased`. The `release-bump` plugin skill cuts releases.
- `pyproject.toml` version and every `plugin.json`/`marketplace.json`
  version move together on release.
