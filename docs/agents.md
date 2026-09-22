# Agents

Every agent call in a ritual is one bounded piece of work: resolve this
conflict, make this task pass, write tests for these lines, answer this
thread. What the agent may touch while doing it is fixed by its role, and
nothing the prompt says can widen it.

## Permission modes

Unattended, every agent call runs under Claude's `dontAsk` permission mode
with an explicit allowlist, so a cast at 3am never hangs on a prompt and
nothing outside the list happens whatever the prompt says.

Attended — `review` always, the sweeps with `--attended true` — the mode is
`auto`: the allowlist still approves what it names, and what falls outside it
is judged rather than refused. Run attended casts inside a sandbox such as
fence, where an approved mistake cannot reach anything that matters.

## Roles

| role     | may use                                                                 |
| -------- | ----------------------------------------------------------------------- |
| reader   | `Read`, `Grep`, `Glob`, `git diff/log/show/status/blame`                |
| writer   | reader + `Edit`, `Write`, `MultiEdit` + every prefix in `agent.may_run` |
| resolver | writer + `git add` (staging is how a conflict is reported resolved)     |

No agent commits, pushes, runs a linter or a sweep, or speaks to the forge.
The ritual does all of that itself through vekna's `shell` medium, and after
every repair attempt it re-runs the task the runner named as broken and hands
the agent the output.

## `may_run`

`may_run` is for the narrow, quick commands you want an agent to check itself
with — a single test, say. Each prefix becomes a `Bash(<prefix>:*)` allowlist
entry, so what the prompt quotes and what the SDK permits are the same list:

```toml
[cabinet.agent]
may_run = ["mise run test:unit", "mise run test:int"]
```

Keep the linters and the sweeps out of it. Those are the ritual's, and running
them is how it decides whether the agent's attempt counted.
