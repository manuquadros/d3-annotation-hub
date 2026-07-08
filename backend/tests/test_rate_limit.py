"""slowapi rate-limiting tests for the auth endpoints (TICKET-27).

The shared ``_reset_rate_limiter`` fixture in ``conftest.py`` disables the
limiter for every other test; these tests opt back in explicitly so the
throttle can be exercised in isolation.
"""

import pytest

from ahbackend import config
from ahbackend.api.api import app

_EMAIL = "ratelimit@ratelimit-test.example"
_PASSWORD = "original-secret"


@pytest.fixture()
def enabled_limiter():
    """Turn the shared limiter on and hand back its configured login budget."""
    app.state.limiter.enabled = True
    app.state.limiter.reset()
    login_budget = int(config.LOGIN_RATE_LIMIT.split("/")[0])
    yield login_budget
    app.state.limiter.enabled = False
    app.state.limiter.reset()


def test_login_is_throttled_after_the_budget(client, enabled_limiter):
    login_budget = enabled_limiter
    # Wrong-password attempts still count against the per-IP budget — that is
    # exactly the brute-force path we want to cap.
    for _ in range(login_budget):
        r = client.post(
            "/token", data={"username": _EMAIL, "password": "wrong"}
        )
        assert r.status_code == 401, r.text

    throttled = client.post(
        "/token", data={"username": _EMAIL, "password": "wrong"}
    )
    assert throttled.status_code == 429


def test_successful_logins_within_the_budget_are_not_throttled(
    client, make_user, enabled_limiter
):
    login_budget = enabled_limiter
    make_user(_EMAIL, _PASSWORD)  # one login already spent by the factory
    for _ in range(login_budget - 1):
        r = client.post(
            "/token", data={"username": _EMAIL, "password": _PASSWORD}
        )
        assert r.status_code == 200, r.text
