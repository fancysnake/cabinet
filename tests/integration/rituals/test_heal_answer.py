"""The answer task: finish what was left, triage, answer, post, gate, commit."""

import pytest
from vekna.trial import Trial

from cabinet.gates.ritual.vekna.heal import (
    answer_gate,
    answer_threads,
    ask_triage,
    land_answers,
    post_answers,
    read_threads,
    settle_left,
    tend,
)
from cabinet.pacts.budgets import ROUNDS
from cabinet.pacts.heal import (
    AnswerGate,
    AnswerThreads,
    AskTriage,
    Chart,
    LandAnswers,
    PostAnswers,
    ReadThreads,
    SetAside,
    SettleLeft,
    StandDown,
    Tend,
)
from cabinet.pacts.healing import Heal, Work
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
from cabinet.rituals.answer import answer
from cabinet.rituals.heal_mine import heal_mine
from tests.conftest import (
    HERE,
    LIST,
    STATUS,
    THREADS,
    board,
    comment,
    commit,
    listing,
    node,
    page,
    row,
    threads_page,
)
from tests.integration.rituals.falling import falling

_ISSUES = "gh issue list *"
_REPLY = "gh api repos/{owner}/{repo}/pulls/7/comments/101/replies"
_RESOLVE = "slug=*-f id=PRRT_1"
_GATE = "CI=1 mise run pr-fix"
_READER = "Triage the open review threads*"
_WRITER = "Below is a triage*"
_ITEM = TriageItem(
    where="src/thing.py",
    raised="add a guard before the loop",
    what="the guard is missing",
    priority="p1",
    action="fix",
    thread="PRRT_1",
)
_GREEN_BOARD = '{"total_count": 0, "check_runs": []}'
_AHEAD = f'test feature = "$({HERE})" && git rev-list --count origin/feature..HEAD'


def _threads(*nodes: dict[str, object]) -> str:
    return threads_page(page(list(nodes)))


def _node(node_id: str, *, resolved: bool = False) -> dict[str, object]:
    guard = page([comment(101, author="bot", body="guard")])
    return node(node_id, guard, resolved=resolved, path="src/thing.py", line=12)


_OPEN = _threads(_node("PRRT_1"))


def _attended(work: Work) -> Work:
    return work.but(run=work.run.model_copy(update={"attended": True}))


# A branch the writer has already been at, so a round with nothing more to do
# lands whatever it changed.
def _written(work: Work) -> Work:
    return _attended(work).charged(answer_threads.name)


def _answering(work: Work, *answers: Answer) -> PostAnswers:
    return PostAnswers(work=work, items=list(answers), threads=["PRRT_1"])


class TestTend:
    @staticmethod
    def test_answer_starts_with_what_an_earlier_cast_left(
        trial: Trial, work: Work
    ) -> None:
        answering = _attended(work).but(todos=["answer", "review"])

        assert trial.walk(tend, answering.to(Tend)) == answering.but(
            todos=["review"]
        ).to(SettleLeft)


