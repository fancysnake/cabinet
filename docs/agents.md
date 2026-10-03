# Agents

Every agent call in a ritual is one bounded piece of work: resolve this
conflict, make this task pass, write tests for these lines, answer this
thread. Every agent has a shell. What it may not run is a deny list, and
nothing the prompt says can shorten it.

## Run every cast in a sandbox

The deny list matches command prefixes. It stops an agent from spending
twenty minutes on a sweep the ritual is about to run anyway, and from an
honest `git commit`. It does not stop an agent set on getting round it:
`sh -c "git push"` is not a command that starts with `git push`. The boundary
is the sandbox the cast runs in, such as fence. Run every cast, attended or
not, inside one.

## Permission modes

Unattended, every agent call runs under Claude's `dontAsk` permission mode,
so a cast at 3am never hangs on a prompt. Attended — `review` always, the
sweeps with `--attended true` — the mode is `auto`, with somebody there to be
asked. The deny list holds in both.

## Roles

| role     | may use                                                         |
| -------- | --------------------------------------------------------------- |
| reader   | `Read`, `Grep`, `Glob`, `Bash`                                  |
| writer   | reader + `Edit`, `Write`, `MultiEdit`                           |
| resolver | writer, told to stage what it resolves with `git add`           |

## Denied to every role

| prefix                                               | why                                                    |
| ---------------------------------------------------- | ------------------------------------------------------ |
| the project's `gate`, `coverage`, `fast_coverage`    | the ritual runs them itself the moment the agent stops |
| `git commit`, `git push`                             | the commits and the push are the ritual's              |
| `git rebase`, `git merge`, `git reset`, `git switch` | they move the branch the ritual reads                  |
| `gh`, `glab`                                         | every forge write is the ritual's                      |
| every prefix in `agent.may_not_run`                  | the project's own slow tasks                           |

So no agent commits, pushes, runs a sweep, or says anything to the forge:
not a label, not a comment, not an issue. Every forge call is the ritual's
own, through vekna's `shell` medium in the `links` adapters, including
`identify`'s labels, sub-issues and links. Its agent reads the backlog and
hands back what each issue is, and the ritual puts that on. After every
repair attempt the ritual re-runs the task the runner named as broken and
hands the agent the output.

The prompt quotes the same list the SDK denies, so an agent does not spend a
turn on a refused command.

## `may_not_run`

`may_not_run` names the slow tasks the gate and the coverage commands do not:
a full e2e suite, a whole-repository linter sweep. Each prefix becomes a
`Bash(<prefix>:*)` deny entry:

```toml
[cabinet.agent]
may_not_run = ["mise run lint:py", "mise run test:py"]
```

Leave the quick checks off it. An agent that runs one test file or one linter
over one file before it stops is an agent whose attempt is more likely to
count.
