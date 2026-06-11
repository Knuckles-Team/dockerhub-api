"""Audit log endpoints (``/v2/auditlogs``).

CONCEPT:HUB-1.0 — core wrapper.
"""

from typing import Any

from dockerhub_api.api.api_client_base import DockerHubApiBase
from dockerhub_api.dockerhub_input_models import AuditLogModel
from dockerhub_api.dockerhub_response_models import (
    AuditLogActions,
    AuditLogPage,
    validate_lenient,
)


class DockerHubApiAuditLogs(DockerHubApiBase):
    """Read access to an account's audit trail."""

    def get_audit_logs(
        self,
        account: str,
        action: str | None = None,
        name: str | None = None,
        actor: str | None = None,
        from_date: str | None = None,
        to_date: str | None = None,
        page: int | None = None,
        page_size: int | None = None,
    ) -> dict[str, Any]:
        """List audit-log events for a namespace.

        Filters: ``action``, ``name`` (object), ``actor`` (username), and a
        ``from_date``/``to_date`` RFC 3339 window (sent as ``from``/``to``).
        """
        model = AuditLogModel(
            account=account,
            action=action,
            name=name,
            actor=actor,
            from_date=from_date,
            to_date=to_date,
            page=page,
            page_size=page_size,
        )
        envelope = self._request(
            "GET", f"/v2/auditlogs/{model.account}", params=model.api_parameters
        )
        envelope["data"] = validate_lenient(AuditLogPage, envelope["data"])
        return envelope

    def get_audit_log_actions(self, account: str) -> dict[str, Any]:
        """List the audit-log action names available for a namespace."""
        envelope = self._request("GET", f"/v2/auditlogs/{account}/actions")
        envelope["data"] = validate_lenient(AuditLogActions, envelope["data"])
        return envelope
