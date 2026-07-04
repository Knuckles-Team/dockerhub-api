"""Docker Hub authentication endpoints.

CONCEPT:DH-OS.identity.jwt-auth-lifecycle-endpoint — JWT auth lifecycle (endpoint wrappers).
"""

import warnings
from typing import Any

from dockerhub_api.api.api_client_base import DockerHubApiBase
from dockerhub_api.dockerhub_input_models import (
    AuthTokenModel,
    LoginModel,
    TwoFactorLoginModel,
)
from dockerhub_api.dockerhub_response_models import (
    JwtToken,
    LoginResult,
    validate_lenient,
)


class DockerHubApiAuth(DockerHubApiBase):
    """``/v2/auth/token``, ``/v2/users/login``, ``/v2/users/2fa-login``."""

    def create_auth_token(self, identifier: str, secret: str) -> dict[str, Any]:
        """Mint a short-lived JWT bearer from an identifier + secret.

        The secret may be an account password, a personal access token
        (``dckr_pat_*``), or an organization access token.
        """
        model = AuthTokenModel(identifier=identifier, secret=secret)
        envelope = self._request("POST", "/v2/auth/token", json=model.payload)
        envelope["data"] = validate_lenient(JwtToken, envelope["data"])
        return envelope

    def login(self, username: str, password: str) -> dict[str, Any]:
        """Authenticate via the legacy login endpoint.

        .. deprecated:: 0.1.0
            ``POST /v2/users/login`` is deprecated by Docker Hub — prefer
            :meth:`create_auth_token` (``POST /v2/auth/token``). Kept for
            parity with the published API surface and for the 2FA flow.
        """
        warnings.warn(
            "POST /v2/users/login is deprecated by Docker Hub; "
            "use create_auth_token (POST /v2/auth/token) instead.",
            DeprecationWarning,
            stacklevel=2,
        )
        model = LoginModel(username=username, password=password)
        envelope = self._request(
            "POST", "/v2/users/login", json=model.payload, raise_for_status=False
        )
        # A 401 carrying a login_2fa_token is the expected second-factor
        # challenge, not an error.
        data = envelope["data"]
        if envelope["status_code"] >= 400 and not (
            isinstance(data, dict) and data.get("login_2fa_token")
        ):
            self._raise_for_status_envelope(envelope)
        envelope["data"] = validate_lenient(LoginResult, data)
        return envelope

    def two_factor_login(self, login_2fa_token: str, code: str) -> dict[str, Any]:
        """Complete a 2FA login with the TOTP code (``POST /v2/users/2fa-login``)."""
        model = TwoFactorLoginModel(login_2fa_token=login_2fa_token, code=code)
        envelope = self._request("POST", "/v2/users/2fa-login", json=model.payload)
        envelope["data"] = validate_lenient(LoginResult, envelope["data"])
        return envelope

    def _raise_for_status_envelope(self, envelope: dict[str, Any]) -> None:
        from agent_utilities.core.exceptions import ApiError, AuthError

        status_code = envelope["status_code"]
        detail = ""
        if isinstance(envelope["data"], dict):
            detail = str(envelope["data"].get("detail") or "")
        if status_code in (401, 403):
            raise AuthError(f"Login failed (HTTP {status_code}): {detail}")
        raise ApiError(f"Login failed (HTTP {status_code}): {detail}")
