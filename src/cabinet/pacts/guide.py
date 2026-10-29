"""The smoke-test guide: what the agent writes, and how its comment is found."""

from typing import Annotated

from pydantic import BaseModel, StringConstraints

# Where the guide comment says it is the guide: hidden in the comment, so the
# next one edits it rather than posting another.
GUIDE_MARK = "<!-- cabinet:guide -->"


# The smoke-test instructions, as markdown. Never empty: a blank comment is
# an agent that read badly, not a guide.
class Guide(BaseModel):
    body: Annotated[str, StringConstraints(strip_whitespace=True, min_length=1)]
