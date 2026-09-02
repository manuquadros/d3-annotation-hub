"""Integration tests for ``POST /save/`` identity and project enforcement.

The save endpoint authenticates the caller but receives the annotation body as
client-supplied JSON that carries its own ``user`` and ``project_id``. These
tests pin down that the endpoint (a) persists under the *authenticated*
identity regardless of the client-supplied user, and (b) refuses to write into
a project the caller doesn't belong to. Shared ``db``/``client``/``login``
fixtures live in ``conftest.py``.
"""

import pytest
from d3textdb.schema import Reference
from d3textdb.schema import User as DbUser
from fastapi.testclient import TestClient

_PMID = 31000001
_ALICE_EMAIL = "alice@save-test.example"
_ALICE_PASSWORD = "alice-secret"
_BOB_EMAIL = "bob@save-test.example"
_BOB_PASSWORD = "bob-secret"
_CURATOR_EMAIL = "curator@save-test.example"
_CURATOR_PASSWORD = "curator-secret"

_SUBJECT = "TEST:bacterium"
_OBJECT = "TEST:enzyme"


@pytest.fixture()
def setup(db, make_project):
    """Alice + curator annotate project A; Bob and project B are outsiders.

    Returns a dict of ids/emails: ``alice_id``, ``bob_id``, ``project_a``,
    ``project_b``, ``ref_id``.
    """
    alice_id = db.create_user(DbUser(email=_ALICE_EMAIL), _ALICE_PASSWORD)
    bob_id = db.create_user(DbUser(email=_BOB_EMAIL), _BOB_PASSWORD)
    curator_id = db.create_user(DbUser(email=_CURATOR_EMAIL), _CURATOR_PASSWORD)

    project_a = make_project("Project A", required_annotators=1)
    db.add_project_member(project_a, alice_id, "annotator")
    db.add_project_member(project_a, curator_id, "curator")

    # Project B has Bob only; Alice is a stranger to it.
    project_b = make_project("Project B", required_annotators=1)
    db.add_project_member(project_b, bob_id, "annotator")

    ref = Reference(
        pubmed_id=_PMID,
        authors="Doe J",
        title="Save article",
        journal="Test Journal",
        volume="1",
        pages="1-10",
        year=2024,
        abstract="Short abstract.",
    )
    ref_id = db.store_reference(ref)
    db.add_reference_to_project(project_a, ref_id)
    return {
        "alice_id": alice_id,
        "bob_id": bob_id,
        "project_a": project_a,
        "project_b": project_b,
        "ref_id": ref_id,
    }


def _completed_payload(
    client: TestClient, auth: dict, project_id: int, ref_id: int
) -> dict:
    """Fetch the reference and build a completed annotation payload for it."""
    r = client.get(
        f"/reference/?ref_identifier={_PMID}&project_id={project_id}",
        headers=auth,
    )
    assert r.status_code == 200, r.text
    ann = r.json()

    ann["entities"] = [
        {
            "entity_id": _SUBJECT,
            "preferred_name": "E. coli",
            "kind": "Bacterium",
            "confirmed": True,
        },
        {
            "entity_id": _OBJECT,
            "preferred_name": "Xylanase",
            "kind": "Enzyme",
            "confirmed": True,
        },
    ]
    ann["pointers"] = [
        {
            "reference_id": ref_id,
            "entity_id": _SUBJECT,
            "offset": 5,
            "length": 7,
        },
        {
            "reference_id": ref_id,
            "entity_id": _OBJECT,
            "offset": 20,
            "length": 8,
        },
    ]
    ann["relations"] = []
    ann["completed"] = True
    # store_reference upserts on (pubmed_id, doi), so the PK must be absent.
    ann["reference"] = {
        k: v for k, v in ann["reference"].items() if k != "reference_id"
    }
    return ann


