"""
Saved Scripts routes.

GET  /scripts        — list all saved scripts (admin)
POST /scripts        — save a generated script (admin)
DELETE /scripts/{id} — delete a saved script (admin)
"""

from datetime import timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.db import get_db
from app.dependencies.auth import verify_admin
from app.models.db_models import Script

router = APIRouter()


class ScriptIn(BaseModel):
    topic: str
    title: str
    hook: str
    script: str


@router.get("/scripts", tags=["Scripts"])
async def list_scripts(
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    rows = db.query(Script).order_by(Script.created_at.desc()).all()
    return {
        "scripts": [
            {
                "id": s.id,
                "topic": s.topic,
                "title": s.title,
                "hook": s.hook,
                "script": s.script,
                "created_at": s.created_at.replace(tzinfo=timezone.utc).isoformat()
                if s.created_at else None,
            }
            for s in rows
        ],
        "count": len(rows),
    }


@router.post("/scripts", tags=["Scripts"], status_code=201)
async def save_script(
    body: ScriptIn,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    row = Script(
        topic=body.topic.strip(),
        title=body.title.strip(),
        hook=body.hook.strip(),
        script=body.script.strip(),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return {"id": row.id, "message": "Script saved."}


@router.delete("/scripts/{script_id}", tags=["Scripts"])
async def delete_script(
    script_id: int,
    db: Session = Depends(get_db),
    _: None = Depends(verify_admin),
) -> dict:
    row = db.query(Script).filter(Script.id == script_id).first()
    if not row:
        raise HTTPException(status_code=404, detail="Script not found.")
    db.delete(row)
    db.commit()
    return {"message": "Script deleted."}
