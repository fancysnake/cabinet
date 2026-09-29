---
name: smoke-test
description: >-
  Write the fifteen-minute manual check for a change that is already on
  staging: the shortest path through the browser, or a Django command when
  there is no web part, that proves the change works, plus the untouched
  features it could have broken. Use whenever the user asks what to click,
  how to check a change on staging, for a smoke test, a quick QA pass, or
  the minimal manual test before merging or releasing.
---

# Smoke test skill

The change is deployed on staging. Migrations ran, the deploy went through,
the site loads; none of that gets a step. The tester is the developer who
wrote the change, with a browser, a shell and fifteen minutes. The output is
the shortest path that proves the change works and the neighbours it could
have knocked over. Not a test plan, not a checklist of acceptance criteria.

## 1. Read the change

- Base, in order: what the request names (a branch, a tag, a ref); else the
  ref the last deploy went out on (`origin/staging`, the release tag,
  whatever the deploy leaves behind); else where the change left the base
  branch — `git merge-base main <branch>`, or the merge commit's first
  parent (`HEAD^1`) when there is one. Never `HEAD~1`: a fast-forwarded
  three-commit branch diffs as one commit, and the path then gets written
  for a third of the change.
- `git diff --stat <base>` first, the diff itself second, `git status` for
  uncommitted work.
- Sort each file: **web** (views, urls, templates, forms, JS, CSS),
  **command** (management commands, tasks, cron entries), **data** (models,
  migrations, signals, fixtures), **plumbing** (settings, middleware,
  dependencies, CI, tests). Plumbing gets no step of its own unless it
  changes what runs in production: a setting, a middleware, an upgraded
  library.
- Read enough surrounding code to name the entry point: the URL, the
  button, the command and its flags. Stop there.

## 2. Pick the surface

- **Browser first.** A URL to open, a form to submit, a button to press,
  and the admin as the fastest way to look at a row.
- **No web part** → the management command with its flags, or a
  `manage.py shell` one-liner that runs the code path and prints the
  result. Say what it prints when it works.
- **Mail, files, jobs** → the staging mailbox, the download, the task
  runner's log or the row it leaves behind.
- Never: migrations, static files, restarts, a unit test, "the site
  loads", anything the deploy already proved.

## 3. Write the path

- One path per changed behaviour: the thing the change was made for, done
  once, end to end. Where the diff adds a guard (a permission, a validation,
  an empty state) poke it once; do not enumerate every wrong input.
- Each step is where to go, what to do, what to look for. The tester knows
  the app: name the URL, the field and the row or message, and skip the
  clicks in between. Setup goes inline ("as an organiser, on an event with
  one slot"), and data that has to exist on staging is named in the step
  that needs it.
- Fifteen minutes in total. Over budget: drop guard pokes first, then
  neighbours the diff makes unlikely to break. The happy path is never cut.
- A step that takes more than a minute is two steps.

## 4. Add the neighbours

Features the diff does not touch but could have broken. One step each, one
action each; the question is "still works", not "unchanged".

Bounded by blast radius, like the path itself: a full-app regression pass is
a different exercise and does not fit fifteen minutes.

| the change touched                    | check                                                             |
| ------------------------------------- | ----------------------------------------------------------------- |
| a base template, shared CSS or JS     | one other page that includes it                                   |
| a model, field or migration           | a page that lists or creates the object, and its admin page       |
| a URL or a redirect                   | the sibling route, the old URL if one was replaced                |
| login, signup, permissions            | the old flow, an anonymous hit, one other role                    |
| a signal, middleware or setting       | one page that has nothing to do with the feature                  |
| a management command                  | whatever schedules it or consumes what it writes                  |
| a dependency upgrade                  | the busiest page that uses the library, and one touching what its changelog changed |
| a form                                | one other form that shares its widgets or base class              |

## 5. Report

```markdown
# Smoke test: <branch> on staging

<one line: what the change does>

## Path (~N min)

1. <where> → <do> → <look for>
2. ...

## Neighbours

- <feature> → <one action> → still works

## Skipped

- <what you left out and why>
```

"Works" means the page renders, the action lands, the row exists, the mail
arrives. Not pixel position, not copy, not layout. Quote expected text only
when the text is the feature. `Skipped` is for cuts made for the budget and
for paths that need data staging does not have; leave it out when empty.
