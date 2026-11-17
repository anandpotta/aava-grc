"""Regulatory change management."""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, HTTPException

from app.models.schemas import ChangeImpact, ChangeStatusUpdate, RegChange
from app.services import change_service

router = APIRouter()


@router.get("/changes", response_model=List[RegChange])
def list_changes(juris: Optional[str] = None, status: Optional[str] = None):
    return change_service.list_changes(juris, status)


@router.get("/changes/pipeline")
def pipeline():
    return change_service.pipeline()


@router.get("/changes/{change_id}", response_model=RegChange)
def get_change(change_id: str):
    items = [c for c in change_service.list_changes() if c.id == change_id]
    if not items:
        raise HTTPException(404, "change not found")
    return items[0]


@router.get("/changes/{change_id}/impact", response_model=ChangeImpact)
def impact(change_id: str):
    res = change_service.impact(change_id)
    if res is None:
        raise HTTPException(404, "change not found")
    return res


@router.post("/changes/{change_id}/status")
def set_status(change_id: str, payload: ChangeStatusUpdate):
    if change_service.get_change(change_id) is None:
        raise HTTPException(404, "change not found")
    return change_service.set_status(change_id, payload.status, payload.note)
