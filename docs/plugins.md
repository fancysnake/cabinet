| `mkdocs-site`  | `mkdocs-site`  | sets up a MkDocs site, or upgrades one to the standard       |
| `mkdocs-site`  | `mkdocs-site`  | sets up a MkDocs site, or upgrades one to the standard       |
# Plugins

The repository is also a Claude Code plugin marketplace, named `cabinet`. Its
plugins live under `plugins/`, one skill each, and carry no Python: they are
the chores around a repository that are not worth a ritual, done by the agent
you already have open.

| plugin         | skill          | what it does                                                 |
| -------------- | -------------- | ------------------------------------------------------------ |
| `issue-maker`  | `issue-maker`  | files or updates a GitHub issue, checked against the code first |
| `release-bump` | `release-bump` | cuts a release: the version, the changelog, the docs         |
| `mkdocs-site`  | `mkdocs-site`  | sets up a MkDocs site, or upgrades one to the standard       |

Add the marketplace once, then install what you want:

```bash
claude plugin marketplace add fancysnake/cabinet
claude plugin install issue-maker@cabinet
claude plugin install release-bump@cabinet
claude plugin install mkdocs-site@cabinet
```

Or from inside a session: `/plugin marketplace add fancysnake/cabinet`, then
`/plugin install issue-maker@cabinet`.

The plugins are unversioned on purpose. A relative-path source in a git
marketplace resolves to the marketplace commit, so an install tracks the
commit and a skill never needs a version bump of its own. `claude plugin
marketplace update cabinet` brings the newest.

## issue-maker

Files or updates a GitHub issue in the current repository. It triggers on
"make an issue for this", "put that in the backlog", or any ask to file, open,
raise or write an issue or ticket about work that is not being done now.

What it does before touching the forge:

1. **Checks the task against the code.** A feature the code already has is
   dropped; one it half has comes back as a question about which parts are
   still wanted.
2. **Hunts duplicates** by keyword in the open issues, and asks what to do
   when it finds something close.
3. **Writes at feature level.** The issue may sit for months while the
   repository moves, so it names what gets added, fixed or changed in terms
   that survive a refactor: "needs a Trello API adapter", not a file path.
   Open questions and decisions are emphasised, and conceptual ambiguities
   are asked about; implementation details are not.
4. **Discovers the metadata the repository offers** and sets only what
   exists: labels, issue types, issue fields, the fields of a Project the
   issue should join. What is missing is reported in one line; nothing is
   created.

Where the repository has them, the issue gets the `backlog` label, an
`effort` and a `priority` field (priority is asked about), and an issue type
by what the work is: `feature` for something a user can see, `edit` for a
refactor with no feature change, `chore` for docs, CI, tooling and tests,
`spike` for an experiment that might not work, `bug` for behaviour that is
wrong. Types named differently get the nearest match.

Updating an existing issue loads it and uses it as the base; a contradiction
between what it says and what you asked is a question, not a guess.

Needs `gh` logged in. Setting Project fields needs the `project` token scope.

## release-bump

Cuts a release: bumps the version by semver from what changed since the last
tag, rewrites the `Unreleased` changelog section into tight entries, and
brings the docs and skills in line with the code. It triggers on any ask to
bump, release, tag, cut a version or update the changelog. It commits nothing
and tags nothing unless asked.

1. **Finds the last release** with `git describe --tags`. No tag means every
   commit counts. The unit of release is one manifest, the repository root's
   unless the request names another, plus whatever mirrors its version; a
   plugin or package elsewhere in the repository is its own release.
2. **Reads what changed** since the tag and sorts every change into a
   bucket: *break*, *feature*, *fix* or *internal*. An `Unreleased` entry
   already written is checked against the diff, because it is often stale.
3. **Chooses the version** strictly: any break is a major, else any feature a
   minor, else any fix a patch. Only internal changes means a patch, or a
   question whether a release is wanted at all. The bump and its reason are
   stated in one line before anything is edited.
4. **Writes the changelog** in [Keep a Changelog](https://keepachangelog.com/en/1.1.0/)
   form: `Unreleased` becomes the dated version section, an empty
   `Unreleased` goes above it, the link block at the bottom follows. Then
   every entry in the new section is compacted by deletion only: internal
   changes go unless the file already lists tooling, two commits for one
   feature become one entry, mechanism goes where the effect is named,
   puffery goes, and the concrete handle a reader will grep for stays in
   backticks.
5. **Brings docs and skills in line.** For every break, feature and
   user-facing fix, the README, `docs/`, skill files and help text are
   checked and corrected. Nothing the release did not add is added; a doc
   gap older than the release is a line in the report.
6. **Reports**: one line per file touched, the version line, and any change
   it could not classify with the question it raises. Staging, commit and
   tag stay with you.

Needs a `CHANGELOG.md` in Keep a Changelog form. Without one it says so and
stops rather than inventing one.

## mkdocs-site

Sets up a documentation site on MkDocs Material, or brings an existing one
up to one standard. It triggers on any ask to add docs, a manual or MkDocs
to a repository, to review, upgrade or standardise a `mkdocs.yml`, or to
publish docs to GitHub Pages. It commits nothing unless asked.

The standard is the one the fancysnake sites converge on, and the skill
carries it in full: a reference `mkdocs.yml` with every key explained,
a palette rule, the pages a manual has, the dependency, the tasks and the
Pages workflow.

1. **Reads the repository**: the stack (Python with poetry, or JS with
   aube and node; both are first class), whether a site exists, the name,
   license and site URL, and the prose that already lives in the README,
   the changelog or an example config.
2. **Writes or diffs the config.** `strict: true` and anchor validation in
   the file, so `mkdocs serve` fails the way the build does; the five
   markdown extensions every site uses and none it does not; `nav` as bare
   paths with titles from each page's H1; no `plugins` key unless one is
   added.
3. **Decides the palette** by what the project has: named Material colours
   and no CSS when it has none of its own, or two schemes named for the
   theme in `docs/stylesheets/<theme>.css` when it does, with the contrast
   ratio measured and the syntax colours set. `primary: custom` is the
   legacy form and gets migrated.
4. **Lays out the pages** and includes rather than copies: README sections
   through snippet markers, the changelog whole, an example config inside
   its fence. A page that restates what the code exposes gets a drift test.
5. **Declares the dependency, the tasks and the workflow**:
   `mkdocs-material` as an optional poetry group in a Python repo or a mise
   `pipx:` tool in a JS one, `site:dev` and `site:build` in both, and
   a `Site` workflow that builds on every pull request and deploys from
   `main` through the Pages artifact, actions pinned to a commit.
6. **Upgrades by table**: each legacy form found (`--strict` on the command
   line, `gh-deploy`, `docs:*` task names, `pip install` in CI, a pasted
   README) is mapped to its standard form; what the table does not name is
   kept.
7. **Verifies** with the build task and reports one line per file, the
   Pages setting to flip, and anything it had to assume.
