"""Audit logs and action discovery."""


def test_audit_logs_filters(hub, api):
    result = api.get_audit_logs(
        account="acme",
        action="repo.create",
        name="acme/app",
        actor="tester",
        from_date="2026-06-01T00:00:00Z",
        to_date="2026-06-10T00:00:00Z",
        page=1,
        page_size=50,
    )
    assert result["data"]["logs"][0]["action"] == "repo.create"
    params = dict(hub.requests[-1].url.params)
    assert params == {
        "action": "repo.create",
        "name": "acme/app",
        "actor": "tester",
        "from": "2026-06-01T00:00:00Z",
        "to": "2026-06-10T00:00:00Z",
        "page": "1",
        "page_size": "50",
    }


def test_audit_log_actions(hub, api):
    result = api.get_audit_log_actions(account="acme")
    assert "repo" in result["data"]["actions"]
    assert hub.requests[-1].url.path == "/v2/auditlogs/acme/actions"
