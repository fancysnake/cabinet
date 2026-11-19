"""Thread answers, and the issues they were filed as."""

from cabinet.pacts.issues import Issue
from cabinet.pacts.threads import (
    ANSWERED,
    ITEM,
    Comment,
    Remark,
    Thread,
    filed_as,
    filed_for,
    remarked,
    settles,
)


def _thread(*bodies: str, mine: bool = True) -> Thread:
    comments = [
        Comment(id=str(n), author="me", body=b, mine=mine) for n, b in enumerate(bodies)
    ]
    return Thread(id="PRRT_1", resolved=False, comments=comments)


class TestRaisedBy:
    @staticmethod
    def test_the_first_comments_author_raised_it() -> None:
        assert _thread("guard", "no").raised_by == "me"

    @staticmethod
    def test_a_thread_without_comments_was_raised_by_nobody() -> None:
        assert not _thread().raised_by


class TestAnswered:
    @staticmethod
    def test_the_last_word_carrying_the_mark_is_answered() -> None:
        assert _thread("guard", f"done\n\n{ANSWERED}").answered

    @staticmethod
    def test_a_word_after_the_answer_reopens_it() -> None:
        assert not _thread(ANSWERED, "no").answered

    @staticmethod
    def test_a_thread_without_comments_is_not_answered() -> None:
        assert not _thread().answered

    @staticmethod
    def test_a_mark_someone_else_wrote_is_not_an_answer() -> None:
        assert not _thread(ANSWERED, mine=False).answered


class TestFiledAs:
    @staticmethod
    def test_the_issue_naming_the_thread_is_found() -> None:
        other = Issue(
            number=1, title="t", url="u1", body=filed_for("PRRT_2"), mine=True
        )
        filed = Issue(
            number=2, title="t", url="u2", body=f"x\n\n{filed_for('PRRT_1')}", mine=True
        )

        assert filed_as([other, filed], "PRRT_1") == filed

    @staticmethod
    def test_no_issue_naming_the_thread_is_none() -> None:
        assert filed_as([Issue(number=1, title="t", url="u")], "PRRT_1") is None

    @staticmethod
    def test_an_issue_someone_else_opened_is_none() -> None:
        forged = Issue(number=1, title="t", url="u", body=filed_for("PRRT_1"))

        assert filed_as([forged], "PRRT_1") is None


_URL = "https://github.com/o/r/pull/7#issuecomment-12"
_ITEM = f"## Quality review\n\nthe docs are stale\n\n{ITEM}"


def _mine(body: str, ref: str = _URL) -> Remark:
    return Remark(ref=ref, author="me", body=body, mine=True)


class TestRemarked:
    @staticmethod
    def test_a_review_item_of_yours_is_an_open_plain_thread() -> None:
        assert remarked([_mine(_ITEM)]) == [
            Thread(
                id=_URL,
                resolved=False,
                plain=True,
                comments=[Comment(id=_URL, author="me", body=_ITEM, mine=True)],
            )
        ]

    @staticmethod
    def test_a_comment_of_yours_settling_it_settles_it() -> None:
        reply = _mine(f"fixed\n\n{settles(_URL)}", ref=f"{_URL}9")

        [thread] = remarked([_mine(_ITEM), reply])

        assert thread.resolved

    # The heading is for the reader: renaming it neither drops an item nor
    # reopens one.
    @staticmethod
    def test_the_heading_is_not_what_makes_an_item() -> None:
        item = _mine(f"## Another title\n\nstale\n\n{ITEM}")

        assert len(remarked([item])) == 1

    # Anyone can type a mark.
    @staticmethod
    def test_somebody_elses_comment_neither_opens_nor_settles() -> None:
        theirs = Remark(ref=f"{_URL}9", author="reviewer", body=_ITEM)
        said = Remark(ref=f"{_URL}8", author="reviewer", body=settles(_URL))

        [thread] = remarked([_mine(_ITEM), theirs, said])

        assert not thread.resolved

    @staticmethod
    def test_a_comment_without_the_mark_is_not_a_review_item() -> None:
        assert remarked([_mine("## Quality review\n\nfine")]) == []

    # One URL is the start of another: `…-12` opens `…-123`.
    @staticmethod
    def test_a_reply_settling_a_longer_reference_settles_nothing() -> None:
        reply = _mine(f"fixed\n\n{settles(_URL + '3')}", ref=f"{_URL}9")

        [thread] = remarked([_mine(_ITEM), reply])

        assert not thread.resolved
