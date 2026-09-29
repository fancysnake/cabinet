---
name: issues
description: >-
  How issues are written, typed, sized and linked in this repo. Use whenever
  the user asks to file, open, create, write, or raise an issue or ticket,
  says "make an issue for this" / "put that in the backlog" about work that
  won't be done now, or asks to refine, triage, type, size, split or
  link issues or the backlog. Also what cabinet's `refine` ritual hands its
  agent.
---

# Issues skill

Everything below is GitHub through `gh` unless it says GitLab; `glab` does
the same where a GitLab line is given.

## Types

One per issue, as a label of the same name (`vekna cast labels:issue` makes
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
3. Write at feature level: the issue may sit for months while the repo moves.
   - Cover the features added, the bugs fixed and the operations changed.
   - Generic terms are fine: "needs a Trello API adapter", "a new view",
     "refactor the enrollment mill".
   - Use bullets and sections, and emphasize open questions and decisions.
   - Ask about conceptual ambiguities, not implementation details.
   - When updating an issue, start from its current body and ask about
     contradictions.
4. Set what the repo offers, create nothing, and report what is missing in one
   line:
   - type and size labels, as above;
   - `backlog` and a priority label (`P1`–`P3`) where they exist, asking the
     user for the priority;
   - issue fields or Project fields where they exist. Discover them with
     `gh label list`, `issueTypes` / `issueFields` over `gh api graphql`, and
     `gh project field-list`.

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

## Refining a backlog

For each issue, set one type, then one size or `epic`, then the links, and
nothing else. Do not close, delete or retitle anything, and do not remove a
label you did not add. Give a sub-issue you open a type and a size in the same
breath, so it is not left behind unrefined.
