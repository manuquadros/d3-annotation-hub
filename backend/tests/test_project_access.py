"""Integration tests for project-membership gating on read endpoints (TICKET-24).

Three authenticated read endpoints previously leaked a foreign project's data to
any logged-in user: ``GET /projects/{id}/properties`` and the ``project_id`` scope
of ``GET /entity/search`` expose that project's pending proposed properties/
entities (curies/labels coined privately inside the project), and ``GET
/reference/`` let a non-member enumerate a project's references. These tests pin
down that all three now require membership. Shared ``db``/``client``/``login``/
``make_user``/``make_project`` fixtures live in ``conftest.py``.
"""

import pytest
from d3textdb.schema import Reference
from d3textdb.schema import User as DbUser

_PMID = 32000001
_MEMBER_EMAIL = "member@access-test.example"
_MEMBER_PASSWORD = "member-secret"
_OUTSIDER_EMAIL = "outsider@access-test.example"
_OUTSIDER_PASSWORD = "outsider-secret"

_PROP_LABEL = "secret-relation"
_PROP_CURIE = "SECRET:REL1"


@pytest.fixture()
def setup(db, make_user, make_project):
    """A private project with a member, a reference, and a proposed property.

    Returns the project id, both users' auth headers, and the reference id.
    """
    member_auth = make_user(_MEMBER_EMAIL, _MEMBER_PASSWORD)
    outsider_auth = make_user(_OUTSIDER_EMAIL, _OUTSIDER_PASSWORD)

    project_id = make_project("Private Project", required_annotators=1)
    member = db.get_user(_MEMBER_EMAIL)
    db.add_project_member(project_id, member.user_id, "annotator")

    ref_id = db.store_reference(
        Reference(
            pubmed_id=_PMID,
            authors="Doe J",
            title="Private article",
            journal="Test Journal",
            volume="1",
            pages="1-10",
            year=2024,
            abstract="Short abstract.",
        )
    )
    db.add_reference_to_project(project_id, ref_id)

    db.store_proposed_property(project_id, _PROP_LABEL, _PROP_CURIE)

    return {
        "project_id": project_id,
        "member_auth": member_auth,
        "outsider_auth": outsider_auth,
        "ref_id": ref_id,
    }


class TestProjectProperties:
    def test_member_reads_proposed_properties(self, setup, client):
        r = client.get(
            f"/projects/{setup['project_id']}/properties",
            headers=setup["member_auth"],
        )
        assert r.status_code == 200, r.text
        assert _PROP_CURIE in {p["curie"] for p in r.json()}

    def test_non_member_is_forbidden(self, setup, client):
        r = client.get(
            f"/projects/{setup['project_id']}/properties",
            headers=setup["outsider_auth"],
        )
        assert r.status_code == 403

    def test_unauthenticated_is_rejected(self, setup, anon_client):
        r = anon_client.get(f"/projects/{setup['project_id']}/properties")
        assert r.status_code == 401


class TestEntitySearchProjectScope:
    def test_member_may_scope_to_project(self, setup, client):
        r = client.get(
            f"/entity/search?q=coli&project_id={setup['project_id']}",
            headers=setup["member_auth"],
        )
        assert r.status_code == 200, r.text

    def test_non_member_scope_is_forbidden(self, setup, client):
        r = client.get(
            f"/entity/search?q=coli&project_id={setup['project_id']}",
            headers=setup["outsider_auth"],
        )
        assert r.status_code == 403

    def test_unscoped_search_stays_open(self, setup, client):
        """Without a project scope the search exposes no per-project data."""
        r = client.get("/entity/search?q=coli", headers=setup["outsider_auth"])
        assert r.status_code == 200, r.text


class TestReferenceFetch:
    def test_member_reads_reference(self, setup, client):
        r = client.get(
            f"/reference/?ref_identifier={_PMID}"
            f"&project_id={setup['project_id']}",
            headers=setup["member_auth"],
        )
        assert r.status_code == 200, r.text

    def test_non_member_is_forbidden(self, setup, client):
        r = client.get(
            f"/reference/?ref_identifier={_PMID}"
            f"&project_id={setup['project_id']}",
            headers=setup["outsider_auth"],
        )
        assert r.status_code == 403

    def test_unauthenticated_is_rejected(self, setup, anon_client):
        r = anon_client.get(
            f"/reference/?ref_identifier={_PMID}"
            f"&project_id={setup['project_id']}"
        )
        assert r.status_code == 401
