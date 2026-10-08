"""Taking every reviewed branch in turn, answering it item by item, shipping it."""

import pytest
from vekna.lexicon import Done, RitualError, Transition
from vekna.trial import Trial

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
from cabinet.pacts.project import Project
from cabinet.pacts.pulls import PullRequest
from cabinet.pacts.review import Land, Look, Pick, QueueUp, Read, Recap, Settle
from cabinet.pacts.reviews import (
    Answering,
    Branch,
    Instructed,
    Landing,
    Picking,
    Recapped,
    Review,
    Reviewed,
    Triage,
)
from cabinet.pacts.services import services
from cabinet.pacts.threads import (
    ANSWERED,
    Answer,
    Answered,
    IssueDraft,
    TriageItem,
    TriageNotes,
    filed_for,
    signed,
)
from cabinet.rituals.review import review
from cabinet.specs import STEPS
from tests.conftest import (
    HERE,
    LIST,
    STATUS,
    THREADS,
    checkpoint,
    comment,
    commit,
    listing,
    node,
    page,
    row,
    threads_page,
)
from tests.integration.rituals.falling import falling

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


_ISSUES = "gh issue list *"


# A branch checked out asks which open issues were filed for its threads.
def _nothing_filed(trial: Trial) -> None:
    trial.shell.replies(when=_ISSUES, stdout="[]", always=True)


def _checked_out(trial: Trial, threads: str) -> None:
    trial.decide.answers(answer=True, when="read the review on feature?")
    trial.shell.replies(when="git checkout feature")
    trial.shell.replies(when=THREADS, stdout=threads)


def _threads(*nodes: dict[str, object]) -> str:
    return threads_page(page(list(nodes)))


def _node(node_id: str, *, resolved: bool = False) -> dict[str, object]:
    guard = page([comment(101, author="bot", body="guard")])
    return node(node_id, guard, resolved=resolved, path="src/thing.py", line=12)


# Nothing between `queue_up` and `settle` raises: a step that gives up writes
# its reason into the picking and routes to `recap`, which says the report and
# fails the cast there. What each of those steps owes is the reason, so that is
# what comes back.
def _gave_up(transition: Transition) -> str:
    assert isinstance(transition, Recap)
    return transition.stopped


# A branch taken with whatever share of the budget `pick` would give it.
def _taken(picking: Picking, pull: PullRequest, left: int) -> Branch:
    share = services().steps.share(picking, left)
    assert share is not None
    return picking.take(pull, share)


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

        transition = trial.walk(queue_up, Picking(project=project, bound=2).to(QueueUp))

        assert isinstance(transition, Pick)
        assert [pull.number for pull in transition.queue] == [8, 7]
        assert transition.reserved == services().steps.opening(2)

    @staticmethod
    def test_a_forge_that_will_not_answer_ends_the_cast(
        trial: Trial, project: Project
    ) -> None:
        _preflight(trial)
        trial.shell.replies(when=LIST, exit_code=1, stderr="not logged in")

        transition = trial.walk(queue_up, Picking(project=project, bound=2).to(QueueUp))

        assert "could not list" in _gave_up(transition)
        # No branch was taken, so there is no row to write — only the report.
        assert isinstance(transition, Recap)
        assert not transition.reviewed


