# Plugins

The repository is also a Claude Code plugin marketplace, named `cabinet`. Its
plugins live under `plugins/`, one skill each, and carry no Python: they are
the chores around a repository that are not worth a ritual, done by the agent
you already have open.

| plugin         | skill          | what it does                                                 |
| -------------- | -------------- | ------------------------------------------------------------ |
| `issues`       | `issues`       | how issues are written, typed, sized and linked; what `refine` follows |
| `release-bump` | `release-bump` | cuts a release: the version, the changelog, the docs         |
| `mkdocs-site`  | `mkdocs-site`  | sets up a MkDocs site, or upgrades one to the standard       |

--8<-- "README.md:plugins-install"

The plugins are unversioned on purpose. A relative-path source in a git
marketplace resolves to the marketplace commit, so an install tracks the
commit and a skill never needs a version bump of its own. `claude plugin
marketplace update cabinet` brings the newest.

## issues

What an issue is in this repository: how one is written, which type and size
it gets, when it becomes an epic, and how issues are linked. Knowledge only:
it triggers on "make an issue for this", "put that in the backlog", any ask to
file, open, raise or write an issue or ticket, and any ask to refine, type,
size, split or link the backlog. The [`refine`](rituals.md#refine) ritual has
its agent read it too, from `refine_skill`.

1. **Types**: `feature` for something a user can see, `edit` for a refactor
   with no feature change, `chore` for docs, CI, tooling and tests, `spike`
   for an experiment that might not work, `bug` for behaviour that is wrong.
   Each is a label, and also a GitHub issue type where the repository has
   them.
2. **Sizes**: `S` is one module in a single sitting, `M` is several modules
   or one new adapter or page, `L` crosses layers but is still one reviewable
   pull request. Anything bigger is an **epic**: the `epic` label in place of
   a size, split into sub-issues that are each typed, sized and attached under
   it.
3. **Writing one**: the task is checked against the code first, duplicates are
   searched for by keyword, and the issue is written at feature level so it
   survives the repository moving on. Conceptual ambiguities are asked about;
   implementation details are not. `backlog`, a priority and any issue or
   Project fields are set where the repository has them, and nothing is
   created.
4. **Links**: sub-issue for a part of an epic, blocked-by only when the order
   is real, a `Related: #n` line otherwise. A likely duplicate is named in a
   comment, never closed. On GitLab, whose epics are Premium, parts are linked
   and named in the body.

`vekna cast labels:issue` makes the type, size and epic labels. Needs `gh`
(or `glab`) logged in; setting Project fields needs the `project` token scope.

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
