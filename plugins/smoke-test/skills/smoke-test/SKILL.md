---
name: smoke-test
description: >-
  Write the fifteen-minute manual check for a change: the shortest path that
  proves it works where users meet it — staging or a production preview for
  a web app, the installed build for a CLI or package — plus the untouched
  features it could have broken. Use whenever the user asks what to click or
  run, how to check a change on staging, for a smoke test, a quick QA pass,
  or the minimal manual test before merging or releasing.
---

# Smoke test skill

The tester is the developer who wrote the change, with a browser, a shell and
fifteen minutes. The output is the shortest path that proves the change works
where users meet it, and the neighbours it could have knocked over. Not a test
plan, not a checklist of acceptance criteria.

## 1. Read the change

- **Kind**, settled here and carried: the target (step 2), the surface
  (step 3) and which neighbour rows apply (step 5) all follow from it, and
  none of them asks again.
  - **Web** — users meet the change in a browser: routes, views, templates,
    pages, components.
  - **CLI or package** — they meet it in a shell, through an installed
    build: commands, flags, output, exit codes, a library's public API.
  - **Neither** — no surface of its own; a code path other code reaches.

  A repo that ships both takes the kind of the change, not of the repo.
- **Base**, in order: what the request names (a branch, a tag, a ref); else
  the ref the last deploy or release went out on (`origin/staging`, the
  latest tag, whatever the deploy leaves behind); else where the change left
  the base branch — `git merge-base main <branch>`, or the merge commit's
  first parent (`HEAD^1`) when there is one. Never `HEAD~1`: a
  fast-forwarded three-commit branch diffs as one commit, and the path then
  gets written for a third of the change.
- `git diff --stat <base>` first, the diff itself second, `git status` for
  uncommitted work.
- Sort each file:
  - **entry points**: what a user touches. Routes, views, templates, pages,
    components, JS, CSS; CLI commands, flags, arguments, output, exit codes;
    config keys users write; a library's public API.
  - **jobs**: background tasks, scheduled or management commands, hooks, a
    CI action the project ships.
  - **data**: models, migrations, schemas, on-disk formats, caches, state
    files.
  - **plumbing**: settings, middleware, dependencies, packaging, CI, tests.
    No step of its own unless it changes what runs or ships: a setting, a
    middleware, an upgraded library, an entry point, package data.
- Read enough surrounding code to name the entry point: the URL, the button,
  the command and its flags. Stop there.

## 2. Pick the target

Where the change runs as users will meet it, by the kind from step 1. Read
the deploy and release workflows and the task runner (`mise tasks`,
`package.json` scripts) to find it; the dev checkout is never the target.

- **Web, with staging** → staging. Migrations ran, the deploy went through,
  the site loads; none of that gets a step.
- **Web, no staging** (deployed straight from `main`) → the production build
  served locally: the project's build task, then its preview task. Not the
  dev server; it hides build-only breaks.
- **CLI or package** → the build installed the way users install it, in a
  throwaway environment outside the checkout: `uv tool install dist/*.whl`
  or `pipx install` for Python, `npm pack` then `npx` from a scratch
  directory for Node, or the consumer example the repo ships. Running from
  the dev environment hides missing package data and broken entry points.
- **Neither** → whichever of those the project ships; the code path is
  reached from there.

Setting up a target the deploy did not already set up is step 0 of the path:
one line, the commands, and the acceptance that ends it — the bare command
runs and exits 0, the preview serves the page. Step 0 sits outside the
budget and outside the one-minute rule; a build and an install are machine
wait, and the budget measures the tester's attention.

## 3. Pick the surface

The medium the test is driven through, by the kind from step 1.

- **Web** → browser first. A URL to open, a form to submit, a button to
  press; the framework's admin, if it has one, as the fastest look at a row.
