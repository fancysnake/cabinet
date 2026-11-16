---
name: cover-diff
description: >-
  Cover the lines a branch changed that no test exercises, with tests placed
  where the project's own layout puts them. Use whenever a diff coverage
  report or a coverage check names uncovered changed lines, or the user asks
  to cover the diff, raise diff coverage or add the missing tests for a
  branch.
---

# Cover diff skill

A diff coverage report names lines this branch changed that no test
exercises. Cover them with tests the project would have written itself.

1. **Read the project's testing guidelines before writing anything**:
   `CLAUDE.md` or `CONTRIBUTING.md`, and whatever testing documentation they
   point at. They say which kind of test each part of the code gets and where
   it lives.
2. **Open the nearest existing test** for the code the report names and
   match it: its directory, its fixtures, its naming, what it asserts on.
3. **Write a test for the behaviour, not for the line.** Each uncovered line
   is there for a case; the test exercises that case and asserts on its
   result. A test that only executes the line covers it and proves nothing.
4. **Put each test where the layout says it belongs.** Extend an existing
   test file before adding a new one.
5. **Check with the narrowest command**: the one test file you touched.

## What is not coverage

- lowering the coverage threshold
- editing the coverage configuration, or adding an exclusion comment
- deleting the uncovered code

A report from a fast measurement leaves the slow suites out, so a line only
a slow suite reaches appears as uncovered. Where that is what you find, say
so and leave the line alone.

cabinet's heal rituals carry these rules inline, in
`src/cabinet/mills/prompts.py`. A change to one belongs in the other.