class TestSettleLeft:
    @staticmethod
    def test_nothing_left_half_settled_goes_to_the_reading(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.shell.replies(when=_ISSUES, stdout="[]", always=True)

        assert trial.walk(settle_left, work.to(SettleLeft)) == work.to(ReadThreads)
        assert not trial.deltas

    # An earlier cast replied and then the forge failed to settle the thread.
    @staticmethod
    def test_a_thread_already_answered_is_settled(trial: Trial, work: Work) -> None:
        replied = page(
            [comment(101, body="guard"), comment(102, body=ANSWERED, mine=True)]
        )
        trial.shell.replies(when=THREADS, stdout=_threads(node("PRRT_1", replied)))
        trial.shell.replies(when=_RESOLVE)

        assert trial.walk(settle_left, work.to(SettleLeft)) == work.to(ReadThreads)
        assert trial.shell.commands[-1].endswith("-f id=PRRT_1")
        assert trial.deltas == ["feature: settled 1 threads an earlier cast left"]

    # A reviewer answering the reply reopens the conversation.
    @staticmethod
    def test_a_reply_answered_back_is_left_to_read(trial: Trial, work: Work) -> None:
        argued = page([comment(101, body=ANSWERED, mine=True), comment(102, body="no")])
        trial.shell.replies(when=THREADS, stdout=_threads(node("PRRT_1", argued)))
        trial.shell.replies(when=_ISSUES, stdout="[]", always=True)

        assert trial.walk(settle_left, work.to(SettleLeft)) == work.to(ReadThreads)
        assert not any("id=PRRT_1" in command for command in trial.shell.commands)

    # An earlier cast filed the issue and then the forge refused the reply.
    @staticmethod
    def test_a_thread_with_an_issue_filed_gets_the_reply_naming_it(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_OPEN)
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
        trial.shell.replies(when=_RESOLVE)

        assert trial.walk(settle_left, work.to(SettleLeft)) == work.to(ReadThreads)
        body = signed("Filed as https://github.com/o/r/issues/9")
        assert f"{_REPLY} -f body='{body}'" in trial.shell.commands
        assert trial.shell.commands[-1].endswith("-f id=PRRT_1")

    # Past the cap, the issue filed for a thread may be the one not listed,
    # and reading that thread again would file it twice.
    @staticmethod
    def test_a_backlog_listed_short_leaves_the_threads(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        rows = [
            {"number": n, "title": "t", "url": "u", "body": "", "labels": []}
            for n in range(1, 201)
        ]
        trial.shell.replies(when=_ISSUES, stdout=listing(*rows))
        trial.shell.replies(when=_ISSUES, stdout="[]")

        transition = trial.walk(settle_left, work.to(SettleLeft))

        assert isinstance(transition, Tend)
        assert "would not list every open issue" in transition.note

    @staticmethod
    def test_threads_the_forge_would_not_give_leave_the_task(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, exit_code=1, stderr="502")

        transition = trial.walk(settle_left, work.to(SettleLeft))

        assert isinstance(transition, Tend)
        assert "could not read the threads" in transition.note


class TestReadThreads:
    @staticmethod
    def test_the_reading_is_a_triage_of_the_open_threads(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(
            when=THREADS,
            stdout=_threads(_node("PRRT_1"), _node("PRRT_2", resolved=True)),
        )
        trial.coding.replies(TriageNotes(items=[_ITEM]))
        attended = _attended(work)

        assert trial.walk(read_threads, attended.to(ReadThreads)) == AskTriage(
            work=attended.charged(read_threads.name), items=[_ITEM]
        )
        prompt = trial.coding.prompts[0]
        assert prompt.startswith("Triage the open review threads on pull request #7")
        assert "thread PRRT_1 (open)" in prompt
        assert "PRRT_2" not in prompt
        assert "UNTRUSTED" in prompt
        assert "Edit" not in str(trial.coding.calls[0].focus_options)
        assert not any("threads open" in delta for delta in trial.deltas)

    @staticmethod
    def test_only_the_first_batch_is_read_and_the_rest_is_counted(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(
            when=THREADS,
            stdout=_threads(_node("PRRT_1"), _node("PRRT_2"), _node("PRRT_3")),
        )
        trial.coding.replies(TriageNotes(items=[_ITEM]))
        batched = work.but(run=work.run.model_copy(update={"batch": 2}))

        trial.walk(read_threads, batched.to(ReadThreads))

        prompt = trial.coding.prompts[0]
        assert "thread PRRT_2 (open)" in prompt
        assert "PRRT_3" not in prompt
        assert "feature: 3 threads open, reading 2 of them" in trial.deltas

    @staticmethod
    def test_nothing_open_on_a_branch_nobody_wrote_on_is_no_work(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True))
        )

        assert trial.walk(read_threads, work.to(ReadThreads)) == work.to(Tend)
        assert not trial.coding.prompts

    # The rounds before this one changed the worktree, so what they did goes
    # to the gate whatever this round found.
    @staticmethod
    def test_nothing_open_after_a_round_is_the_gate(trial: Trial, work: Work) -> None:
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True))
        )
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")
        written = _written(work)

        assert trial.walk(read_threads, written.to(ReadThreads)) == written.to(
            AnswerGate
        )

    @staticmethod
    def test_a_round_that_changed_no_file_has_nothing_to_land(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True))
        )
        trial.shell.replies(when=STATUS)
        written = _written(work)

        assert trial.walk(read_threads, written.to(ReadThreads)) == written.to(Tend)

    @staticmethod
    def test_a_status_that_fails_sets_the_branch_aside(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True))
        )
        trial.shell.replies(when=STATUS, exit_code=128, stderr="not a repo")

        transition = trial.walk(read_threads, _written(work).to(ReadThreads))

        assert isinstance(transition, SetAside)
        assert "git status failed" in transition.note

    # What is still open waits for the next cast: the rounds are what the
    # share spoke for.
    @staticmethod
    def test_the_last_round_spent_lands_without_reading(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")
        spent = _written(work)
        for _ in range(ROUNDS):
            spent = spent.charged(read_threads.name)

        assert trial.walk(read_threads, spent.to(ReadThreads)) == spent.to(AnswerGate)
        assert trial.shell.commands == ["git status --porcelain"]

    @staticmethod
    def test_a_reading_that_found_nothing_is_said(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.coding.replies(TriageNotes(items=[]))

        assert trial.walk(read_threads, work.to(ReadThreads)) == work.but(
            note="the reading found nothing, but the forge says otherwise"
        ).to(Tend)

    @staticmethod
    def test_an_answer_in_the_wrong_shape_is_said(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.coding.replies("no idea, sorry")

        transition = trial.walk(read_threads, work.to(ReadThreads))

        assert isinstance(transition, Tend)
        assert "did not answer in the shape" in transition.note

    @staticmethod
    def test_threads_the_forge_would_not_give_still_land_the_round(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, exit_code=1, stderr="502")
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")

        transition = trial.walk(read_threads, _written(work).to(ReadThreads))

        assert isinstance(transition, AnswerGate)
        assert "could not read the threads" in transition.note

    @staticmethod
    def test_an_agent_that_dies_ends_the_cast(trial: Trial, work: Work) -> None:
        falling()
        trial.shell.replies(when=THREADS, stdout=_OPEN)

        assert trial.walk(read_threads, work.to(ReadThreads)) == work.abandoned(
            "the agent stopped mid-flight: boom"
        ).to(Chart)


class TestAskTriage:
    @staticmethod
    def test_every_item_is_shown_and_asked(trial: Trial, work: Work) -> None:
        second = _ITEM.model_copy(update={"thread": "PRRT_2", "action": "file"})
        trial.decide.answers(answer="it guards the empty case", when="1. *")
        trial.decide.answers(answer="", when="2. *")

        transition = trial.walk(ask_triage, AskTriage(work=work, items=[_ITEM, second]))

        assert isinstance(transition, AnswerThreads)
        assert transition.work == work
        # Each item's reading is fenced and the answer to it is not, so the
        # `what I want` line sits after the closing marker.
        closed = "--- END UNTRUSTED REVIEW DATA ---"
        assert (
            f"thread: PRRT_1\n{closed}\nwhat I want: it guards the empty case"
            in transition.prompt
        )
        assert (
            f"thread: PRRT_2\n{closed}\nwhat I want: file it, as the reading says"
            in transition.prompt
        )
        assert transition.threads == ["PRRT_1", "PRRT_2"]
        assert "2 outstanding — p1: 2, p2: 0, p3: 0, p4: 0" in trial.deltas[0]


class TestAnswerThreads:
    @staticmethod
    def test_the_writer_hands_its_answers_on(trial: Trial, work: Work) -> None:
        answered = Answered(items=[Answer(thread="PRRT_1", reply="guarded")])
        trial.coding.replies(answered)
        attended = _attended(work)
        told = AnswerThreads(work=attended, prompt="the triage", threads=["PRRT_1"])

        assert trial.walk(answer_threads, told) == PostAnswers(
            work=attended.charged(answer_threads.name),
            items=answered.items,
            threads=["PRRT_1"],
        )
        assert trial.coding.prompts == ["the triage"]
        assert "Edit" in str(trial.coding.calls[0].focus_options)

    @staticmethod
    def test_an_answer_in_the_wrong_shape_still_lands_what_it_changed(
        trial: Trial, work: Work
    ) -> None:
        trial.coding.replies("no idea, sorry")
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")
        told = AnswerThreads(work=work, prompt="x", threads=["PRRT_1"])

        transition = trial.walk(answer_threads, told)

        assert isinstance(transition, AnswerGate)
        assert "did not answer in the shape" in transition.note

    @staticmethod
    def test_an_agent_that_dies_ends_the_cast(trial: Trial, work: Work) -> None:
        falling()
        told = AnswerThreads(work=work, prompt="x", threads=[])

        assert trial.walk(answer_threads, told) == work.charged(
            answer_threads.name
        ).abandoned("the agent stopped mid-flight: boom").to(Chart)


class TestPostAnswers:
    @staticmethod
    def test_replies_settle_each_thread_and_read_again(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.shell.replies(when="gh api repos/*")
        trial.shell.replies(when=_RESOLVE)
        written = _written(work)

        assert trial.walk(
            post_answers, _answering(written, Answer(thread="PRRT_1", reply="guarded"))
        ) == written.to(ReadThreads)
        assert trial.shell.commands[1] == f"{_REPLY} -f body='{signed('guarded')}'"
        assert trial.shell.commands[2].endswith("-f id=PRRT_1")

    @staticmethod
    def test_an_issue_is_opened_and_named_in_the_reply(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.shell.replies(
            when="gh api repos/{owner}/{repo}/issues -X POST*",
            stdout='{"number": 9, "html_url": "https://github.com/o/r/issues/9"}',
        )
        trial.shell.replies(when="gh api repos/*")
        trial.shell.replies(when=_RESOLVE)
        filing = Answer(
            thread="PRRT_1", reply="filed", issue=IssueDraft(title="guard", body="x")
        )

        trial.walk(post_answers, _answering(_written(work), filing))

        assert trial.shell.commands[1] == (
            "gh api repos/{owner}/{repo}/issues -X POST -f title=guard"
            f" -f body='x\n\n{filed_for('PRRT_1')}'"
        )
        body = signed("filed\n\nFiled as https://github.com/o/r/issues/9")
        assert trial.shell.commands[2].endswith(f"-f body='{body}'")

    # Nothing settled, so another round would read the same thread back.
    @staticmethod
    def test_a_thread_nobody_triaged_is_skipped_and_said(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")
        written = _written(work)

        assert trial.walk(
            post_answers, _answering(written, Answer(thread="PRRT_9", reply="made up"))
        ) == written.to(AnswerGate)
        assert "a thread nobody triaged: PRRT_9" in trial.deltas[0]

    # The fixes are in the worktree whether or not the replies went up.
    @staticmethod
    def test_a_forge_that_refuses_still_lands_the_fixes(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.shell.replies(when="gh api repos/*", exit_code=1, stderr="403")
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")

        transition = trial.walk(
            post_answers,
            _answering(_written(work), Answer(thread="PRRT_1", reply="guarded")),
        )

        assert isinstance(transition, AnswerGate)
        assert "could not reply on thread PRRT_1" in transition.note


class TestAnswerGate:
    @staticmethod
    def test_a_green_gate_lands(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_GATE)

        assert trial.walk(answer_gate, work.to(AnswerGate)) == work.to(LandAnswers)

    @staticmethod
    def test_a_red_gate_is_repaired_in_the_answers_session(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(
            when=_GATE,
            exit_code=1,
            stdout="E501",
            stderr="[lint:ruff] ERROR task failed",
        )
        trial.coding.replies("fixed")

        assert trial.walk(answer_gate, work.to(AnswerGate)) == work.but(
            gate="mise run lint:ruff"
        ).charged(answer_gate.name).to(AnswerGate)

    @staticmethod
    def test_a_spent_budget_stands_the_branch_down(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=_GATE, exit_code=1, stdout="1 failed")
        spent = work.but(budgets={answer_gate.name: 3})

        assert trial.walk(answer_gate, spent.to(AnswerGate)) == spent.stopped_by(
            "`mise run pr-fix` is still red:\n1 failed"
        ).but(run=spent.run.but(seen=["1 failed"])).to(StandDown)


class TestLandAnswers:
    @staticmethod
    def test_the_answers_are_one_commit(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="git add -A*")

        assert trial.walk(land_answers, work.to(LandAnswers)) == work.committed().to(
            Tend
        )
        assert trial.shell.commands == [commit("chore: act on the review triage")]

    @staticmethod
    def test_a_commit_that_fails_is_set_aside(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="git add -A*", exit_code=1, stderr="gpg failed")

        assert trial.walk(land_answers, work.to(LandAnswers)) == work.but(
            note="could not commit the answers: could not commit: gpg failed"
        ).to(SetAside)


# The listing and git's preflight, the branch on the forge with one open
# thread, and the count at the end.
def _listed(trial: Trial) -> None:
    trial.shell.replies(
        when="git remote get-url origin", stdout="https://github.com/o/r.git\n"
    )
    trial.shell.replies(when="git config --get-urlmatch*", stdout="!gh auth\n")
    labels = [{"name": "pr::thermo"}, {"name": "v:guide:done"}]
    trial.shell.replies(
        when=LIST, stdout=listing(row(7, mergeable="MERGEABLE", labels=labels))
    )
    trial.shell.replies(when=board(), stdout=_GREEN_BOARD)


class TestWholeCast:
    # The cast that answers nothing still says what it left, and how to get
    # it answered.
    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_an_unattended_cast_leaves_the_threads_waiting(trial: Trial) -> None:
        _listed(trial)
        trial.shell.replies(when=THREADS, stdout=_OPEN)

        result = trial.cast(heal_mine, Heal())

        assert result.checked == []
        assert trial.steps == ["muster_mine", "survey", "survey", "chart"]
        assert trial.deltas[-1] == (
            "heal — 0 worked\n\n  (none)\n\n"
            "waiting for you, cast with --attended true:\n"
            "  #7 feature: 1 thread\n"
        )

    @staticmethod
    @pytest.mark.usefixtures("here")
    def test_an_attended_answer_triages_fixes_replies_and_pushes(trial: Trial) -> None:
        _listed(trial)
        trial.shell.replies(when=HERE, stdout="feature\n")
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True))
        )
        trial.shell.replies(when=_ISSUES, stdout="[]", always=True)
        trial.shell.replies(when=STATUS)
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")
        trial.shell.replies(when="git fetch*")
        trial.shell.replies(when="git checkout feature")
        trial.shell.replies(when="git merge --ff-only*")
        trial.coding.replies(TriageNotes(items=[_ITEM]), when=_READER)
        trial.decide.answers(answer="", when="1. *")
        trial.coding.replies(
            Answered(items=[Answer(thread="PRRT_1", reply="guarded")]), when=_WRITER
        )
        trial.shell.replies(when="gh api repos/*")
        trial.shell.replies(when=_RESOLVE)
        trial.shell.replies(when=_GATE)
        trial.shell.replies(when="git add -A*")
        trial.shell.replies(when="git push origin feature")
        trial.shell.replies(when=_AHEAD, stdout="0\n")

        result = trial.cast(answer, Heal(attended=True))

        assert [one.outcome for one in result.checked] == ["worked"]
        assert trial.steps == [
            "muster_this",
            "survey",
            "check_clean",
            "sync_branch",
            "tend",
            "settle_left",
            "read_threads",
            "ask_triage",
            "answer_threads",
            "post_answers",
            "read_threads",
            "answer_gate",
            "land_answers",
            "tend",
            "push_work",
            "tend",
            "finish_pr",
            "survey",
            "chart",
        ]
        commands = trial.shell.commands
        assert commands.index(commit("chore: act on the review triage")) < (
            commands.index("git push origin feature")
        )
