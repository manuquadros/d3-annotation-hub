"""The string-valued schema enums and their serialized forms.

``Verdict`` reaches the frontend through ``VerdictBody`` in the public API
schema and ``PdfIngestStatus`` is re-exported from the backend, so the values
these members render as are a wire contract, not an implementation detail.
"""

import json

import pytest
from pydantic import BaseModel
from sqlalchemy.dialects import sqlite

from d3textdb.schema import (
    CurationDecision,
    PdfIngestJob,
    PdfIngestStatus,
    Verdict,
)

_MEMBERS = list(Verdict) + list(PdfIngestStatus)


@pytest.mark.parametrize("member", _MEMBERS)
def test_member_renders_as_its_bare_value(member):
    """Interpolating a member yields the value, not ``Class.member``."""
    assert str(member) == member.value
    assert f"{member}" == member.value
    # The legacy interpolation forms are the point of this test, not an
    # oversight: each one routes through a different dunder.
    assert "{}".format(member) == member.value  # noqa: UP032
    assert "%s" % member == member.value  # noqa: UP031


@pytest.mark.parametrize("member", _MEMBERS)
def test_member_serializes_as_its_bare_value(member):
    assert json.dumps(member) == json.dumps(member.value)
    assert member == member.value
    assert hash(member) == hash(member.value)


@pytest.mark.parametrize(
    ("column", "member"),
    [(CurationDecision.__table__.c.verdict, m) for m in Verdict]
    + [(PdfIngestJob.__table__.c.status, m) for m in PdfIngestStatus],
)
def test_member_round_trips_through_its_column_as_its_value(column, member):
    dialect = sqlite.dialect()
    bind = column.type.bind_processor(dialect)
    result = column.type.result_processor(dialect, None)

    stored = bind(member) if bind else member
    assert stored == member.value
    assert (result(stored) if result else stored) is member


def test_verdict_serializes_as_a_bare_string_through_pydantic():
    class Body(BaseModel):
        verdict: Verdict

    assert Body(verdict=Verdict.accepted).model_dump_json() == (
        '{"verdict":"accepted"}'
    )
    assert Body.model_json_schema()["$defs"]["Verdict"] == {
        "enum": ["accepted", "rejected"],
        "title": "Verdict",
        "type": "string",
    }
