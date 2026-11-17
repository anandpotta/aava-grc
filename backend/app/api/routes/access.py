"""Roles, named approvers and who is acting."""
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.api.deps import current, need
from app.services import access_service as ac, store

router = APIRouter()


class UserIn(BaseModel):
    role: Optional[str] = None
    approves: Optional[List[str]] = None


@router.get("/access/roles")
def roles():
    return {"permissions": ac.PERMS, "roles": [{"id": k, **v, "room": bool(v.get("room"))} for k, v in ac.ROLES.items()]}


@router.get("/access/users")
def users():
    ac.user(None)
    return [ac.describe(u) for u in ac.USERS.values()]


@router.get("/access/me")
def me(u=Depends(current)):
    return ac.describe(u)


@router.put("/access/users/{uid}")
def change(uid: str, body: UserIn, admin=Depends(need("manage_roles"))):
    before = dict(ac.USERS.get(uid) or {})
    try:
        res = ac.update(uid, body.role, body.approves)
    except KeyError:
        raise HTTPException(404, "unknown user")
    except ValueError as e:
        raise HTTPException(400, str(e))
    store.audit("access.change", uid, {"role": [before.get("role"), res["role"]], "approves": [before.get("approves"), res["approves"]]})
    return res


@router.get("/story")
def story():
    """The worked leadership example: one regulatory change followed end to end."""
    return store._load("story")
