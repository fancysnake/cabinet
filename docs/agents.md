# Agents

Every agent call in a ritual is one bounded piece of work: resolve this
conflict, make this task pass, write tests for these lines, answer this
thread. Every agent has a shell, and cabinet denies it no command.

## Run every cast in a sandbox

A shell can run anything: `mise exec` or `sh -c` gets round any list of
command prefixes. The boundary is the sandbox the cast runs in, such as
fence. Run every cast, attended or not, inside one.

## Permission modes

Unattended, every agent call runs under Claude's `dontAsk` permission mode,
so a cast at 3am never hangs on a prompt. Attended — `review` always, the
sweeps with `--attended true` — the mode is `auto`, with somebody there to be
asked.

## Roles

| role   | may use                               |
| ------ | ------------------------------------- |
| reader | `Read`, `Grep`, `Glob`, `Bash`        |
| writer | reader + `Edit`, `Write`, `MultiEdit` |

A reader gets no edit tools, but it is not read-only: its shell writes. The
role says what the call is for.

## What the ritual owns

The ritual commits, pushes and runs the long tasks, and makes every forge
call through vekna's `shell` medium in the `links` adapters, including
`identify`'s labels, sub-issues and links. Its agent reads the backlog and
hands back what each issue is, and the ritual puts that on. After every
repair attempt the ritual re-runs the task the runner named as broken and
hands the agent the output. The prompt tells the agent all this.

## `may_not_run`

An agent that runs one test file, or one linter over one file, before it
stops makes an attempt more likely to count. An agent that runs a sweep
spends minutes on an answer the ritual is about to give it. So the prompt
names the long tasks and asks the agent to leave them alone: the project's
`gate`, `coverage` and `fast_coverage`, and every prefix in `may_not_run`:

```toml
[cabinet.agent]
may_not_run = ["mise run lint:py", "mise run test:py"]
```

The list is advice in the prompt, not a lock.
