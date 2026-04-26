from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from fastapi import Depends, Header, HTTPException, status

from shared.schemas import Role


@dataclass
class RequestContext:
    user: str
    role: Role
    request_id: str


def get_request_context(
    x_user: str | None = Header(default=None, alias="X-User"),
    x_role: str | None = Header(default=None, alias="X-Role"),
    x_request_id: str | None = Header(default=None, alias="X-Request-Id"),
) -> RequestContext:
    role_value = x_role or Role.viewer.value
    try:
        role = Role(role_value)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported role '{role_value}'. Allowed: viewer, operator, admin.",
        ) from exc

    return RequestContext(
        user=x_user or "anonymous",
        role=role,
        request_id=x_request_id or "no-request-id",
    )


def require_roles(*allowed: Role) -> Callable[[RequestContext], RequestContext]:
    def checker(ctx: RequestContext = Depends(get_request_context)) -> RequestContext:
        if ctx.role not in allowed:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You do not have permission to perform this action.",
            )
        return ctx

    return checker

