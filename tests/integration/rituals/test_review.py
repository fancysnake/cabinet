"""Taking every reviewed branch in turn, answering it item by item, shipping it."""

import json
from typing import TYPE_CHECKING

import pytest
from vekna.lexicon import Goto, RitualError, done, goto

from cabinet.gates.ritual.vekna.review import (
    answer,
    gates,
    land,
    look,
    pick,
    plan,
    queue_up,
    read,
    recap,
    settle,
    work,
)
from cabinet.pacts.reviews import (
    Answering,
    Branch,
    Instructed,
    Landing,
    Picking,
    Review,
    Reviewed,
    Triage,
)
from cabinet.pacts.threads import Answer, Answered, IssueDraft, TriageItem, TriageNotes
from cabinet.rituals.review import review
from tests.conftest import HERE, LIST, STATUS, THREADS, checkpoint, commit, listing, row
from tests.integration.rituals.falling import falling

if TYPE_CHECKING:

    from vekna.trial import Trial

    from cabinet.pacts.project import Project
    from cabinet.pacts.pulls import PullRequest

_STARTED = checkpoint("review", "started")
_DONE = checkpoint("review", "done")
_GATE = "CI=1 mise run pr-fix"
_ITEM = TriageItem(
    where="src/thing.py",
    raised="add a guard before the loop",
    what="the guard is missing",
    priority="p1",
    action="fix",
    thread="PRRT_1",
)


def _threads(*nodes: dict[str, object]) -> str:
    return json.dumps(
        {
            "data": {
                "repository": {"pullRequest": {"reviewThreads": {"nodes": list(nodes)}}}
            }
        }
    )


def _node(node_id: str, *, resolved: bool = False) -> dict[str, object]:
    return {
        "id": node_id,
        "isResolved": resolved,
        "path": "src/thing.py",
        "line": 12,
        "comments": {
            "nodes": [{"databaseId": 101, "author": {"login": "bot"}, "body": "guard"}]
        },
    }


def _preflight(trial: Trial) -> None:
    trial.shell.replies(
        when="git remote get-url origin", stdout="https://github.com/o/r.git\n"
    )
    trial.shell.replies(when="git config --get-urlmatch*", stdout="!gh auth\n")


class TestQueueUp:
    @staticmethod
    def test_only_reviewed_branches_and_yours_first(
        trial: Trial, project: Project
    ) -> None:
        _preflight(trial)
        reviewed = {"labels": [{"name": "pr::thermo"}]}
        trial.shell.replies(
            when=LIST,
            stdout=listing(
                row(8, updatedAt="2026-08-02T00:00:00Z", **reviewed),
                row(7, **reviewed),
                row(9),
                row(10, headRefName="main", **reviewed),
            ),
        )
        trial.shell.replies(when=HERE, stdout="feature-8\n")

        transition = trial.walk(queue_up, Picking(project=project, bound=2))

        assert isinstance(transition, Goto)
        assert transition.target is pick
        assert isinstance(transition.payload, Picking)
        assert [pull.number for pull in transition.payload.queue] == [8, 7]

    @staticmethod
    def test_a_forge_that_will_not_answer_fails_the_cast(
        trial: Trial, project: Project
    ) -> None:
        _preflight(trial)
        trial.shell.replies(when=LIST, exit_code=1, stderr="not logged in")

        with pytest.raises(RitualError, match="could not list"):
            trial.walk(queue_up, Picking(project=project, bound=2))


