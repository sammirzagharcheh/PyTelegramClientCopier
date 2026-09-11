"""FastAPI dependencies that gate API-key scopes by HTTP method / path."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status

from app.auth.scopes import ensure_api_key_scopes
from app.web.deps import CurrentUser


def _forbid_missing_scope(user: dict, needed: tuple[str, ...]) -> None:
    try:
        ensure_api_key_scopes(user, needed)
    except PermissionError as e:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail=str(e)) from e


def resource_scope_dependency(
    read_scope: str,
    write_scope: str,
    *,
    read_path_suffixes: tuple[str, ...] = (),
):
    """Router dependency: GET/HEAD → read_scope; otherwise write_scope.

    Paths ending with any ``read_path_suffixes`` (e.g. ``/preview``) use read
    even on POST.
    """

    async def _gate(request: Request, user: CurrentUser) -> None:
        if user.get("auth_via") != "api_key":
            return
        path = request.url.path.rstrip("/")
        if request.method in ("GET", "HEAD", "OPTIONS") or any(
            path.endswith(suf.rstrip("/")) for suf in read_path_suffixes
        ):
            _forbid_missing_scope(user, (read_scope,))
        else:
            _forbid_missing_scope(user, (write_scope,))

    return Depends(_gate)


def read_only_scope_dependency(scope: str):
    """Router dependency requiring a single read scope for all methods."""

    async def _gate(user: CurrentUser) -> None:
        if user.get("auth_via") != "api_key":
            return
        _forbid_missing_scope(user, (scope,))

    return Depends(_gate)


def reject_api_key_dependency():
    """Block X-Api-Key on routes that must use JWT (admin / session profile)."""

    async def _gate(user: CurrentUser) -> None:
        if user.get("auth_via") == "api_key":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="This endpoint requires JWT authentication; API keys are not allowed",
            )

    return Depends(_gate)
