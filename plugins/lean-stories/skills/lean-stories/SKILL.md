---
name: lean-stories
description: Write lean one-line user stories ("As a X, I want Y, so that Z") and hunt for loopholes, edge cases, abuse paths, missing actors and conflicting rules. Use when the user asks for user stories, wants a feature broken into stories, or asks what could go wrong, where the gaps are, or which edge cases or loopholes a feature or requirement has.
argument-hint: [feature description or path to a spec]
---

# Lean Stories

Stories are one line. The value is in the gaps you find. Spend most of your effort on probing, not on formatting.

## Input

Work from `$ARGUMENTS`, a file the user points to, or the conversation. Where the feature is too vague to name an actor and a goal, write the stories you can name and put the rest under **Open questions**, each with a recommended answer.

## Step 1: Write the stories

One line each:

> As a **[specific actor]**, I want **[concrete goal]**, so that **[real benefit]**.

Rules:
- Name a real actor ("first-time buyer", "billing admin"). Never use "As a user".
- The "so that" must state a benefit, not restate the goal.
- Write one goal per story. If the goal joins two separate actions, split it.
- Cover only what the feature needs. Don't pad with generic stories.

## Step 2: Sweep for actors

List who touches this feature, including the ones that are easy to forget:
- unauthenticated visitor
- admin, support, or other operator
- an external system or integration

If an actor has no story but plausibly matters, list it under **Missing actors**.

## Step 3: Probe each story

Run every story through these lenses. Keep only findings that are plausible and would change behavior. Don't record findings just to fill in every lens.

1. **Boundaries:** min, max, zero, one, limit and limit + 1, pagination, size, time.
2. **Bad input:** empty, null, duplicate, malformed, wrong type, special characters or unicode.
3. **Unhappy paths:** failure, timeout, retry, partial completion, recovery.
4. **State and timing:** concurrency, double submit, stale data, an action taken mid-transition, expiry.
5. **Permissions and ownership:** who can do this, on whose data, and what happens after a role changes.
6. **Abuse and misuse:** gaming the rule, enumeration, cost or rate abuse, privilege escalation, using the feature against another user.
7. **Conflicting rules:** this story against another story, an existing policy, or itself.
8. **Ambiguous terms:** "fast", "recent", "valid", "active". Who defines them, and as what?
9. **Lifecycle:** undo, edit, delete, data retention, and what happens to dependent data.

For deeper probing questions on any lens, read `reference.md`.

## Step 4: Output

Use this format exactly. Add nothing else unless the user asks for it.

```
## Stories

### S1. As a [actor], I want [goal], so that [benefit].
- [Abuse and misuse] <finding in one line>
- [Boundaries] <finding>
- [Conflicting rules] <finding: name the rule or story it conflicts with>
Also consider: <overflow findings, one line>

### S2. ...

## Missing actors
- <actor>: <why they matter>

## Open questions
1. <question>
   Recommended: <your suggested answer, with a short reason>
2. ...
```

The findings under S1 are examples, not a fixed set. Tag each finding with the name of the lens that found it.

Limits:
- At most 7 findings per story, ranked by likelihood × impact.
- Put any beyond 7 on the "Also consider" line; leave the line out when there are none.

## Rules

- **Don't invent answers.** When the behavior is unknown, turn it into an open question with a recommended answer. The user makes the decision.
- **Don't add scaffolding.** Leave out epics, story points, priorities, personas, and definitions of done.
- **Given/When/Then is opt-in.** Write it only if the user asks, and then only for the riskiest findings.
- **Iterate.** When the user answers open questions, update the stories and findings, re-probe the stories that changed, then re-run the Conflicting rules lens across all stories.
