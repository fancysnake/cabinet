---
name: resolve-conflict
description: >-
  Resolve a merge conflict keeping the intent of both sides. Use whenever a
  merge, rebase, cherry-pick or stash pop stops on conflicts, the user asks
  to resolve or fix conflicts, or a file carries conflict markers.
---

# Resolve conflict skill

A conflict is between work already on the base branch and work this branch
adds. Both were meant. The resolution keeps the intent of both.

1. **List the conflicted files**: `git status --short` shows them as `UU`,
   `AA`, `DU` or `UD`.
2. **Read both sides before choosing one.** For each file, read what each
   side changed and why: `git log --merge -p -- <file>` shows the commits of
   both sides that touch it. Picking one side whole is right only when the
   other side's change is already contained in it.
3. **Write the version both authors would accept.** Where one side renamed
   or moved what the other side edited, apply the edit at the new place.
   Where one side deleted what the other side edited, find out from the
   deleting commit whether the edit still has a home.
4. **Stage each resolved file** with `git add <file>`. Git counts a file as
   conflicted until it is staged, however clean its contents are.
5. **Check before finishing**: no conflict markers left
   (`git diff --check`), and the narrowest test or linter over each resolved
   file passes.

Do not run `git merge --abort` to escape a hard conflict, and do not finish
the merge until every file is staged. When an automation started the merge,
staging is where you stop: it finishes the merge itself.

cabinet's heal rituals carry these rules inline, in
`src/cabinet/mills/prompts.py`. A change to one belongs in the other.