class TestPick:
    @staticmethod
    def test_an_empty_queue_is_the_recap(trial: Trial, project: Project) -> None:
        picking = Picking(project=project, bound=2)

        assert trial.walk(pick, picking) == goto(recap, picking)

    @staticmethod
    def test_a_branch_with_an_open_thread_is_looked_at(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.shell.replies(when=STATUS)

        assert trial.walk(
            pick, Picking(project=project, bound=2, queue=[pull])
        ) == goto(
            look,
            Branch(picking=Picking(project=project, bound=2), name="feature", number=7),
        )

    @staticmethod
    def test_a_branch_with_nothing_open_earns_no_row(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True))
        )

        assert trial.walk(
            pick, Picking(project=project, bound=2, queue=[pull])
        ) == goto(pick, Picking(project=project, bound=2))

    @staticmethod
    def test_a_forge_that_would_not_say_is_named(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        trial.shell.replies(when=THREADS, exit_code=1)

        transition = trial.walk(pick, Picking(project=project, bound=2, queue=[pull]))

        assert transition == goto(
            pick,
            Picking(
                project=project,
                bound=2,
                reviewed=[Reviewed(branch="feature", outcome="unread")],
            ),
        )
        assert "would not say what is open on feature" in trial.deltas[0]

    @staticmethod
    def test_a_dirty_worktree_fails_the_cast(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")

        with pytest.raises(RitualError, match="not clean"):
            trial.walk(pick, Picking(project=project, bound=2, queue=[pull]))

    @staticmethod
    def test_a_status_that_fails_fails_the_cast(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.shell.replies(when=STATUS, exit_code=128, stderr="not a repo")

        with pytest.raises(RitualError, match="git status failed"):
            trial.walk(pick, Picking(project=project, bound=2, queue=[pull]))


class TestLook:
    @staticmethod
    def test_declining_takes_the_next_branch(trial: Trial, branch: Branch) -> None:
        trial.decide.answers(answer=False, when="read the review on feature?")

        assert trial.walk(look, branch) == goto(pick, branch.rowed("declined"))
        assert not trial.shell.commands

    @staticmethod
    def test_a_checkout_that_will_not_go_through_is_reported(
        trial: Trial, branch: Branch
    ) -> None:
        trial.decide.answers(answer=True, when="read the review on feature?")
        trial.shell.replies(when="git checkout feature", exit_code=1, stderr="busy")

        assert trial.walk(look, branch) == goto(
            pick, branch.rowed("elsewhere", "could not take feature: busy")
        )

    @staticmethod
    def test_a_checkout_that_went_through_is_read(trial: Trial, branch: Branch) -> None:
        trial.decide.answers(answer=True, when="read the review on feature?")
        trial.shell.replies(when="git checkout feature")

        assert trial.walk(look, branch) == goto(read, branch)


class TestRead:
    @staticmethod
    def test_the_reading_is_a_triage_of_the_open_threads(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(
            when=THREADS,
            stdout=_threads(_node("PRRT_1"), _node("PRRT_2", resolved=True)),
        )
        trial.coding.replies(TriageNotes(items=[_ITEM]))

        transition = trial.walk(read, branch)

        assert transition == goto(plan, Triage(branch=branch, items=[_ITEM]))
        prompt = trial.coding.prompts[0]
        assert "thread PRRT_1 (open)" in prompt
        assert "PRRT_2" not in prompt
        assert "UNTRUSTED" in prompt
        assert trial.coding.calls[0].focus_options is not None
        assert "Edit" not in str(trial.coding.calls[0].focus_options)
        # Somebody is at the terminal for the whole of this ritual.
        assert "permission_mode='auto'" in str(trial.coding.calls[0].focus_options)
        assert "threads open" not in trial.deltas[0]

    @staticmethod
    def test_only_the_first_batch_is_read_and_the_rest_is_counted(
        trial: Trial, project: Project
    ) -> None:
        branch = Branch(
            picking=Picking(project=project, bound=2, batch=2), name="feature", number=7
        )
        trial.shell.replies(
            when=THREADS,
            stdout=_threads(_node("PRRT_1"), _node("PRRT_2"), _node("PRRT_3")),
        )
        trial.coding.replies(TriageNotes(items=[_ITEM]))

        trial.walk(read, branch)

        prompt = trial.coding.prompts[0]
        assert "thread PRRT_1 (open)" in prompt
        assert "thread PRRT_2 (open)" in prompt
        assert "PRRT_3" not in prompt
        assert trial.deltas[0] == "feature: 3 threads open, reading 2 of them"

    @staticmethod
    def test_threads_the_forge_would_not_give_fail_the_cast(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(when=THREADS, exit_code=1, stderr="502")

        with pytest.raises(RitualError, match="could not read the threads"):
            trial.walk(read, branch)

    @staticmethod
    def test_a_reading_that_found_nothing_is_said(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.coding.replies(TriageNotes(items=[]))

        assert trial.walk(read, branch) == goto(
            pick,
            branch.rowed(
                "nothing", "the reading found nothing, but the forge says otherwise"
            ),
        )

    @staticmethod
    def test_nothing_left_open_on_an_untouched_branch_is_no_work(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True))
        )

        assert trial.walk(read, branch) == goto(
            pick, branch.rowed("nothing", "nothing is left open")
        )
        assert not trial.coding.prompts

    # The rounds before this one changed the worktree, so what they did goes
    # to the gate whatever this round found.
    @staticmethod
    def test_nothing_left_open_after_a_round_is_the_gate(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True))
        )
        taken = branch.taken(7)

        assert trial.walk(read, taken) == goto(gates, Landing(branch=taken))
        assert trial.deltas == ["feature: nothing is left open"]

    @staticmethod
    def test_a_reading_that_found_nothing_after_a_round_is_the_gate(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.coding.replies(TriageNotes(items=[]))
        taken = branch.taken(7)

        assert trial.walk(read, taken) == goto(gates, Landing(branch=taken))

    @staticmethod
    def test_an_answer_in_the_wrong_shape_fails_the_cast(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.coding.replies("no idea, sorry")

        with pytest.raises(RitualError, match="did not answer in the shape"):
            trial.walk(read, branch)


class TestPlan:
    @staticmethod
    def test_every_item_is_shown_and_asked(trial: Trial, branch: Branch) -> None:
        second = _ITEM.model_copy(update={"thread": "PRRT_2", "action": "file"})
        trial.decide.answers(answer="it guards the empty case", when="1. *")
        trial.decide.answers(answer="", when="2. *")

        transition = trial.walk(plan, Triage(branch=branch, items=[_ITEM, second]))

        assert isinstance(transition, Goto)
        assert transition.target is work
        assert isinstance(transition.payload, Instructed)
        prompt = transition.payload.prompt
        assert "thread: PRRT_1\n   what I want: it guards the empty case" in prompt
        assert "thread: PRRT_2\n   what I want: file it, as the reading says" in prompt
        assert transition.payload.threads == ["PRRT_1", "PRRT_2"]
        assert "2 outstanding — p1: 2, p2: 0, p3: 0, p4: 0" in trial.deltas[0]


class TestWork:
    @staticmethod
    def test_marks_started_and_hands_the_answers_on(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(when="gh pr edit 7*")
        answered = Answered(items=[Answer(thread="PRRT_1", reply="guarded")])
        trial.coding.replies(answered)
        instructed = Instructed(branch=branch, prompt="the triage", threads=["PRRT_1"])

        transition = trial.walk(work, instructed)

        assert transition == goto(
            answer, Answering(branch=branch, items=answered.items, threads=["PRRT_1"])
        )
        assert trial.shell.commands == [_STARTED]
        assert trial.coding.prompts == ["the triage"]
        assert trial.coding.calls[0].focus_options is not None
        assert "Edit" in str(trial.coding.calls[0].focus_options)

    @staticmethod
    def test_a_checkpoint_that_will_not_go_on_is_said_and_survived(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(when="gh pr edit 7*", exit_code=1, stderr="no label")
        trial.coding.replies(Answered(items=[]))

        trial.walk(work, Instructed(branch=branch, prompt="x", threads=[]))

        assert "could not mark v:review:started" in trial.deltas[0]

    @staticmethod
    def test_an_agent_that_dies_fails_the_cast(trial: Trial, branch: Branch) -> None:
        falling()
        trial.shell.replies(when="gh pr edit 7*")

        with pytest.raises(RitualError, match="stopped mid-flight"):
            trial.walk(work, Instructed(branch=branch, prompt="x", threads=[]))


class TestAnswer:
    @staticmethod
    def test_replies_and_settles_each_thread(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.shell.replies(when="gh api repos/*")
        trial.shell.replies(when="slug=*-f id=PRRT_1")
        answering = Answering(
            branch=branch,
            items=[Answer(thread="PRRT_1", reply="guarded")],
            threads=["PRRT_1"],
        )

        assert trial.walk(answer, answering) == goto(read, branch.taken(1))
        assert trial.shell.commands[1] == (
            "gh api repos/{owner}/{repo}/pulls/7/comments/101/replies -f body=guarded"
        )
        assert trial.shell.commands[2].endswith("-f id=PRRT_1")

    @staticmethod
    def test_an_issue_is_opened_and_named_in_the_reply(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.shell.replies(
            when="gh issue create*", stdout="https://github.com/o/r/issues/9\n"
        )
        trial.shell.replies(when="gh api repos/*")
        trial.shell.replies(when="slug=*-f id=PRRT_1")
        answering = Answering(
            branch=branch,
            items=[
                Answer(
                    thread="PRRT_1",
                    reply="filed",
                    issue=IssueDraft(title="guard", body="later"),
                )
            ],
            threads=["PRRT_1"],
        )

        trial.walk(answer, answering)

        assert trial.shell.commands[1] == "gh issue create --title guard --body later"
        assert trial.shell.commands[2].endswith(
            "-f body='filed\n\nFiled as https://github.com/o/r/issues/9'"
        )

    @staticmethod
    def test_a_thread_nobody_triaged_is_skipped_and_said(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        answering = Answering(
            branch=branch,
            items=[Answer(thread="PRRT_9", reply="made up")],
            threads=["PRRT_1"],
        )

        # Nothing settled, so another round would read the same thread back.
        assert trial.walk(answer, answering) == goto(gates, Landing(branch=branch))
        assert len(trial.shell.commands) == 1
        assert "a thread nobody triaged: PRRT_9" in trial.deltas[0]

    @staticmethod
    def test_a_forge_that_refuses_fails_the_cast(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.shell.replies(when="gh api repos/*", exit_code=1, stderr="403")
        answering = Answering(
            branch=branch,
            items=[Answer(thread="PRRT_1", reply="guarded")],
            threads=["PRRT_1"],
        )

        with pytest.raises(RitualError, match="could not reply"):
            trial.walk(answer, answering)


class TestGates:
    @staticmethod
    def test_a_green_gate_lands(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when=_GATE)

        assert trial.walk(gates, Landing(branch=branch)) == goto(land, branch)

    @staticmethod
    def test_a_green_narrow_task_spends_the_gate(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when="CI=1 mise run lint:mypy")

        assert trial.walk(
            gates, Landing(branch=branch, tries=1, gate="mise run lint:mypy")
        ) == goto(gates, Landing(branch=branch, tries=1))

    @staticmethod
    def test_a_red_gate_is_repaired_on_the_casts_thread(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(
            when=_GATE,
            exit_code=1,
            stdout="E501 too long",
            stderr="[lint:ruff] ERROR task failed",
        )
        trial.coding.replies("fixed")

        assert trial.walk(gates, Landing(branch=branch)) == goto(
            gates, Landing(branch=branch, tries=1, gate="mise run lint:ruff")
        )
        assert "E501 too long" in trial.coding.prompts[0]

    @staticmethod
    def test_an_agent_that_dies_fails_the_cast(trial: Trial, branch: Branch) -> None:
        falling()
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")

        with pytest.raises(RitualError, match="stopped mid-flight"):
            trial.walk(gates, Landing(branch=branch))

    @staticmethod
    def test_a_spent_bound_ends_the_cast_with_the_work_in_place(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")

        assert trial.walk(gates, Landing(branch=branch, tries=2)) == goto(
            recap,
            branch.picking.but(
                stopped="`mise run pr-fix` is still red after 2 attempts"
            ),
        )
        assert not trial.coding.prompts


class TestLand:
    @staticmethod
    def test_commits_and_pushes(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when="git add -A*")
        trial.shell.replies(when="git push origin feature")

        assert trial.walk(land, branch) == goto(settle, branch)
        assert trial.shell.commands == [
            commit("chore: act on the review triage"),
            "git push origin feature",
        ]

    @staticmethod
    def test_a_push_that_fails_fails_the_cast(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when="git add -A*")
        trial.shell.replies(when="git push origin feature", exit_code=1, stderr="no")

        with pytest.raises(RitualError, match="could not push feature: no"):
            trial.walk(land, branch)


class TestSettle:
    @staticmethod
    def test_nothing_left_open_is_done(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True))
        )
        trial.shell.replies(when="gh pr edit 7*")

        assert trial.walk(settle, branch) == goto(pick, branch.rowed("shipped"))
        assert trial.shell.commands[1] == _DONE

    @staticmethod
    def test_threads_left_open_are_counted(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))

        assert trial.walk(settle, branch) == goto(
            pick, branch.rowed("shipped", "1 review threads are still open")
        )
        assert len(trial.shell.commands) == 1

    @staticmethod
    def test_a_forge_that_would_not_say(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when=THREADS, exit_code=1)

        assert trial.walk(settle, branch) == goto(
            pick, branch.rowed("shipped", "the forge would not say what is left open")
        )


class TestRecap:
    @staticmethod
    def test_a_cast_that_ran_to_the_end(trial: Trial, project: Project) -> None:
        picking = Picking(
            project=project,
            bound=2,
            reviewed=[Reviewed(branch="feature", outcome="shipped")],
        )

        assert trial.walk(recap, picking) == done(picking)

    @staticmethod
    def test_a_stopped_cast_is_said_then_failed(trial: Trial, project: Project) -> None:
        picking = Picking(project=project, bound=2, stopped="red")

        with pytest.raises(RitualError, match="red"):
            trial.walk(recap, picking)

        assert "the cast stopped: red" in trial.deltas[0]


class TestWholeCast:
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_one_branch_read_answered_and_shipped(trial: Trial) -> None:
        _preflight(trial)
        trial.shell.replies(
            when=LIST, stdout=listing(row(7, labels=[{"name": "pr::thermo"}]))
        )
        trial.shell.replies(when=HERE, stdout="feature\n")
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.shell.replies(when=STATUS)
        trial.decide.answers(answer=True, when="read the review on feature?")
        trial.shell.replies(when="git checkout feature")
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.coding.replies(TriageNotes(items=[_ITEM]), when="Triage the open*")
        trial.decide.answers(answer="", when="1. *")
        trial.shell.replies(when="gh pr edit 7*", always=True)
        trial.coding.replies(
            Answered(items=[Answer(thread="PRRT_1", reply="guarded")]),
            when="Below is a triage*",
        )
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.shell.replies(when="gh api repos/*")
        trial.shell.replies(when="slug=*-f id=PRRT_1")
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True)), always=True
        )
        trial.shell.replies(when=_GATE)
        trial.shell.replies(when="git add -A*")
        trial.shell.replies(when="git push origin feature")

        result = trial.cast(review, Review(bound=2))

        assert result == Picking(
            project=Picking.model_validate({"project": {}, "bound": 2}).project,
            bound=2,
            reviewed=[Reviewed(branch="feature", outcome="shipped")],
        )
        assert trial.steps == [
            "queue_up",
            "pick",
            "look",
            "read",
            "plan",
            "work",
            "answer",
            "read",
            "gates",
            "land",
            "settle",
            "pick",
            "recap",
        ]
        assert trial.shell.commands[-1] == _DONE
        assert trial.shell.commands[-2].startswith("slug=")

    # Three threads, a batch of two: two rounds of reading and answering, one
    # gate, one commit.
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_a_review_bigger_than_the_batch_goes_round_twice(trial: Trial) -> None:
        _preflight(trial)
        trial.shell.replies(
            when=LIST, stdout=listing(row(7, labels=[{"name": "pr::thermo"}]))
        )
        trial.shell.replies(when=HERE, stdout="feature\n")
        every = _threads(_node("PRRT_1"), _node("PRRT_2"), _node("PRRT_3"))
        trial.shell.replies(when=THREADS, stdout=every)
        trial.shell.replies(when=STATUS)
        trial.decide.answers(answer=True, when="read the review on feature?")
        trial.shell.replies(when="git checkout feature")
        # The first round reads, works and posts over the whole list.
        trial.shell.replies(when=THREADS, stdout=every)
        first = [_ITEM, _ITEM.model_copy(update={"thread": "PRRT_2"})]
        trial.coding.replies(TriageNotes(items=first), when="Triage the open*")
        trial.decide.answers(answer="", when="1. *", always=True)
        trial.decide.answers(answer="", when="2. *")
        trial.shell.replies(when="gh pr edit 7*", always=True)
        trial.coding.replies(
            Answered(
                items=[
                    Answer(thread="PRRT_1", reply="guarded"),
                    Answer(thread="PRRT_2", reply="guarded"),
                ]
            ),
            when="Below is a triage*",
        )
        trial.shell.replies(when=THREADS, stdout=every)
        trial.shell.replies(when="gh api repos/*", always=True)
        trial.shell.replies(when="slug=*-f id=PRRT_1")
        trial.shell.replies(when="slug=*-f id=PRRT_2")
        # The second round sees the first two settled and reads the third.
        remaining = _threads(
            _node("PRRT_1", resolved=True),
            _node("PRRT_2", resolved=True),
            _node("PRRT_3"),
        )
        trial.shell.replies(when=THREADS, stdout=remaining)
        second = [_ITEM.model_copy(update={"thread": "PRRT_3"})]
        trial.coding.replies(TriageNotes(items=second), when="Triage the open*")
        trial.coding.replies(
            Answered(items=[Answer(thread="PRRT_3", reply="guarded")]),
            when="Below is a triage*",
        )
        trial.shell.replies(when=THREADS, stdout=remaining)
        trial.shell.replies(when="slug=*-f id=PRRT_3")
        settled = _threads(
            _node("PRRT_1", resolved=True),
            _node("PRRT_2", resolved=True),
            _node("PRRT_3", resolved=True),
        )
        trial.shell.replies(when=THREADS, stdout=settled, always=True)
        trial.shell.replies(when=_GATE)
        trial.shell.replies(when="git add -A*")
        trial.shell.replies(when="git push origin feature")

        result = trial.cast(review, Review(bound=2, batch=2))

        assert result.reviewed == [Reviewed(branch="feature", outcome="shipped")]
        assert trial.steps == [
            "queue_up",
            "pick",
            "look",
            "read",
            "plan",
            "work",
            "answer",
            "read",
            "plan",
            "work",
            "answer",
            "read",
            "gates",
            "land",
            "settle",
            "pick",
            "recap",
        ]
        assert "PRRT_3" not in trial.coding.prompts[0]
        assert "PRRT_1" not in trial.coding.prompts[2]
        assert "PRRT_3" in trial.coding.prompts[2]
        assert trial.deltas[0] == "feature: 3 threads open, reading 2 of them"
        assert trial.shell.commands.count(_GATE) == 1
        assert trial.shell.commands[-1] == _DONE