- **CLI or package** → the command with its flags, run in a scratch fixture
  it needs ("in a fresh git repo with one commit", "on a directory with two
  songs"). Say what it prints and the exit code when it works.
- **Neither** → a one-liner that runs the code path and prints the result:
  `manage.py shell -c`, `python -c`, `node -e`. Say what it prints.
- **Side effects**, any kind → where they land: the staging mailbox, the
  file written, the log, the row, the commit made, the comment posted.
- Never a step for what the deploy or step 0 already proved — migrations,
  static files, restarts, "the site loads", the bare command exiting 0 —
  and never a unit test. The ban reaches exactly that far: an install does
  not prove an entry point resolves, which is why that check is step 0's
  acceptance line rather than something forbidden.

## 4. Write the path

- One path per changed behaviour: the thing the change was made for, done
  once, end to end. Where the diff adds a guard (a permission, a validation,
  an empty state, a refused flag) poke it once; do not enumerate every wrong
  input.
- Each step is where to go, what to do, what to look for. The tester knows
  the app: name the URL, the field, the command, and the row, message or
  output line, and skip the clicks in between. Setup goes inline ("as an
  organiser, on an event with one slot"), and data that has to exist is
  named in the step that needs it.
- Fifteen minutes in total, step 0 not counted. Over budget: drop guard
  pokes first, then neighbours the diff makes unlikely to break. The happy
  path is never cut.
- The happy paths alone over budget: split into two runs, or call the change
  too broad for one smoke test — cover the behaviours that carry it, and
  name in `Skipped` both what got covered and what did not.
- A step that takes more than a minute is two steps. Step 0 is exempt.

## 5. Add the neighbours

Features the diff does not touch but could have broken. One step each, one
action, or two where a row names a second; the question is "still works",
not "unchanged". The second check is the weaker one — it goes first when the
budget bites.

Bounded by blast radius, like the path itself: a full regression pass is a
different exercise and does not fit fifteen minutes.

Any kind:

| the change touched                    | check                                                             |
| ------------------------------------- | ----------------------------------------------------------------- |
| a model, schema or migration          | a place that lists or creates the object, or its admin page if there is one |
| an on-disk format or state file       | reading one the last release wrote                                |
| a signal, middleware, hook or setting | one feature that has nothing to do with the change                |
| a job or scheduled command            | whatever schedules it or consumes what it writes                  |
| a dependency upgrade                  | the busiest place that uses the library, and one touching what its changelog changed |
| a helper that shells out (git, gh, …) | one other caller that goes through the same helper                |

Web:

| the change touched                    | check                                                             |
| ------------------------------------- | ----------------------------------------------------------------- |
| a base template, layout, shared CSS or JS | one other page that includes it                               |
| a URL, route or redirect              | the sibling route, or the old URL if one was replaced             |
| login, signup, permissions            | the old flow, and an anonymous hit or one other role              |
| a form                                | one other form that shares its widgets or base class              |

CLI or package:

| the change touched                    | check                                                             |
| ------------------------------------- | ----------------------------------------------------------------- |
| the argument parser or a shared option | one other subcommand                                             |
| an output renderer or exit codes      | one other command using it, and the machine-readable form if there is one |
| config loading or a config key        | a run with the project's real config, and one with none           |
| packaging: entry points, package data | the command that reads the packaged file, in the fresh install    |

## 6. Report

```markdown
# Smoke test: <branch> on <target>

<one line: what the change does>

## Path (~N min, setup not counted)

0. <setup, only when the target needs it> → <it runs and exits 0>
1. <where> → <do> → <look for>
2. ...

## Neighbours

- <feature> → <one action, or two> → still works

## Skipped

- <what you left out and why>
```

"Works" means the page renders, the action lands, the row exists, the mail
arrives, the command exits 0 and prints the line, the file appears. Not
pixel position, not copy, not layout, not every byte of output. Quote
expected text only when the text is the feature. `Skipped` is for cuts made
for the budget and for paths that need data the target does not have; leave
it out when empty.