class TestSaveIdentity:
    def test_completion_is_attributed_to_the_authenticated_user(
        self, setup, client, login
    ):
        """Alice forging Bob's user_id still lands the snapshot under Alice."""
        alice_auth = login(_ALICE_EMAIL, _ALICE_PASSWORD)
        payload = _completed_payload(
            client, alice_auth, setup["project_a"], setup["ref_id"]
        )
        payload["user"]["user_id"] = str(setup["bob_id"])
        payload["user"]["email"] = _BOB_EMAIL

        r = client.post(
            "/save/",
            json=payload,
            headers=alice_auth,
        )
        assert r.status_code == 200, r.text

        curator_auth = login(_CURATOR_EMAIL, _CURATOR_PASSWORD)
        r = client.get(
            f"/projects/{setup['project_a']}/curation/"
            f"{setup['ref_id']}/snapshots",
            headers=curator_auth,
        )
        assert r.status_code == 200, r.text
        snapshots = r.json()["snapshots"]
        assert len(snapshots) == 1
        assert snapshots[0]["email"] == _ALICE_EMAIL
        assert snapshots[0]["user_id"] == str(setup["alice_id"])
        assert snapshots[0]["user_id"] != str(setup["bob_id"])

    def test_member_can_save_their_own_annotation(self, setup, client, login):
        alice_auth = login(_ALICE_EMAIL, _ALICE_PASSWORD)
        payload = _completed_payload(
            client, alice_auth, setup["project_a"], setup["ref_id"]
        )
        r = client.post(
            "/save/",
            json=payload,
            headers=alice_auth,
        )
        assert r.status_code == 200, r.text


class TestSaveProjectScope:
    def test_saving_into_a_non_member_project_is_forbidden(
        self, setup, client, login
    ):
        """Alice cannot write into project B, where she has no role."""
        alice_auth = login(_ALICE_EMAIL, _ALICE_PASSWORD)
        payload = _completed_payload(
            client, alice_auth, setup["project_a"], setup["ref_id"]
        )
        payload["project_id"] = setup["project_b"]

        r = client.post(
            "/save/",
            json=payload,
            headers=alice_auth,
        )
        assert r.status_code == 403, r.text

    def test_unauthenticated_save_is_rejected(self, anon_client):
        # Auth is enforced before body validation, so an empty body still 401s.
        r = anon_client.post("/save/", json={})
        assert r.status_code == 401, r.text


