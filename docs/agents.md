# Agents

Every agent call in a ritual is one bounded piece of work: resolve this
conflict, make this task pass, write tests for these lines, answer this
thread. Every agent has a shell, and cabinet denies it no command.

## The sandbox is the only boundary

A shell can run anything: `mise exec` or `sh -c` gets round any list of
command prefixes. Nothing bounds paths either: `Read`, `Grep` and `Glob` reach
any file the user can read. The prompts that carry other people's text
(review threads, issue bodies) fence it as untrusted and ask the agent to stay
in the repository, but a prompt is an instruction, and the text it fences is
written by other people.

The sandbox the cast runs in, such as
[fence](https://github.com/fencesandbox/fence), is what bounds both the paths an
agent reaches and the commands it runs. Run every cast, attended or not, inside one.

## Permission modes

A cast is attended unless it runs under `vekna cast --unattended`, with
`--attended false`, or under `[defaults."cabinet:<ritual>"] attended = false`
in `.vekna.toml`. Attended, the mode is `auto`, with somebody there to be
asked. Unattended, every agent call runs under Claude's `dontAsk` permission
mode, so a cast at 3am never hangs on a prompt. A cron job must pass
`--unattended`, or its agents run in `auto` with nobody to answer.

## Roles

| role   | may use                               |
| ------ | ------------------------------------- |
| reader | `Read`, `Grep`, `Glob`, `Bash`        |
| writer | reader + `Edit`, `Write`, `MultiEdit` |

A reader gets no edit tools, but it is not read-only: its shell writes. The
role says what the call is for. It limits which tools the agent holds, never
which paths they touch, so it is no substitute for the sandbox.

## Field rules

Every agent call names its job, and the job picks the model.

| job    | what the call does                              | default  |
| ------ | ----------------------------------------------- | -------- |
| plan   | verifies a bug, plans, checks issues against code, reads review threads for triage | `opus`   |
| build  | implements a plan or a feature                  | `opus`   |
| review | judges a branch                                 | `opus`   |
| fix    | resolves conflicts, repairs a gate or a CI job, closes a coverage gap, works triaged threads | `sonnet` |
| doc    | writes from the branch: the smoke-test guide    | `sonnet` |

No ritual runs `build` yet. Set a model per job under
`[cabinet.agent.models]`; `effort` stays one setting for every job:

```toml
[cabinet.agent.models]
fix = "opus"
```

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
