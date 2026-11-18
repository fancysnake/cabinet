"""The flags a ritual takes: a base that refuses the ones it does not know."""

from pydantic import BaseModel, ConfigDict


class Components(BaseModel):
    # A flag a cast does not know is an error, not a silent no-op.
    model_config = ConfigDict(extra="forbid")
