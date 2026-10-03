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
rituals/   what vekna loads: one module per ritual, re-exporting its steps
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

vekna registers a step when it is decorated and routes by payload class, so
nothing constructs a step and nothing can inject into one. Every step reaches its
collaborators through `services()` in `pacts/services.py`: a single slot
filled once by `bind()`. Importing `cabinet.rituals` wires it, exactly once,
before any facade body runs.

`Services.project()` reads `[cabinet]` from `.vekna.toml` at the current
directory; `forge()` picks GitHub or GitLab from `project.forge`.

## Payloads are the graph

A step returns the next step's payload, or `Done(result)`, and its return
annotation names every exit. vekna routes by the payload's exact class, so
every step has a class of its own, named for it and adding no fields:
`SetAside(Work)` in `pacts/sweep.py`, `Pick(Picking)` in `pacts/review.py`,
`Leaf(Identifying)` in `pacts/identify.py`.
`payload.to(NextStep)` rebuilds one as another — one `to` per carrier, taking
only that carrier's own steps — and mypy checks every `return` against the
annotation.

## Facades

`rituals/refresh.py` and `rituals/cover.py` both wrap the shared sweep steps
and each re-export the full step list, so importing either registers the whole
graph. A new sweep step is added to both.

## Development

Python 3.11 through 3.14 via mise; `mise tasks` lists everything.

--8<-- "README.md:development"

- `tests/unit/`: mills and pacts, plain pytest, no shell.
- `tests/integration/`: vekna's `trial` fixture walks steps with a scripted
  shell and an agent double. A test asserts on transitions:
  `trial.walk(step, work.to(Step)) == work.to(Next)`.

mypy runs fully strict, ruff selects `ALL`, and tingle counts every
suppression as debt against main. Fix the code rather than suppress.

## This site

`.github/workflows/site.yml` builds `docs/` on every pull request and
publishes it on a push to `main`. `strict: true` in `mkdocs.yml` fails that
build on a link to a page that is not there. Pages is sourced from the
workflow rather than from a branch, so the custom domain is a repository
setting — a `CNAME` file in `docs/` would be copied into the artifact and
ignored.
