from uuid import UUID

from d3textdb.schema import UserAuth

from ahbackend.api.api import can_access_project, can_curate_project
from ahbackend.utils import cse_citation

_DUMMY_UUID = UUID("00000000-0000-0000-0000-000000000000")


def make_user_auth(
    *, is_super_user: bool = False, can_manage: bool = False
) -> UserAuth:
    return UserAuth(
        user_id=_DUMMY_UUID,
        hashed_password="",
        is_super_user=is_super_user,
        can_manage=can_manage,
    )


class TestCanAccessProject:
    def test_returns_true_when_user_has_a_project_role(self):
        assert can_access_project(None, ["annotator"])

    def test_returns_true_when_user_has_can_manage_and_no_roles(self):
        assert can_access_project(make_user_auth(can_manage=True), [])

    def test_returns_true_when_super_user_has_no_roles(self):
        assert can_access_project(make_user_auth(is_super_user=True), [])

    def test_returns_false_when_no_roles_and_plain_user(self):
        assert not can_access_project(make_user_auth(), [])

    def test_returns_false_when_user_auth_is_none_and_no_roles(self):
        assert not can_access_project(None, [])


class TestCanCurateProject:
    def test_returns_true_when_user_has_curator_role(self):
        assert can_curate_project(None, ["curator"])

    def test_returns_true_when_user_has_manager_role(self):
        assert can_curate_project(None, ["manager"])

    def test_returns_false_when_user_has_annotator_role_only(self):
        assert not can_curate_project(make_user_auth(), ["annotator"])

    def test_returns_false_when_user_auth_is_none_and_no_roles(self):
        assert not can_curate_project(None, [])


class TestCseCitation:
    def test_single_author(self):
        assert cse_citation("Smith, J.", 2004) == "Smith 2004"

    def test_two_authors(self):
        assert (
            cse_citation("Smith, J.; Jones, A.", 2004) == "Smith & Jones 2004"
        )

    def test_three_or_more_authors(self):
        assert (
            cse_citation("Smith, J.; Jones, A.; Williams, B.", 2004)
            == "Smith et al. 2004"
        )
        assert (
            cse_citation(
                "Bhakta, S.; Besra, G.S.; Upton, A.M.; Parish, T.", 2004
            )
            == "Bhakta et al. 2004"
        )

    def test_empty_authors(self):
        assert cse_citation("", 2004) == "2004"
