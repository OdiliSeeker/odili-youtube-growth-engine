"""Tests for the network-failure incident tracker in lead_discovery_service.

Locks in the state-machine semantics of ``_record_network_failures``:
  * a fully-failed scan (api_failures > 0, api_successes == 0) increments the streak;
  * a neutral scan (no API calls at all) leaves the streak unchanged;
  * any successful API call resets the streak and re-arms the alert;
  * one admin notice fires at NETWORK_FAILURE_THRESHOLD and is not repeated;
  * a failed notice send retries on the next failing scan;
  * the streak is exposed as ``network_failure`` in status().
"""

import pytest

from app.services import lead_discovery_service as lds


FAIL = {"api_failures": 2, "api_successes": 0, "last_api_error": "Network error calling YouTube API: timeout"}
OK = {"api_failures": 0, "api_successes": 3}
MIXED = {"api_failures": 1, "api_successes": 1}
NEUTRAL = {"api_failures": 0, "api_successes": 0}


@pytest.fixture()
def notices(monkeypatch):
    """Capture admin notices instead of sending real email."""
    sent = []

    class _Result:
        success = True
        error = None

    import app.services.email_sender_service as ess

    monkeypatch.setattr(ess, "send_admin_notice", lambda subject, body: (sent.append(subject), _Result())[1])
    return sent


def test_failed_scans_increment_streak(db, notices):
    lds._record_network_failures(db, FAIL)
    lds._record_network_failures(db, FAIL)
    state = lds._get_network_failure(db)
    assert state is not None
    assert state["count"] == 2
    assert state["notified"] is False
    assert state["since"]
    assert "timeout" in state["last_error"]
    assert state["threshold"] == lds.NETWORK_FAILURE_THRESHOLD
    assert notices == []


def test_neutral_scan_leaves_streak_unchanged(db, notices):
    lds._record_network_failures(db, FAIL)
    lds._record_network_failures(db, NEUTRAL)
    state = lds._get_network_failure(db)
    assert state is not None and state["count"] == 1


def test_notice_fires_once_at_threshold(db, notices):
    for _ in range(lds.NETWORK_FAILURE_THRESHOLD):
        lds._record_network_failures(db, FAIL)
    assert len(notices) == 1
    state = lds._get_network_failure(db)
    assert state["count"] == lds.NETWORK_FAILURE_THRESHOLD
    assert state["notified"] is True

    # Further failing scans do NOT re-notify within the same incident.
    lds._record_network_failures(db, FAIL)
    assert len(notices) == 1


def test_success_resets_and_rearms(db, notices):
    for _ in range(lds.NETWORK_FAILURE_THRESHOLD):
        lds._record_network_failures(db, FAIL)
    assert len(notices) == 1

    lds._record_network_failures(db, OK)
    assert lds._get_network_failure(db) is None, "recovery must clear the streak"

    # A new incident notifies again once the threshold is reached.
    for _ in range(lds.NETWORK_FAILURE_THRESHOLD):
        lds._record_network_failures(db, FAIL)
    assert len(notices) == 2


def test_mixed_scan_counts_as_success(db, notices):
    lds._record_network_failures(db, FAIL)
    lds._record_network_failures(db, MIXED)
    assert lds._get_network_failure(db) is None, "any successful API call means YouTube is reachable"


def test_failed_notice_send_retries_next_failing_scan(db, monkeypatch):
    sent = []

    class _Fail:
        success = False
        error = "sendgrid down"

    class _Ok:
        success = True
        error = None

    import app.services.email_sender_service as ess

    results = [_Fail(), _Ok()]
    monkeypatch.setattr(ess, "send_admin_notice", lambda s, b: (sent.append(s), results.pop(0))[1])

    for _ in range(lds.NETWORK_FAILURE_THRESHOLD):
        lds._record_network_failures(db, FAIL)
    state = lds._get_network_failure(db)
    assert state["notified"] is False, "failed send must leave the flag unset for retry"

    lds._record_network_failures(db, FAIL)
    state = lds._get_network_failure(db)
    assert state["notified"] is True
    assert len(sent) == 2


def test_status_exposes_network_failure(db, notices):
    assert lds.status(db)["network_failure"] is None
    lds._record_network_failures(db, FAIL)
    state = lds.status(db)["network_failure"]
    assert state is not None and state["count"] == 1