class TestSaveBodyValidation:
    """Every part of the body is validated, nested objects included.

    The nested pointers, relations and reference used to be typed with the
    SQLModel tables, which skip Pydantic validation, so a corrupt one reached
    the database instead of being refused here.
    """

    def _bad(self, client, auth, payload) -> None:
        r = client.post("/save/", json=payload, headers=auth)
        assert r.status_code == 422, r.text

    def test_a_malformed_annotation_is_rejected_at_the_boundary(
        self, setup, client, login
    ):
        """The body is validated by FastAPI, so a bad field is a 422.

        Deserialising it inside the handler instead surfaced the same input as
        an unhandled ValidationError.
        """
        alice_auth = login(_ALICE_EMAIL, _ALICE_PASSWORD)
        payload = _completed_payload(
            client, alice_auth, setup["project_a"], setup["ref_id"]
        )
        payload["project_id"] = "not-a-project"

        self._bad(client, alice_auth, payload)

    def test_a_non_numeric_pointer_offset_is_rejected(
        self, setup, client, login
    ):
        alice_auth = login(_ALICE_EMAIL, _ALICE_PASSWORD)
        payload = _completed_payload(
            client, alice_auth, setup["project_a"], setup["ref_id"]
        )
        payload["pointers"][0]["offset"] = "halfway"

        self._bad(client, alice_auth, payload)

    def test_a_pointer_field_outside_the_enum_is_rejected(
        self, setup, client, login
    ):
        alice_auth = login(_ALICE_EMAIL, _ALICE_PASSWORD)
        payload = _completed_payload(
            client, alice_auth, setup["project_a"], setup["ref_id"]
        )
        payload["pointers"][0]["field"] = "footnote"

        self._bad(client, alice_auth, payload)

    def test_a_pointer_missing_its_entity_is_rejected(
        self, setup, client, login
    ):
        alice_auth = login(_ALICE_EMAIL, _ALICE_PASSWORD)
        payload = _completed_payload(
            client, alice_auth, setup["project_a"], setup["ref_id"]
        )
        del payload["pointers"][0]["entity_id"]

        self._bad(client, alice_auth, payload)

    def test_a_relation_without_a_predicate_is_rejected(
        self, setup, client, login
    ):
        alice_auth = login(_ALICE_EMAIL, _ALICE_PASSWORD)
        payload = _completed_payload(
            client, alice_auth, setup["project_a"], setup["ref_id"]
        )
        payload["relations"] = [{"subject": _SUBJECT, "object": _OBJECT}]

        self._bad(client, alice_auth, payload)

    def test_a_non_numeric_reference_year_is_rejected(
        self, setup, client, login
    ):
        alice_auth = login(_ALICE_EMAIL, _ALICE_PASSWORD)
        payload = _completed_payload(
            client, alice_auth, setup["project_a"], setup["ref_id"]
        )
        payload["reference"]["year"] = "last spring"

        self._bad(client, alice_auth, payload)

    def test_a_reference_missing_a_required_field_is_rejected(
        self, setup, client, login
    ):
        alice_auth = login(_ALICE_EMAIL, _ALICE_PASSWORD)
        payload = _completed_payload(
            client, alice_auth, setup["project_a"], setup["ref_id"]
        )
        del payload["reference"]["title"]

        self._bad(client, alice_auth, payload)

    def test_a_user_without_an_email_is_rejected(self, setup, client, login):
        """The handler discards the client's user, but it still has a shape."""
        alice_auth = login(_ALICE_EMAIL, _ALICE_PASSWORD)
        payload = _completed_payload(
            client, alice_auth, setup["project_a"], setup["ref_id"]
        )
        payload["user"] = {}

        self._bad(client, alice_auth, payload)

    def test_a_corrupt_pointer_never_reaches_the_database(
        self, setup, client, login
    ):
        """A refused save leaves no trace of the offending pointer."""
        alice_auth = login(_ALICE_EMAIL, _ALICE_PASSWORD)
        payload = _completed_payload(
            client, alice_auth, setup["project_a"], setup["ref_id"]
        )
        payload["pointers"][0]["offset"] = "halfway"

        self._bad(client, alice_auth, payload)

        r = client.get(
            f"/reference/?ref_identifier={_PMID}"
            f"&project_id={setup['project_a']}",
            headers=alice_auth,
        )
        assert r.status_code == 200, r.text
        assert r.json()["pointers"] == []


class TestSaveRoundTrip:
    def test_the_reference_response_posts_back_unchanged(
        self, setup, client, login
    ):
        """The frontend saves what ``/reference/`` gave it, verbatim.

        Including ``reference.reference_id`` and ``last_updated``, which the
        read model always fills in and the write model has to tolerate.
        """
        alice_auth = login(_ALICE_EMAIL, _ALICE_PASSWORD)
        payload = _completed_payload(
            client, alice_auth, setup["project_a"], setup["ref_id"]
        )
        payload["relations"] = [
            {"predicate": "produces", "subject": _SUBJECT, "object": _OBJECT}
        ]
        assert (
            client.post("/save/", json=payload, headers=alice_auth).status_code
            == 200
        )

        r = client.get(
            f"/reference/?ref_identifier={_PMID}"
            f"&project_id={setup['project_a']}",
            headers=alice_auth,
        )
        assert r.status_code == 200, r.text
        fetched = r.json()
        assert fetched["reference"]["reference_id"] == setup["ref_id"]
        assert len(fetched["pointers"]) == 2
        assert fetched["relations"][0]["relation_id"] is not None
        assert fetched["last_updated"] is not None

        r = client.post("/save/", json=fetched, headers=alice_auth)
        assert r.status_code == 200, r.text
