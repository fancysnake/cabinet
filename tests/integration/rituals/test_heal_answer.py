"""The answer task: finish what was left, triage, answer, post, gate, commit."""

import shlex

import pytest
from vekna.trial import Trial

from cabinet.gates.ritual.vekna.heal.answer import (
    answer_gate,
    answer_threads,
    approve_replies,
    ask_triage,
    land_answers,
    post_answers,
    read_threads,
    settle_left,
)
from cabinet.gates.ritual.vekna.heal.branch import tend
from cabinet.pacts.agent import UNTRUSTED_THREADS, Prompt
from cabinet.pacts.budgets import ROUNDS
from cabinet.pacts.heal import (
    AnswerGate,
    AnswerThreads,
    ApproveReplies,
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
    Comment,
    IssueDraft,
    Thread,
    TriageItem,
    TriageNotes,
    filed_for,
    settles,
    signed,
)
from cabinet.rituals.answer import answer
from cabinet.rituals.heal_mine import heal_mine
from cabinet.specs import MANY_THREADS
from tests.conftest import (
    HERE,
    LIST,
    STATUS,
    THREADS,
    board,
    comment,
    commit,
    fetches,
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
_DONE = "gh pr edit 7 --add-label v:answer:done"
_UNDONE = "gh pr edit 7 --remove-label v:answer:done"
_GATE = "CI=1 mise run pr-fix"
_READER = "Triage the open review threads*"
_WRITER = "Below is a triage*"
_ITEM = TriageItem(
    where="src/thing.py",
    raised="add a guard before the loop",
    left="an empty list crashes the run",
    what="the guard is missing",
    grounds="tested",
    proof="ran it with [] and got IndexError",
    size="small",
    files=1,
    risk="low",
    priority="p1",
    action="fix",
    thread="PRRT_1",
)
_GREEN_BOARD = '[{"total_count": 0, "check_runs": []}]'
_AHEAD = f'test feature = "$({HERE})" && git rev-list --count origin/feature..HEAD'


# The thread opener as the operator wrote it: the ritual resolves its own.
_MINE = comment(101, author="me", body="guard", mine=True)
# One somebody else opened, and the ritual's reply under it.
_THEIRS = comment(101, author="alice", body="guard")
_REPLIED = comment(102, author="me", body=ANSWERED, mine=True)


def _threads(*nodes: dict[str, object]) -> str:
    return threads_page(page(list(nodes)))


def _node(node_id: str, *, resolved: bool = False) -> dict[str, object]:
    guard = page([_MINE])
    return node(node_id, guard, resolved=resolved, path="src/thing.py", line=12)


_OPEN = _threads(_node("PRRT_1"))
# `_node("PRRT_1")` as the forge reads it.
_THREAD = Thread(
    id="PRRT_1",
    resolved=False,
    path="src/thing.py",
    line=12,
    comments=[Comment(id="101", author="me", body="guard", mine=True)],
)

_ITEM_URL = "https://github.com/o/r/pull/7#issuecomment-12"
# A review item posted as a plain comment, which the forge cannot resolve.
_PLAIN = Thread(
    id=_ITEM_URL,
    resolved=False,
    plain=True,
    comments=[Comment(id=_ITEM_URL, author="me", body="guard", mine=True)],
)


_ALICES = _THREAD.model_copy(
    update={"comments": [Comment(id="101", author="alice", body="guard")]}
)


def _configured(work: Work, **keys: bool | list[str]) -> Work:
    project = work.run.project.model_copy(update=keys)
    return work.but(run=work.run.model_copy(update={"project": project}))


def _attended(work: Work) -> Work:
    return work.but(run=work.run.model_copy(update={"attended": True}))


# A branch the writer has already been at, so a round with nothing more to do
# lands whatever it changed.
def _written(work: Work) -> Work:
    return _attended(work).charged(answer_threads.name)


def _answering(work: Work, *answers: Answer) -> PostAnswers:
    return PostAnswers(work=work, items=list(answers), threads=[_THREAD])


class TestTend:
    @staticmethod
    def test_answer_starts_with_what_an_earlier_cast_left(
        trial: Trial, work: Work
    ) -> None:
        answering = _attended(work).but(todos=["answer", "guide"])

        assert trial.walk(tend, answering.to(Tend)) == answering.but(
            todos=["guide"]
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
        assert _UNDONE not in trial.shell.commands

    # Open threads make the label a lie until the task ends with none.
    @staticmethod
    def test_a_branch_answered_before_takes_the_label_off(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.shell.replies(when=_ISSUES, stdout="[]", always=True)
        trial.shell.replies(when=_UNDONE)
        pr = work.pr.model_copy(update={"labels": ["v:answer:done"]})
        worn = work.model_copy(update={"pr": pr})

        assert trial.walk(settle_left, worn.to(SettleLeft)) == worn.to(ReadThreads)
        assert _UNDONE in trial.shell.commands

    # An earlier cast replied and then the forge failed to settle the thread.
    @staticmethod
    def test_a_thread_already_answered_is_settled(trial: Trial, work: Work) -> None:
        replied = page([_MINE, comment(102, body=ANSWERED, mine=True)])
        trial.shell.replies(when=THREADS, stdout=_threads(node("PRRT_1", replied)))
        trial.shell.replies(when=_RESOLVE)

        assert trial.walk(settle_left, work.to(SettleLeft)) == work.to(ReadThreads)
        assert trial.shell.commands[-1].endswith("-f id=PRRT_1")
        assert trial.deltas == ["feature: settled 1 threads an earlier cast left"]

    @staticmethod
    def test_a_settle_the_forge_refuses_leaves_the_task(
        trial: Trial, work: Work
    ) -> None:
        replied = page([_MINE, comment(102, body=ANSWERED, mine=True)])
        trial.shell.replies(when=THREADS, stdout=_threads(node("PRRT_1", replied)))
        trial.shell.replies(when=_RESOLVE, exit_code=1, stderr="502")

        transition = trial.walk(settle_left, work.to(SettleLeft))

        assert isinstance(transition, Tend)
        assert "could not resolve thread PRRT_1" in transition.note

    @staticmethod
    def test_a_thread_somebody_else_opened_is_left_open(
        trial: Trial, work: Work
    ) -> None:
        theirs = node("PRRT_1", page([_THEIRS, _REPLIED]))
        trial.shell.replies(when=THREADS, stdout=_threads(theirs))

        assert trial.walk(settle_left, work.to(SettleLeft)) == work.to(ReadThreads)
        assert not any("id=PRRT_1" in command for command in trial.shell.commands)
        assert not trial.deltas

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

    # The reply naming the issue is up and somebody wrote under it since: that
    # is a follow-up to read, not a reply to post again.
    @staticmethod
    def test_a_thread_already_naming_its_issue_is_not_told_twice(
        trial: Trial, work: Work
    ) -> None:
        url = "https://github.com/o/r/issues/9"
        followed = page(
            [
                _MINE,
                comment(102, body=signed(f"Filed as {url}"), mine=True),
                comment(103, body="why a new issue?"),
            ]
        )
        trial.shell.replies(when=THREADS, stdout=_threads(node("PRRT_1", followed)))
        filed = {
            "number": 9,
            "title": "guard",
            "url": url,
            "body": f"later\n\n{filed_for('PRRT_1')}",
            "labels": [],
        }
        trial.shell.replies(when=_ISSUES, stdout=listing(filed))
        trial.shell.replies(when=_ISSUES, stdout="[]")

        assert trial.walk(settle_left, work.to(SettleLeft)) == work.to(ReadThreads)
        assert not any("replies" in command for command in trial.shell.commands)
        assert not any("id=PRRT_1" in command for command in trial.shell.commands)
        assert not trial.deltas

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
            work=attended.charged(read_threads.name),
            items=[_ITEM],
            threads=[_THREAD],
            unsettled=1,
        )
        prompt = trial.coding.prompts[0]
        assert prompt.startswith("Triage the open review threads on pull request #7")
        assert "thread PRRT_1 (open)" in prompt
        assert "PRRT_2" not in prompt
        assert "UNTRUSTED" in prompt
        assert "Edit" not in str(trial.coding.calls[0].focus_options)
        assert trial.coding.calls[0].focus_options.skills == ["heal:untrusted-threads"]
        assert trial.coding.calls[0].model == "plan-model"
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

        transition = trial.walk(read_threads, batched.to(ReadThreads))

        assert isinstance(transition, AskTriage)
        assert transition.unsettled == len(["PRRT_1", "PRRT_2", "PRRT_3"])
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
        trial.shell.replies(when=_DONE)

        assert trial.walk(read_threads, work.to(ReadThreads)) == work.to(Tend)
        assert not trial.coding.prompts

    @staticmethod
    def test_nothing_open_labels_the_branch_answered(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads())
        trial.shell.replies(when=_DONE)

        trial.walk(read_threads, work.to(ReadThreads))

        assert _DONE in trial.shell.commands

    # Theirs to resolve: the reply under it is all the task owed.
    @staticmethod
    def test_a_thread_somebody_else_opened_is_done_once_replied_to(
        trial: Trial, work: Work
    ) -> None:
        theirs = node("PRRT_1", page([_THEIRS, _REPLIED]))
        trial.shell.replies(when=THREADS, stdout=_threads(theirs))
        trial.shell.replies(when=_DONE)

        trial.walk(read_threads, work.to(ReadThreads))

        assert _DONE in trial.shell.commands
        assert not trial.coding.prompts

    # The threads are settled whether or not the label went on.
    @staticmethod
    def test_a_label_the_forge_refuses_is_said(trial: Trial, work: Work) -> None:
        trial.shell.replies(when=THREADS, stdout=_threads())
        trial.shell.replies(when=_DONE, exit_code=1, stderr="no such label")

        assert trial.walk(read_threads, work.to(ReadThreads)) == work.but(
            note="could not label #7: no such label"
        ).to(Tend)

    # The rounds before this one changed the worktree, so what they did goes
    # to the gate whatever this round found.
    @staticmethod
    def test_nothing_open_after_a_round_is_the_gate(trial: Trial, work: Work) -> None:
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True))
        )
        trial.shell.replies(when=_DONE)
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
        trial.shell.replies(when=_DONE)
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
        trial.shell.replies(when=_DONE)
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

    # The reading is the agent's own word: an item for a thread nobody sent it
    # is dropped, and a reading of nothing else is no reading.
    @staticmethod
    def test_an_item_for_a_thread_never_sent_is_dropped(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        made_up = _ITEM.model_copy(update={"thread": "PRRT_9"})
        trial.coding.replies(TriageNotes(items=[made_up, _ITEM]))

        transition = trial.walk(read_threads, work.to(ReadThreads))

        assert isinstance(transition, AskTriage)
        assert transition.items == [_ITEM]

    @staticmethod
    def test_a_reading_of_threads_never_sent_found_nothing(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        made_up = _ITEM.model_copy(update={"thread": "PRRT_9"})
        trial.coding.replies(TriageNotes(items=[made_up]))

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
    def test_every_item_is_asked_as_a_card_most_urgent_first(
        trial: Trial, work: Work
    ) -> None:
        second = _ITEM.model_copy(
            update={"thread": "PRRT_2", "action": "file", "priority": "p3"}
        )
        other = _THREAD.model_copy(update={"id": "PRRT_2"})
        untriaged = _THREAD.model_copy(update={"id": "PRRT_3"})
        trial.decide.answers(
            answer="it guards the empty case", when="#7 pr 7 — thread 1 of 2\n*"
        )
        trial.decide.answers(
            answer="", when="#7 pr 7 — thread 2 of 2\n*Action:   file — *"
        )
        triage = AskTriage(
            work=work,
            items=[second, _ITEM],
            threads=[_THREAD, other, untriaged],
            unsettled=MANY_THREADS,
        )

        transition = trial.walk(ask_triage, triage)

        assert isinstance(transition, AnswerThreads)
        assert transition.work == work
        assert transition.unsettled == MANY_THREADS
        # Each item's reading is fenced and the answer to it is not, so the
        # `what I want` line sits after the closing marker.
        closed = "--- END UNTRUSTED REVIEW DATA ---"
        assert (
            f"thread: PRRT_1\n{closed}\nwhat I want: it guards the empty case"
            in transition.prompt.text
        )
        assert (
            f"thread: PRRT_2\n{closed}\nwhat I want: file it, as the reading says"
            in transition.prompt.text
        )
        assert transition.threads == [_THREAD, other]
        assert "Thread:   src/thing.py, raised by me" in transition.prompt.text
        assert trial.deltas == []

    @staticmethod
    def test_ok_takes_the_readings_proposal(trial: Trial, work: Work) -> None:
        trial.decide.answers(answer="ok")
        triage = AskTriage(work=work, items=[_ITEM], threads=[_THREAD], unsettled=1)

        transition = trial.walk(ask_triage, triage)

        assert isinstance(transition, AnswerThreads)
        assert (
            f"what I want: {_ITEM.action} it, as the reading says"
            in transition.prompt.text
        )


class TestAnswerThreads:
    @staticmethod
    def test_the_writer_hands_its_answers_on(trial: Trial, work: Work) -> None:
        answered = Answered(items=[Answer(thread="PRRT_1", reply="guarded")])
        trial.coding.replies(answered)
        attended = _attended(work)
        told = AnswerThreads(
            work=attended,
            prompt=Prompt(text="the triage", skills=(UNTRUSTED_THREADS,)),
            threads=[_THREAD],
            unsettled=MANY_THREADS - 1,
        )

        assert trial.walk(answer_threads, told) == PostAnswers(
            work=attended.charged(answer_threads.name),
            items=answered.items,
            threads=[_THREAD],
        )
        assert trial.coding.prompts == ["the triage"]
        assert trial.coding.calls[0].model == "fix-model"
        assert "Edit" in str(trial.coding.calls[0].focus_options)
        assert trial.coding.calls[0].focus_options.skills == ["heal:untrusted-threads"]

    @staticmethod
    def test_many_open_threads_go_to_the_escalated_model(
        trial: Trial, work: Work
    ) -> None:
        trial.coding.replies(Answered(items=[]))
        told = AnswerThreads(
            work=work,
            prompt=Prompt(text="x", skills=()),
            threads=[_THREAD],
            unsettled=MANY_THREADS,
        )

        trial.walk(answer_threads, told)

        assert trial.coding.calls[0].model == "escalated-model"

    @staticmethod
    def test_an_answer_in_the_wrong_shape_still_lands_what_it_changed(
        trial: Trial, work: Work
    ) -> None:
        trial.coding.replies("no idea, sorry")
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")
        told = AnswerThreads(
            work=work,
            prompt=Prompt(text="x", skills=()),
            threads=[_THREAD],
            unsettled=1,
        )

        transition = trial.walk(answer_threads, told)

        assert isinstance(transition, AnswerGate)
        assert "did not answer in the shape" in transition.note

    @staticmethod
    def test_an_agent_that_dies_ends_the_cast(trial: Trial, work: Work) -> None:
        falling()
        told = AnswerThreads(
            work=work, prompt=Prompt(text="x", skills=()), threads=[], unsettled=0
        )

        assert trial.walk(answer_threads, told) == work.charged(
            answer_threads.name
        ).abandoned("the agent stopped mid-flight: boom").to(Chart)


def _drafted(work: Work, *drafts: Answer) -> ApproveReplies:
    return ApproveReplies(work=work, drafts=list(drafts), threads=[_THREAD])


class TestApproveReplies:
    @staticmethod
    def test_a_project_that_asks_for_it_gets_the_replies_first(
        trial: Trial, work: Work
    ) -> None:
        draft = Answer(thread="PRRT_1", reply="guarded")
        trial.coding.replies(Answered(items=[draft]))
        asking = _configured(work, approve_replies=True)
        told = AnswerThreads(
            work=asking,
            prompt=Prompt(text="x", skills=()),
            threads=[_THREAD],
            unsettled=1,
        )

        assert trial.walk(answer_threads, told) == _drafted(
            asking.charged(answer_threads.name), draft
        )

    @staticmethod
    def test_a_return_posts_the_reply_as_drafted(trial: Trial, work: Work) -> None:
        trial.decide.answers(answer="", when="#7 pr 7 — reply to me — src/thing.py:12*")
        draft = Answer(thread="PRRT_1", reply="guarded")

        assert trial.walk(approve_replies, _drafted(work, draft)) == _answering(
            work, draft
        )
        assert (
            "\n\nguarded\n\nPress return or answer ok to post it"
            in trial.decide.prompts[0]
        )
        assert not trial.coding.prompts

    # Discord sends no empty reply, so a word takes the draft too.
    @staticmethod
    def test_ok_posts_the_reply_as_drafted(trial: Trial, work: Work) -> None:
        trial.decide.answers(answer=" OK ")
        draft = Answer(thread="PRRT_1", reply="guarded")

        assert trial.walk(approve_replies, _drafted(work, draft)) == _answering(
            work, draft
        )
        assert not trial.coding.prompts

    # The redraft names another thread, and the reply stays under its own. The
    # reply taken beside it is not asked about again.
    @staticmethod
    def test_what_you_changed_is_redrafted_and_asked_again(
        trial: Trial, work: Work
    ) -> None:
        trial.decide.answers(answer="shorter", when="*\n\nguarded, at length\n\n*")
        trial.decide.answers(answer="", when="*\n\nfine\n\n*")
        trial.coding.replies(Answer(thread="PRRT_9", reply="guarded"))
        long = Answer(thread="PRRT_1", reply="guarded, at length")
        fine = Answer(thread="PRRT_2", reply="fine")
        other = _THREAD.model_copy(update={"id": "PRRT_2"})
        drafted = ApproveReplies(
            work=work, drafts=[long, fine], threads=[_THREAD, other]
        )

        assert trial.walk(approve_replies, drafted) == ApproveReplies(
            work=work.charged(approve_replies.name),
            drafts=[Answer(thread="PRRT_1", reply="guarded")],
            items=[fine],
            threads=[_THREAD, other],
        )
        assert "guarded, at length" in trial.coding.prompts[0]
        assert "what I want changed: shorter" in trial.coding.prompts[0]

    # Taking the last one hands the budget back for the next round.
    @staticmethod
    def test_a_redraft_taken_is_posted_with_the_rest(trial: Trial, work: Work) -> None:
        trial.decide.answers(answer="")
        fine = Answer(thread="PRRT_2", reply="fine")
        redraft = Answer(thread="PRRT_1", reply="guarded")
        again = _drafted(work.charged(approve_replies.name), redraft).model_copy(
            update={"items": [fine]}
        )

        assert trial.walk(approve_replies, again) == _answering(work, fine, redraft)

    @staticmethod
    def test_a_redraft_in_the_wrong_shape_leaves_the_draft_to_ask_again(
        trial: Trial, work: Work
    ) -> None:
        trial.decide.answers(answer="shorter")
        trial.coding.replies("no idea, sorry")
        draft = Answer(thread="PRRT_1", reply="guarded")

        assert trial.walk(approve_replies, _drafted(work, draft)) == _drafted(
            work.charged(approve_replies.name), draft
        )
        assert "did not answer in the shape" in trial.deltas[-1]

    # The bound is spent: nothing is redrafted, and nothing you did not take
    # is posted.
    @staticmethod
    def test_a_reply_still_not_taken_at_the_bound_is_not_posted(
        trial: Trial, work: Work
    ) -> None:
        trial.decide.answers(answer="shorter")
        spent = work
        for _ in range(work.run.bound):
            spent = spent.charged(approve_replies.name)
        draft = Answer(thread="PRRT_1", reply="guarded")

        assert trial.walk(approve_replies, _drafted(spent, draft)) == _answering(work)
        assert "No redrafts are left" in trial.decide.prompts[0]
        assert not trial.coding.prompts
        assert "thread PRRT_1 gets no reply and stays open" in trial.deltas[0]

    @staticmethod
    def test_an_answer_to_a_thread_nobody_triaged_is_not_asked_about(
        trial: Trial, work: Work
    ) -> None:
        made_up = Answer(thread="PRRT_9", reply="made up")

        assert trial.walk(approve_replies, _drafted(work, made_up)) == _answering(
            work, made_up
        )
        assert not trial.decide.prompts

    @staticmethod
    def test_an_agent_that_dies_ends_the_cast(trial: Trial, work: Work) -> None:
        falling()
        trial.decide.answers(answer="shorter")
        draft = Answer(thread="PRRT_1", reply="guarded")

        assert trial.walk(approve_replies, _drafted(work, draft)) == work.abandoned(
            "the agent stopped mid-flight: boom"
        ).to(Chart)


class TestPostAnswers:
    @staticmethod
    def test_replies_settle_each_thread_and_read_again(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="gh api repos/*")
        trial.shell.replies(when=_RESOLVE)
        written = _written(work)

        assert trial.walk(
            post_answers, _answering(written, Answer(thread="PRRT_1", reply="guarded"))
        ) == written.to(ReadThreads)
        assert trial.shell.commands[0] == f"{_REPLY} -f body='{signed('guarded')}'"
        assert trial.shell.commands[1].endswith("-f id=PRRT_1")

    # No reply for the resolve is scripted, so issuing one would fail the walk.
    @staticmethod
    def test_a_thread_somebody_else_opened_gets_the_reply_and_stays_open(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="gh api repos/*")
        written = _written(work)
        answering = PostAnswers(
            work=written,
            items=[Answer(thread="PRRT_1", reply="guarded")],
            threads=[_ALICES],
        )

        assert trial.walk(post_answers, answering) == written.to(ReadThreads)
        assert trial.shell.commands == [f"{_REPLY} -f body='{signed('guarded')}'"]

    @staticmethod
    def test_a_thread_a_named_bot_opened_is_resolved(trial: Trial, work: Work) -> None:
        trial.shell.replies(when="gh api repos/*")
        trial.shell.replies(when=_RESOLVE)
        written = _configured(_written(work), bots=["alice"])
        answering = PostAnswers(
            work=written,
            items=[Answer(thread="PRRT_1", reply="guarded")],
            threads=[_ALICES],
        )

        assert trial.walk(post_answers, answering) == written.to(ReadThreads)
        assert trial.shell.commands[1].endswith("-f id=PRRT_1")

    @staticmethod
    def test_an_issue_is_opened_and_named_in_the_reply(
        trial: Trial, work: Work
    ) -> None:
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

        assert trial.shell.commands[0] == (
            "gh api repos/{owner}/{repo}/issues -X POST -f title=guard"
            f" -f body='x\n\n{filed_for('PRRT_1')}'"
        )
        body = signed("filed\n\nFiled as https://github.com/o/r/issues/9")
        assert trial.shell.commands[1].endswith(f"-f body='{body}'")

    # Nothing settled, so another round would read the same thread back.
    @staticmethod
    def test_a_thread_nobody_triaged_is_skipped_and_said(
        trial: Trial, work: Work
    ) -> None:
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
        trial.shell.replies(when="gh api repos/*", exit_code=1, stderr="403")
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")

        transition = trial.walk(
            post_answers,
            _answering(_written(work), Answer(thread="PRRT_1", reply="guarded")),
        )

        assert isinstance(transition, AnswerGate)
        assert "could not reply on thread PRRT_1" in transition.note

    # A plain comment is neither replied under nor resolved: one comment naming
    # it is both.
    @staticmethod
    def test_a_plain_item_is_settled_by_one_comment_naming_it(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="gh pr comment*")
        written = _written(work)
        answering = PostAnswers(
            work=written,
            items=[Answer(thread=_ITEM_URL, reply="guarded")],
            threads=[_PLAIN],
        )

        assert trial.walk(post_answers, answering) == written.to(ReadThreads)
        said = f"guarded\n\nSettles {_ITEM_URL}\n\n{settles(_ITEM_URL)}"
        assert trial.shell.commands == [
            f"gh pr comment 7 --body {shlex.quote(signed(said))}"
        ]

    @staticmethod
    def test_a_comment_the_forge_refuses_still_lands_the_fixes(
        trial: Trial, work: Work
    ) -> None:
        trial.shell.replies(when="gh pr comment*", exit_code=1, stderr="403")
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")
        answering = PostAnswers(
            work=_written(work),
            items=[Answer(thread=_ITEM_URL, reply="guarded")],
            threads=[_PLAIN],
        )

        transition = trial.walk(post_answers, answering)

        assert isinstance(transition, AnswerGate)
        assert "could not comment on #7" in transition.note


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
    fetches(trial)
    labels = [{"name": "pr::thermo"}, {"name": "v:guide:done"}]
    trial.shell.replies(when=LIST, stdout=listing(row(7, labels=labels)), always=True)
    trial.shell.replies(when=board(), stdout=_GREEN_BOARD, always=True)


class TestWholeCast:
    # The cast that answers nothing still says what it left, and how to get
    # it answered.
    @staticmethod
    @pytest.mark.usefixtures("here", "holds_base")
    def test_an_unattended_cast_leaves_the_threads_waiting(trial: Trial) -> None:
        _listed(trial)
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.decide.attended = False

        result = trial.cast(heal_mine, Heal())

        assert result.queued == []
        assert trial.steps == ["muster_mine", "summon", "summon", "handoff"]
        assert trial.deltas[-1] == (
            "heal — 0 queued\n\n  (none)\n\n"
            "waiting for you, cast without --unattended:\n"
            "  #7 feature: 1 thread\n"
        )

    @staticmethod
    @pytest.mark.usefixtures("here", "holds_base")
    def test_an_attended_answer_triages_fixes_replies_and_pushes(trial: Trial) -> None:
        _listed(trial)
        trial.shell.replies(when=HERE, stdout="feature\n")
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.shell.replies(when=THREADS, stdout=_OPEN)
        trial.shell.replies(
            when=THREADS, stdout=_threads(_node("PRRT_1", resolved=True)), always=True
        )
        trial.shell.replies(when=_ISSUES, stdout="[]", always=True)
        trial.shell.replies(when=STATUS)
        trial.shell.replies(when=STATUS, stdout=" M a.py\n")
        fetches(trial)
        trial.shell.replies(when="git checkout feature")
        trial.shell.replies(when="git merge --ff-only*")
        trial.coding.replies(TriageNotes(items=[_ITEM]), when=_READER)
        trial.decide.answers(answer="", when="#7 *")
        trial.coding.replies(
            Answered(items=[Answer(thread="PRRT_1", reply="guarded")]), when=_WRITER
        )
        trial.shell.replies(when="gh api repos/*")
        trial.shell.replies(when=_RESOLVE)
        trial.shell.replies(when=_DONE)
        trial.shell.replies(when=_GATE)
        trial.shell.replies(when="git add -A*")
        trial.shell.replies(when="git push origin feature")
        trial.shell.replies(when=_AHEAD, stdout="0\n")

        result = trial.cast(answer, Heal())

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
            "resurvey",
            "finish_pr",
            "survey",
            "chart",
        ]
        commands = trial.shell.commands
        assert commands.index(commit("chore: act on the review triage")) < (
            commands.index("git push origin feature")
        )
