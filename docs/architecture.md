# Architecture

For anyone sending a patch. [GLIMPSE](https://glimpse.fancysnake.dev/)
layering under `src/cabinet`, enforced by import-linter:

```text
pacts/     contracts: payloads, the Project config, the forge/scm/tasks/agent protocols
specs.py   the numbers only a rule reads
mills/     pure logic: which pull requests, what a task said, what the agent is told
links/     adapters: forge/github, forge/gitlab, scm/git, tasks/mise, agent/claude, config
gates/     the @ritual and @step bodies, reaching everything through pacts
inits/     the one place the adapters are chosen and bound
rituals/   what vekna sweeps: one module per ritual, re-exporting its steps
```

| layer      | may import                                                     |
| ---------- | -------------------------------------------------------------- |
| `pacts/`   | nothing internal                                               |
| `specs.py` | pacts                                                          |
| `mills/`   | pacts, specs                                                   |
| `links/`   | pacts only; each `links/*` subpackage independent of the others |
| `gates/`   | pacts only                                                     |
| `inits/`   | everything                                                     |
| `rituals/` | the layers; nothing imports it back                            |

## The services seam

vekna discovers steps by sweeping a module and routes by reference, so nothing
constructs a step and nothing can inject into one. Every step reaches its
collaborators through `services()` in `pacts/services.py`: a single slot
filled once by `bind()`. Importing `cabinet.rituals` wires it, exactly once,
before any facade body runs.

`Services.project()` reads `[cabinet]` from `.vekna.toml` at the current
directory; `forge()` picks GitHub or GitLab from `project.forge`.

## Facades

`rituals/refresh.py` and `rituals/cover.py` both wrap the shared sweep steps
and each re-export the full step list, deliberately copied, because vekna
registers only what it finds in the named module's namespace. A new sweep
step is added to both.

## Development

Python 3.14 via mise; `mise tasks` lists everything.

```bash
mise run test:py       # the suite
mise run lint:py       # every linter
mise run fullcheck     # the gate before a commit
mise run site:dev      # this site, with live reload
vekna rituals show refresh
```

- `tests/unit/`: mills and pacts, plain pytest, no shell.
- `tests/integration/`: vekna's `trial` fixture walks steps with a scripted
  shell and an agent double. A test asserts on transitions:
  `trial.walk(step, payload) == goto(next, payload)`.

mypy runs fully strict, ruff selects `ALL`, and tingle counts every
suppression as debt against main. Fix the code rather than suppress.

## This site

`.github/workflows/site.yml` builds `docs/` on every pull request and
publishes it on a push to `main`. `strict: true` in `mkdocs.yml` fails that
build on a link to a page that is not there. Pages is sourced from the
workflow rather than from a branch, so the custom domain is a repository
setting — a `CNAME` file in `docs/` would be copied into the artifact and
ignored.
