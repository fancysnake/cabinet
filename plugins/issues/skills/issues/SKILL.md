---
name: issues
description: >-
  How issues are written, typed, sized and linked in this repo. Use whenever
  the user asks to file, open, create, write, or raise an issue or ticket,
  says "make an issue for this" / "put that in the backlog" about work that
  won't be done now, or asks to refine, triage, type, size, split or
  link issues or the backlog. Also what cabinet's `identify` ritual hands its
  agent.
---

# Issues skill

Everything below is GitHub through `gh` unless it says GitLab; `glab` does
the same where a GitLab line is given.

## Types

One per issue, as a label of the same name (`vekna cast labels.identify` makes
them). Where the repo also has GitHub issue types, set the matching one too.

- **feature**: new functionality the user can see, such as a page, an option
  or a capability.
- **edit**: a refactor or improvement to production code, with no change in
  features.
- **chore**: no production code: docs, deployment, CI, repo hygiene, dev
  tooling, tests, observability.
- **spike**: an investigation or experiment that might not work.
- **bug**: something doesn't behave as expected.

## Sizes

One per issue, as a label: what the change costs in the repo as it stands. Read
the code it touches before judging.

- **S**: one module, done in a single sitting.
- **M**: several modules, or one new adapter or page; one PR.
- **L**: crosses layers, but still one reviewable PR.
- **epic** (label, instead of a size): more than one PR, or several parts that
  could each ship on their own. The epic keeps its type and gets no size.
  Split it into sub-issues, each typed and sized, and attach each under the
  epic. Where existing open issues are already parts of it, attach those
  instead of opening duplicates.

## Writing an issue

1. Validate the task against the current code. If it is already implemented,
   drop it. If it is partly done, say what is left and ask which parts still
   matter.
2. Search the open issues by keyword (`gh issue list --search "<words>"`). If
   something similar exists, ask what to do.
3. Write the body as a STAGE or a Slice (see [Bodies](#bodies)), never a
   plan. Ask about conceptual ambiguities, not implementation details.
4. Set what the repo offers, create nothing, and report what is missing in one
   line:
   - type and size labels, as above, and `shape` on a shape-changing issue;
   - `backlog` and a priority label (`P1`–`P3`) where they exist, asking the
     user for the priority;
   - issue fields or Project fields where they exist. Discover them with
     `gh label list`, `issueTypes` / `issueFields` over `gh api graphql`, and
     `gh project field-list`.

   This step is the interactive path, where you run `gh` yourself. Under
   cabinet's `identify` you reach no forge client at all: name the type, the size
   and the links in your answer and the ritual puts on what it can.

## Bodies

An issue says why and what done looks like, never how. Name no files,
classes or APIs, so the body stays true while the code moves. The one
exception is a bug's observed error text, quoted as it appeared. There is no
solution section: the design is written when the work starts, as interfaces,
a spike or tests.

A **STAGE** is the body of any issue that ships on its own: a standalone
issue, an epic, or a feature-sized part of an epic. A sub-issue's Target
opens with one sentence on how it serves its parent. A STAGE holds Status
(the situation now), Target (the outcome once done), Assets (what already
exists to reuse or copy), Guards (no-gos) and Ellipsis (open questions).
Fill every field and keep it under 15 lines of content; headings and blank
lines do not count.

Status and Target split by tense. Status is the present: the situation and
why it hurts now. Target is the future: what is true once the work lands,
with no word on how things are today. A sentence about today in Target
belongs in Status.

- **bug**: Status is how to reproduce it and what happens; Target is what
  should happen instead.
- **spike**: Target's done is the question answered, whichever way.

Assets are hints, not a guide. Mention, in a few words, what the code already
has that the work can use (a mailer, for a newsletter) or that does something
similar to copy (the existing CRUD views, for a new one). Say what it is, not
where: no names, modules or lines, which rot as soon as they are written.
Write "none known" when nothing fits.

```markdown
## Status (the situation now)
When <situation>, <what happens now, and why it hurts>.

## Target (the outcome, once done)
<what is true once this lands>
Done looks like: <one observable sentence>

## Assets (what exists to reuse or copy)
- use: <something that exists, e.g. "a Discord integration">
- like: <a similar feature, e.g. "the other CRUD views">

## Guards (what this will not do)
- <a no-go>

## Ellipsis (open questions)
- <unknowns and rabbit holes; any solution hunch marked non-binding>
```

A **Slice** is the body of a step that does not ship on its own, such as
plumbing or one part of a split M or L issue. It matters only through its
parent:

```markdown
## Serves parent because
<one sentence tying this step to the parent's intent>

## Done when
<one observable sentence>
```

A STAGE or Slice that changes the shape of the system wears the `shape`
label: it goes to the user, who writes its spine, spike or acceptance tests
first. One without it can go straight to an agent. Under `identify`, say `shape` in your
answer and the ritual puts the label on.

The fields are the user's. On an existing issue you may comment, append to
Ellipsis, and append link lines (`Part of #<n>`, `Related: #<n>`); never
rewrite the other fields. When the intent changes, open a new issue and say
which one it replaces, rather than editing the old one into it.

## Links

Link only real relationships. Each wrong link is noise that someone has to
undo.

- **Sub-issue**: this issue is a part of that epic.
  - GitHub: `gh api -X POST repos/{owner}/{repo}/issues/<epic>/sub_issues -F sub_issue_id=<id>`.
  - GitLab: `glab api -X POST projects/:id/issues/<epic>/links -f target_project_id=<project> -f target_issue_iid=<n> -f link_type=relates_to`.
    Also put `Part of #<epic>` in the body: epics and child items are
    GitLab Premium, and a link is what every tier has.
- **Blocked by**: this one cannot start until that one lands. Use it only
  when the order is real.
  - GitHub: `gh api -X POST repos/{owner}/{repo}/issues/<n>/dependencies/blocked_by -F issue_id=<id>`.
  - GitLab: link with `link_type=is_blocked_by`.
- **Related**: add a line to the body, `Related: #<n>`. Neither forge has a
  plain relation that is worth the noise.
- **Duplicate**: say so in a comment on the newer issue
  (`gh issue comment <n> --body "Looks like a duplicate of #<m>"`). Never close
  it.

`<id>` in a GitHub REST call is the issue's database id, not its number:
`gh api repos/{owner}/{repo}/issues/<n> --jq .id`. `gh api` fills in
`{owner}` and `{repo}` itself.

## Identifying a backlog

For each issue, set one type, then one size or `epic`, then `shape` where it
changes the shape of the system, then the links, and nothing else. Do not
close, delete or retitle anything, and do not remove a label you did not add.
Give a sub-issue you open a type and a size in the same breath, so it is not
left behind unrefined.

Under cabinet's `identify` ritual you only read: say what each issue is and what
should be opened, labelled and linked, and the ritual makes every one of those
calls itself.