class TestPick:
    @staticmethod
    def test_an_empty_queue_is_the_recap(trial: Trial, project: Project) -> None:
        picking = Picking(project=project, bound=2)

        assert trial.walk(pick, picking.to(Pick)) == picking.to(Recap)

    @staticmethod
    def test_a_branch_with_an_open_thread_is_looked_at(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.shell.replies(when=STATUS)
        taken = _taken(Picking(project=project, bound=2), pull, 1)

        assert trial.walk(
            pick, Picking(project=project, bound=2, queue=[pull]).to(Pick)
        ) == taken.to(Look)

    # Nothing went wrong, so nothing fails: the branch goes back on the queue
    # it came off, for the report to name.
    @staticmethod
    def test_a_branch_the_budget_has_no_room_for_ends_the_cast(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        full = Picking(project=project, bound=2, queue=[pull], reserved=STEPS)

        assert trial.walk(pick, full.to(Pick)) == full.to(Recap)
        assert len(trial.shell.commands) == 1

    @staticmethod
    def test_a_branch_with_nothing_open_earns_no_row(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True))
        )

        assert trial.walk(
            pick, Picking(project=project, bound=2, queue=[pull]).to(Pick)
        ) == Picking(project=project, bound=2).to(Pick)

    @staticmethod
    def test_a_forge_that_would_not_say_is_named(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        trial.shell.replies(when=THREADS, exit_code=1)

        transition = trial.walk(
            pick, Picking(project=project, bound=2, queue=[pull]).to(Pick)
        )

        assert transition == Picking(
            project=project,
            bound=2,
            reviewed=[Reviewed(branch="feature", outcome="unread")],
        ).to(Pick)
        assert "would not say what is open on feature" in trial.deltas[0]

    @staticmethod
    def test_a_dirty_worktree_ends_the_cast_and_names_the_branch(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")
        stopped = "the worktree is not clean:\nM a.py"
        taken = _taken(Picking(project=project, bound=2), pull, 1)

        assert trial.walk(
            pick, Picking(project=project, bound=2, queue=[pull]).to(Pick)
        ) == taken.rowed("stopped", stopped).but(stopped=stopped).to(Recap)

    @staticmethod
    def test_a_status_that_fails_ends_the_cast(
        trial: Trial, project: Project, pull: PullRequest
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.shell.replies(when=STATUS, exit_code=128, stderr="not a repo")

        transition = trial.walk(
            pick, Picking(project=project, bound=2, queue=[pull]).to(Pick)
        )

        assert "git status failed" in _gave_up(transition)


class TestLook:
    @staticmethod
    def test_declining_takes_the_next_branch(trial: Trial, branch: Branch) -> None:
        trial.decide.answers(answer=False, when="read the review on feature?")

        assert trial.walk(look, branch.to(Look)) == branch.rowed("declined").to(Pick)
        assert not trial.shell.commands

    @staticmethod
    def test_a_checkout_that_will_not_go_through_is_reported(
        trial: Trial, branch: Branch
    ) -> None:
        trial.decide.answers(answer=True, when="read the review on feature?")
        trial.shell.replies(when="git checkout feature", exit_code=1, stderr="busy")

        assert trial.walk(look, branch.to(Look)) == branch.rowed(
            "elsewhere", "could not take feature: busy"
        ).to(Pick)

    @staticmethod
    def test_a_checkout_that_went_through_is_read(trial: Trial, branch: Branch) -> None:
        _checked_out(trial, _threads(_node("PRRT_1")))
        _nothing_filed(trial)

        assert trial.walk(look, branch.to(Look)) == branch.to(Read)

    @staticmethod
    def test_threads_the_forge_would_not_give_end_the_cast(
        trial: Trial, branch: Branch
    ) -> None:
        trial.decide.answers(answer=True, when="read the review on feature?")
        trial.shell.replies(when="git checkout feature")
        trial.shell.replies(when=THREADS, exit_code=1, stderr="502")

        assert "could not read the threads" in _gave_up(
            trial.walk(look, branch.to(Look))
        )

    # An earlier cast replied and then the forge failed to settle the thread.
    @staticmethod
    def test_a_thread_already_answered_is_settled_and_counted(
        trial: Trial, branch: Branch
    ) -> None:
        replied = page([comment(101, body="guard"), comment(102, body=ANSWERED)])
        _checked_out(trial, _threads(node("PRRT_1", replied), _node("PRRT_2")))
        _nothing_filed(trial)
        trial.shell.replies(when="slug=*-f id=PRRT_1")

        assert trial.walk(look, branch.to(Look)) == branch.recovered(1).to(Read)
        assert trial.shell.commands[-1].endswith("-f id=PRRT_1")
        assert trial.deltas == ["feature: settled 1 threads an earlier cast left"]

    # A reviewer answering the reply reopens the conversation.
    @staticmethod
    def test_a_reply_answered_back_is_left_to_read(
        trial: Trial, branch: Branch
    ) -> None:
        argued = page([comment(101, body=ANSWERED), comment(102, body="no")])
        _checked_out(trial, _threads(node("PRRT_1", argued)))
        _nothing_filed(trial)

        assert trial.walk(look, branch.to(Look)) == branch.to(Read)
        assert not any("id=PRRT_1" in command for command in trial.shell.commands)

    # An earlier cast filed the issue and then the forge refused the reply.
    @staticmethod
    def test_a_thread_with_an_issue_filed_gets_the_reply_naming_it(
        trial: Trial, branch: Branch
    ) -> None:
        _checked_out(trial, _threads(_node("PRRT_1")))
        filed = {
            "number": 9,
            "title": "guard",
            "url": "https://github.com/o/r/issues/9",
            "body": f"later\n\n{filed_for('PRRT_1')}",
            "labels": [],
        }
        trial.shell.replies(when=_ISSUES, stdout=listing(filed))
        trial.shell.replies(when=_ISSUES, stdout="[]")
        trial.shell.replies(when="gh api repos/*")
        trial.shell.replies(when="slug=*-f id=PRRT_1")

        assert trial.walk(look, branch.to(Look)) == branch.recovered(1).to(Read)
        body = signed("Filed as https://github.com/o/r/issues/9")
        assert trial.shell.commands[4] == (
            "gh api repos/{owner}/{repo}/pulls/7/comments/101/replies"
            f" -f body='{body}'"
        )
        assert trial.shell.commands[5].endswith("-f id=PRRT_1")

    # Past the cap, the issue filed for a thread may be the one not listed,
    # and reading that thread again would file it twice.
    @staticmethod
    def test_a_backlog_listed_short_ends_the_cast(trial: Trial, branch: Branch) -> None:
        _checked_out(trial, _threads(_node("PRRT_1")))
        rows = [
            {"number": n, "title": "t", "url": "u", "body": "", "labels": []}
            for n in range(1, 201)
        ]
        trial.shell.replies(when=_ISSUES, stdout=listing(*rows))
        trial.shell.replies(when=_ISSUES, stdout="[]")

        assert "would not list every open issue" in _gave_up(
            trial.walk(look, branch.to(Look))
        )
        assert not any("id=PRRT_1" in command for command in trial.shell.commands)


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

        transition = trial.walk(read, branch.to(Read))

        assert transition == Triage(branch=branch, items=[_ITEM])
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
            picking=Picking(project=project, bound=2, batch=2),
            name="feature",
            number=7,
            rounds=2,
        )
        trial.shell.replies(
            when=THREADS,
            stdout=_threads(_node("PRRT_1"), _node("PRRT_2"), _node("PRRT_3")),
        )
        trial.coding.replies(TriageNotes(items=[_ITEM]))

        trial.walk(read, branch.to(Read))

        prompt = trial.coding.prompts[0]
        assert "thread PRRT_1 (open)" in prompt
        assert "thread PRRT_2 (open)" in prompt
        assert "PRRT_3" not in prompt
        assert trial.deltas[0] == "feature: 3 threads open, reading 2 of them"

    @staticmethod
    def test_threads_the_forge_would_not_give_end_the_cast(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(when=THREADS, exit_code=1, stderr="502")

        assert "could not read the threads" in _gave_up(
            trial.walk(read, branch.to(Read))
        )

    @staticmethod
    def test_a_reading_that_found_nothing_is_said(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.coding.replies(TriageNotes(items=[]))

        assert trial.walk(read, branch.to(Read)) == branch.rowed(
            "nothing", "the reading found nothing, but the forge says otherwise"
        ).to(Pick)

    @staticmethod
    def test_nothing_left_open_on_an_untouched_branch_is_no_work(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True))
        )

        assert trial.walk(read, branch.to(Read)) == branch.rowed(
            "nothing", "nothing is left open"
        ).to(Pick)
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

        assert trial.walk(read, taken.to(Read)) == Landing(branch=taken)
        assert trial.deltas == ["feature: nothing is left open"]

    @staticmethod
    def test_a_reading_that_found_nothing_after_a_round_is_the_gate(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.coding.replies(TriageNotes(items=[]))
        taken = branch.taken(7)

        assert trial.walk(read, taken.to(Read)) == Landing(branch=taken)

    @staticmethod
    def test_an_answer_in_the_wrong_shape_ends_the_cast(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.coding.replies("no idea, sorry")

        assert "did not answer in the shape" in _gave_up(
            trial.walk(read, branch.to(Read))
        )


class TestPlan:
    @staticmethod
    def test_every_item_is_shown_and_asked(trial: Trial, branch: Branch) -> None:
        second = _ITEM.model_copy(update={"thread": "PRRT_2", "action": "file"})
        trial.decide.answers(answer="it guards the empty case", when="1. *")
        trial.decide.answers(answer="", when="2. *")

        transition = trial.walk(plan, Triage(branch=branch, items=[_ITEM, second]))

        assert isinstance(transition, Instructed)
        prompt = transition.prompt
        # Each item's reading is fenced and the answer to it is not, so the
        # `what I want` line sits after the closing marker.
        closed = "--- END UNTRUSTED REVIEW DATA ---"
        assert f"thread: PRRT_1\n{closed}\nwhat I want: it guards the empty case" in (
            prompt
        )
        assert (
            f"thread: PRRT_2\n{closed}\nwhat I want: file it, as the reading says"
            in (prompt)
        )
        assert transition.threads == ["PRRT_1", "PRRT_2"]
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

        assert transition == Answering(
            branch=branch, items=answered.items, threads=["PRRT_1"]
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
    def test_an_agent_that_dies_ends_the_cast(trial: Trial, branch: Branch) -> None:
        falling()
        trial.shell.replies(when="gh pr edit 7*")
        instructed = Instructed(branch=branch, prompt="x", threads=[])

        assert "stopped mid-flight" in _gave_up(trial.walk(work, instructed))


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

        assert trial.walk(answer, answering) == branch.taken(1).to(Read)
        assert trial.shell.commands[1] == (
            "gh api repos/{owner}/{repo}/pulls/7/comments/101/replies"
            f" -f body='{signed('guarded')}'"
        )
        assert trial.shell.commands[2].endswith("-f id=PRRT_1")

    # A thread opened after the branch was taken, or one a round left
    # unanswered, is not read: the rounds were what the budget spoke for.
    @staticmethod
    def test_the_last_round_is_the_gate_with_threads_still_open(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1"), _node("PRRT_9"))
        )
        trial.shell.replies(when="gh api repos/*")
        trial.shell.replies(when="slug=*-f id=PRRT_1")
        last = branch.taken(0)
        answering = Answering(
            branch=last,
            items=[Answer(thread="PRRT_1", reply="guarded")],
            threads=["PRRT_1"],
        )

        assert trial.walk(answer, answering) == Landing(branch=last.taken(1))

    @staticmethod
    def test_an_issue_is_opened_and_named_in_the_reply(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.shell.replies(
            when="gh api repos/{owner}/{repo}/issues -X POST*",
            stdout='{"number": 9, "html_url": "https://github.com/o/r/issues/9"}',
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

        assert trial.shell.commands[1] == (
            "gh api repos/{owner}/{repo}/issues -X POST -f title=guard"
            f" -f body='later\n\n{filed_for('PRRT_1')}'"
        )
        body = signed("filed\n\nFiled as https://github.com/o/r/issues/9")
        assert trial.shell.commands[2].endswith(f"-f body='{body}'")

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
        assert trial.walk(answer, answering) == Landing(branch=branch)
        assert len(trial.shell.commands) == 1
        assert "a thread nobody triaged: PRRT_9" in trial.deltas[0]

    @staticmethod
    def test_a_forge_that_refuses_ends_the_cast(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
        trial.shell.replies(when="gh api repos/*", exit_code=1, stderr="403")
        answering = Answering(
            branch=branch,
            items=[Answer(thread="PRRT_1", reply="guarded")],
            threads=["PRRT_1"],
        )

        assert "could not reply" in _gave_up(trial.walk(answer, answering))


class TestGates:
    @staticmethod
    def test_a_green_gate_lands(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when=_GATE)

        assert trial.walk(gates, Landing(branch=branch)) == branch.to(Land)

    @staticmethod
    def test_a_green_narrow_task_spends_the_gate(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when="CI=1 mise run lint:mypy")

        spent = Landing(branch=branch).charged(gates.name)

        assert trial.walk(gates, spent.but(gate="mise run lint:mypy")) == spent

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

        assert trial.walk(gates, Landing(branch=branch)) == Landing(
            branch=branch, gate="mise run lint:ruff"
        ).charged(gates.name)
        assert "E501 too long" in trial.coding.prompts[0]

    @staticmethod
    def test_an_agent_that_dies_ends_the_cast(trial: Trial, branch: Branch) -> None:
        falling()
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")

        transition = trial.walk(gates, Landing(branch=branch))

        assert "stopped mid-flight" in _gave_up(transition)

    @staticmethod
    def test_a_spent_bound_ends_the_cast_with_the_work_in_place(
        trial: Trial, branch: Branch
    ) -> None:
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")
        # The branch's bound is two, and both attempts are behind it.
        spent = Landing(branch=branch).charged(gates.name).charged(gates.name)
        stopped = "`mise run pr-fix` is still red:\n1 failed"

        assert trial.walk(gates, spent) == branch.rowed("stopped", stopped).but(
            stopped=stopped
        ).to(Recap)
        assert not trial.coding.prompts


class TestLand:
    @staticmethod
    def test_commits_and_pushes(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when="git add -A*")
        trial.shell.replies(when="git push origin feature")

        assert trial.walk(land, branch.to(Land)) == branch.to(Settle)
        assert trial.shell.commands == [
            commit("chore: act on the review triage"),
            "git push origin feature",
        ]

    @staticmethod
    def test_a_push_that_fails_ends_the_cast(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when="git add -A*")
        trial.shell.replies(when="git push origin feature", exit_code=1, stderr="no")

        assert "could not push feature: no" in _gave_up(
            trial.walk(land, branch.to(Land))
        )


class TestSettle:
    @staticmethod
    def test_nothing_left_open_is_done(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True))
        )
        trial.shell.replies(when="gh pr edit 7*")

        assert trial.walk(settle, branch.to(Settle)) == branch.rowed("shipped").to(Pick)
        assert trial.shell.commands[1] == _DONE

    @staticmethod
    def test_threads_left_open_are_counted(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))

        assert trial.walk(settle, branch.to(Settle)) == branch.rowed(
            "shipped", "1 review threads are still open"
        ).to(Pick)
        assert len(trial.shell.commands) == 1

    @staticmethod
    def test_a_forge_that_would_not_say(trial: Trial, branch: Branch) -> None:
        trial.shell.replies(when=THREADS, exit_code=1)

        assert trial.walk(settle, branch.to(Settle)) == branch.rowed(
            "shipped", "the forge would not say what is left open"
        ).to(Pick)


class TestRecap:
    @staticmethod
    def test_a_cast_that_ran_to_the_end(trial: Trial, project: Project) -> None:
        picking = Picking(
            project=project,
            bound=2,
            reviewed=[Reviewed(branch="feature", outcome="shipped")],
        )

        assert trial.walk(recap, picking.to(Recap)) == Done(
            Recapped(reviewed=[Reviewed(branch="feature", outcome="shipped")])
        )

    @staticmethod
    def test_a_stopped_cast_is_said_then_failed(trial: Trial, project: Project) -> None:
        picking = Picking(project=project, bound=2, stopped="red")

        with pytest.raises(RitualError, match="red"):
            trial.walk(recap, picking.to(Recap))

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
        _nothing_filed(trial)
        trial.shell.replies(when=THREADS, stdout=_threads(_node("PRRT_1")))
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

        assert result == Recapped(
            reviewed=[Reviewed(branch="feature", outcome="shipped")]
        )
        assert trial.steps == [
            "queue_up",
            "pick",
            "look",
            "read",
            "plan",
            "work",
            "answer",
            "gates",
            "land",
            "settle",
            "pick",
            "recap",
        ]
        assert trial.shell.commands[-1] == _DONE
        assert trial.shell.commands[-2].startswith("slug=")

    # An earlier cast replied and then the forge failed to settle the thread:
    # settling it leaves nothing to read, and the branch is still marked done.
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_a_branch_finished_by_recovery_is_shipped_and_done(trial: Trial) -> None:
        _preflight(trial)
        trial.shell.replies(
            when=LIST, stdout=listing(row(7, labels=[{"name": "pr::thermo"}]))
        )
        trial.shell.replies(when=HERE, stdout="feature\n")
        replied = page([comment(101, body="guard"), comment(102, body=ANSWERED)])
        open_reply = _threads(node("PRRT_1", replied))
        trial.shell.replies(when=THREADS, stdout=open_reply)
        trial.shell.replies(when=STATUS)
        trial.decide.answers(answer=True, when="read the review on feature?")
        trial.shell.replies(when="git checkout feature")
        trial.shell.replies(when=THREADS, stdout=open_reply)
        trial.shell.replies(when="slug=*-f id=PRRT_1")
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True)), always=True
        )
        trial.shell.replies(when=_GATE)
        trial.shell.replies(when="git add -A*")
        trial.shell.replies(when="git push origin feature")
        trial.shell.replies(when="gh pr edit 7*", always=True)

        result = trial.cast(review, Review(bound=2))

        assert result.reviewed == [Reviewed(branch="feature", outcome="shipped")]
        assert trial.steps == [
            "queue_up",
            "pick",
            "look",
            "read",
            "gates",
            "land",
            "settle",
            "pick",
            "recap",
        ]
        assert not trial.coding.prompts
        assert trial.shell.commands[-1] == _DONE

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
        _nothing_filed(trial)
        trial.shell.replies(when=THREADS, stdout=every)
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

    # Every round the branch was given, and every repair the bound allows: the
    # longest a branch can run, and exactly what its share spoke for.
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_the_worst_a_branch_can_spend_is_what_was_reserved(trial: Trial) -> None:
        _preflight(trial)
        trial.shell.replies(
            when=LIST, stdout=listing(row(7, labels=[{"name": "pr::thermo"}]))
        )
        trial.shell.replies(when=HERE, stdout="feature\n")
        both = _threads(_node("PRRT_1"), _node("PRRT_2"))
        trial.shell.replies(when=THREADS, stdout=both)
        trial.shell.replies(when=STATUS)
        trial.decide.answers(answer=True, when="read the review on feature?")
        trial.shell.replies(when="git checkout feature")
        _nothing_filed(trial)
        trial.shell.replies(when=THREADS, stdout=both)
        trial.decide.answers(answer="", when="1. *", always=True)
        trial.shell.replies(when="gh pr edit 7*", always=True)
        trial.shell.replies(when="gh api repos/*", always=True)
        second = _threads(_node("PRRT_1", resolved=True), _node("PRRT_2"))
        for thread, seen in (("PRRT_1", both), ("PRRT_2", second)):
            trial.shell.replies(when=THREADS, stdout=seen)
            trial.coding.replies(
                TriageNotes(items=[_ITEM.model_copy(update={"thread": thread})]),
                when="Triage the open*",
            )
            trial.coding.replies(
                Answered(items=[Answer(thread=thread, reply="guarded")]),
                when="Below is a triage*",
            )
            trial.shell.replies(when=THREADS, stdout=seen)
            trial.shell.replies(when=f"slug=*-f id={thread}")
        # Red on the whole gate, green on the task it named, twice over.
        red = "[lint:ruff] ERROR task failed"
        trial.shell.replies(when=_GATE, exit_code=1, stdout="E501", stderr=red)
        trial.shell.replies(when=_GATE, exit_code=1, stdout="E501", stderr=red)
        trial.shell.replies(when=_GATE)
        trial.shell.replies(when="CI=1 mise run lint:ruff", always=True)
        trial.coding.replies("fixed", when="*is this project's gate*", always=True)
        trial.shell.replies(when="git add -A*")
        trial.shell.replies(when="git push origin feature")
        settled = _threads(
            _node("PRRT_1", resolved=True), _node("PRRT_2", resolved=True)
        )
        trial.shell.replies(when=THREADS, stdout=settled)

        result = trial.cast(review, Review(bound=2, batch=1))

        assert result.reviewed == [Reviewed(branch="feature", outcome="shipped")]
        assert trial.steps == [
            "queue_up",
            "pick",
            "look",
            *["read", "plan", "work", "answer"] * 2,
            *["gates"] * 5,
            "land",
            "settle",
            "pick",
            "recap",
        ]
        share = services().steps.share(Picking(project=Project(), bound=2, batch=1), 2)
        assert share is not None
        assert len(trial.steps[2:-2]) == share.steps
        assert len(trial.steps) == services().steps.opening(1) + share.steps
