"""What to do about a task that came back, on whichever loop is asking.

Three loops share these beats: run the gate, read what it said, and either
move on, stand the branch down, or pay for one more attempt. The loops differ
in what they run and where they go next; the rule for choosing between the
three does not, so it is written once here and the steps only route on it.
"""

from typing_extensions import override

from cabinet.pacts.repairs import Attempt, Fixed, Repair, Ruling, Stalled
from cabinet.pacts.services import PromptsProtocol, RepairsProtocol, VerdictsProtocol

# What the report says where the attempt was the operator's to approve and
# they said no.
DECLINED = "was not tried again, as you decided"


class Repairs(RepairsProtocol):
    def __init__(self, prompts: PromptsProtocol, verdicts: VerdictsProtocol) -> None:
        self._prompts = prompts
        self._verdicts = verdicts

    @override
    def ruling(self, attempt: Attempt) -> Ruling:
        report = self._measured(attempt)
        missing = self._verdicts.uncovered(report) if attempt.covering else False
        # A coverage task naming missing lines exits 0, so the exit code is
        # only half the answer wherever there is a report to read.
        if not missing and not attempt.ran.exit_code:
            return Fixed(whole=attempt.gate == attempt.whole)
        said = self._verdicts.verdict(attempt.ran)
        # Only a red gate is worth remembering across branches: what lines a
        # branch left uncovered is that branch's own business, and two
        # branches missing lines in the same file look identical from here.
        seen = attempt.seen if missing else [*attempt.seen, said]
        # Asked before the first repair and not after, so this reads "the
        # branch arrived broken the same way", never "the agent failed to fix
        # it twice". The memory it is read against is the one the run came in
        # with, which is why nothing has been added to it yet.
        if (
            not attempt.spent
            and not missing
            and self._verdicts.already_seen(said, attempt.seen)
        ):
            reason = f"`{attempt.gate}` is red as it already was:\n{said}"
            return Stalled(reason=reason, seen=attempt.seen)
        left = "still reports missing lines" if missing else "is still red"
        if attempt.spent >= attempt.bound:
            return Stalled(reason=f"`{attempt.gate}` {left}:\n{said}", seen=seen)
        return Repair(
            asking=self._asking(attempt, report=report, missing=missing),
            next_gate=self._next_gate(attempt, missing=missing),
            seen=seen,
            declined=f"`{attempt.gate}` {DECLINED}:\n{said}",
        )

    # The work list, whole: a tail of a coverage report is an agent asked to
    # cover lines it was never shown. Nothing to read on a loop that is not
    # measuring coverage.
    def _measured(self, attempt: Attempt) -> str:
        if not attempt.covering:
            return ""
        return self._verdicts.coverage_report(attempt.ran)

    # Two different jobs down one budget, because they are the same loop going
    # round: lines left uncovered are written up as tests, and a task that
    # will not pass at all is repaired like any other red gate.
    def _asking(self, attempt: Attempt, *, report: str, missing: bool) -> str:
        if missing:
            return self._prompts.cover_gap(
                attempt.project, report, partial=attempt.gate != attempt.whole
            )
        return self._prompts.fix_gates(
            attempt.project, self._verdicts.said(attempt.ran), gate=attempt.gate
        )

    # The one task worth running next round rather than the whole chain. Lines
    # are re-measured without the slow suites: what an agent writes for a gap
    # is a test, and the fast suite is the one that runs it.
    def _next_gate(self, attempt: Attempt, *, missing: bool) -> str:
        if missing:
            return attempt.project.fast_coverage
        narrowed = self._verdicts.narrowed(attempt.ran)
        if attempt.covering:
            return narrowed or attempt.project.fast_coverage
        return narrowed
