"""Request identity and permission checks."""
from typing import Optional

from fastapi import Depends, Header, HTTPException

from app.services import access_service


def current(x_aava_user: Optional[str] = Header(None)):
    return access_service.user(x_aava_user)


def need(perm: str):
    def dep(u=Depends(current)):
        try:
            access_service.require(u, perm)
        except PermissionError as e:
            raise HTTPException(403, str(e))
        return u
    return dep
