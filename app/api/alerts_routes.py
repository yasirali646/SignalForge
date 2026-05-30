from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import AlertLog, AlertRule, Competitor, Event
from app.services.alerts import evaluate_alerts_for_event, seed_default_alert_rules

router = APIRouter(prefix="/alerts", tags=["alerts"])


class AlertRuleIn(BaseModel):
    name: str = Field(..., min_length=1, max_length=128)
    enabled: bool = True
    event_types: str = ""
    min_severity: str = Field(default="medium", pattern="^(low|medium|high)$")
    competitor_id: int | None = None
    webhook_url: str | None = None


class AlertRuleOut(BaseModel):
    id: int
    name: str
    enabled: bool
    event_types: str
    min_severity: str
    competitor_id: int | None
    webhook_url: str | None

    model_config = {"from_attributes": True}


class AlertLogOut(BaseModel):
    id: int
    rule_id: int
    event_id: int
    message: str
    delivered: bool
    created_at: str
    event_title: str | None = None
    competitor_name: str | None = None


@router.get("/rules", response_model=list[AlertRuleOut])
def list_rules(db: Session = Depends(get_db)):
    return db.scalars(select(AlertRule).order_by(AlertRule.id)).all()


@router.post("/rules", response_model=AlertRuleOut, status_code=201)
def create_rule(body: AlertRuleIn, db: Session = Depends(get_db)):
    if body.competitor_id and not db.get(Competitor, body.competitor_id):
        raise HTTPException(404, detail="Competitor not found")
    row = AlertRule(**body.model_dump())
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


@router.patch("/rules/{rule_id}", response_model=AlertRuleOut)
def update_rule(rule_id: int, body: AlertRuleIn, db: Session = Depends(get_db)):
    row = db.get(AlertRule, rule_id)
    if not row:
        raise HTTPException(404, detail="Rule not found")
    for k, v in body.model_dump().items():
        setattr(row, k, v)
    db.commit()
    db.refresh(row)
    return row


@router.delete("/rules/{rule_id}", status_code=204)
def delete_rule(rule_id: int, db: Session = Depends(get_db)):
    row = db.get(AlertRule, rule_id)
    if not row:
        raise HTTPException(404, detail="Rule not found")
    db.delete(row)
    db.commit()


@router.get("/logs", response_model=list[AlertLogOut])
def list_alert_logs(limit: int = 30, db: Session = Depends(get_db)):
    logs = db.scalars(
        select(AlertLog).order_by(AlertLog.created_at.desc()).limit(limit)
    ).all()
    out = []
    for log in logs:
        event = db.get(Event, log.event_id)
        comp_name = None
        event_title = None
        if event:
            event_title = event.title
            comp = db.get(Competitor, event.competitor_id)
            comp_name = comp.name if comp else None
        out.append(
            AlertLogOut(
                id=log.id,
                rule_id=log.rule_id,
                event_id=log.event_id,
                message=log.message,
                delivered=log.delivered,
                created_at=log.created_at.isoformat(),
                event_title=event_title,
                competitor_name=comp_name,
            )
        )
    return out


@router.post("/evaluate/{event_id}")
def reevaluate_event(event_id: int, db: Session = Depends(get_db)):
    event = db.get(Event, event_id)
    if not event:
        raise HTTPException(404, detail="Event not found")
    logs = evaluate_alerts_for_event(db, event)
    return {"triggered": len(logs)}


@router.post("/seed")
def seed_rules(db: Session = Depends(get_db)):
    seed_default_alert_rules(db)
    return {"ok": True}
