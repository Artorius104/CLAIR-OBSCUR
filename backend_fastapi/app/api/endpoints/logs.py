from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, desc
from typing import List, Optional
from app.core.database import get_db
from app.models.log import FirewallLog, FirewallSuspiciousIP, FirewallTopPort
from app.schemas.log import Log, SuspiciousIPOut, TopPortOut

router = APIRouter()


@router.get("/", response_model=List[Log])
def read_logs(
    skip: int = 0,
    limit: int = 100,
    severity: Optional[str] = Query(None),
    action: Optional[str] = Query(None),
    protocol: Optional[str] = Query(None),
    search: Optional[str] = Query(None),
    db: Session = Depends(get_db),
):
    q = db.query(FirewallLog)

    if severity:
        q = q.filter(FirewallLog.severity == severity)
    if action:
        q = q.filter(FirewallLog.action == action)
    if protocol:
        q = q.filter(FirewallLog.protocol == protocol)
    if search:
        pattern = f"%{search}%"
        q = q.filter(
            FirewallLog.src_ip.ilike(pattern)
            | FirewallLog.dst_ip.ilike(pattern)
            | FirewallLog.reason.ilike(pattern)
            | FirewallLog.firewall_id.ilike(pattern)
        )

    logs = q.order_by(desc(FirewallLog.timestamp)).offset(skip).limit(limit).all()
    return logs


@router.get("/count")
def count_logs(db: Session = Depends(get_db)):
    return {"count": db.query(FirewallLog).count()}


@router.get("/suspicious-ips", response_model=List[SuspiciousIPOut])
def get_suspicious_ips(limit: int = 50, db: Session = Depends(get_db)):
    return (
        db.query(FirewallSuspiciousIP)
        .order_by(desc(FirewallSuspiciousIP.blocked_count))
        .limit(limit)
        .all()
    )


@router.get("/top-ports", response_model=List[TopPortOut])
def get_top_ports(limit: int = 50, db: Session = Depends(get_db)):
    return (
        db.query(FirewallTopPort)
        .order_by(desc(FirewallTopPort.total_connections))
        .limit(limit)
        .all()
    )
