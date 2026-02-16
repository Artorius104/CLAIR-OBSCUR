from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, extract
from app.core.database import get_db
from app.models.log import FirewallLog, FirewallStatsHourly

router = APIRouter()


@router.get("/overview")
def get_overview(db: Session = Depends(get_db)):
    total = db.query(FirewallLog).count()

    total_blocked = (
        db.query(FirewallLog)
        .filter(FirewallLog.action.in_(["DENY", "DROP", "REJECT"]))
        .count()
    )
    total_allowed = (
        db.query(FirewallLog)
        .filter(FirewallLog.action.in_(["ALLOW", "ACCEPT"]))
        .count()
    )

    severity_high = db.query(FirewallLog).filter(FirewallLog.severity == "High").count()
    severity_medium = db.query(FirewallLog).filter(FirewallLog.severity == "Medium").count()
    severity_low = db.query(FirewallLog).filter(FirewallLog.severity == "Low").count()

    unique_src = db.query(func.count(func.distinct(FirewallLog.src_ip))).scalar() or 0
    unique_dst = db.query(func.count(func.distinct(FirewallLog.dst_ip))).scalar() or 0

    return {
        "total_logs": total,
        "total_blocked": total_blocked,
        "total_allowed": total_allowed,
        "severity_high": severity_high,
        "severity_medium": severity_medium,
        "severity_low": severity_low,
        "unique_src_ips": unique_src,
        "unique_dst_ips": unique_dst,
    }


@router.get("/timeline")
def get_timeline(db: Session = Depends(get_db)):
    """Hourly event counts from the stats table, falling back to raw logs."""
    # Try aggregated stats first
    stats = (
        db.query(
            FirewallStatsHourly.hour_timestamp,
            func.sum(FirewallStatsHourly.total_events).label("total"),
        )
        .group_by(FirewallStatsHourly.hour_timestamp)
        .order_by(FirewallStatsHourly.hour_timestamp)
        .limit(168)  # last 7 days max
        .all()
    )

    if stats:
        return [
            {"hour": str(s.hour_timestamp), "total": s.total}
            for s in stats
        ]

    # Fallback: raw logs grouped by hour
    rows = (
        db.query(
            func.date_trunc("hour", FirewallLog.timestamp).label("hour"),
            func.count().label("total"),
        )
        .group_by("hour")
        .order_by("hour")
        .limit(168)
        .all()
    )
    return [{"hour": str(r.hour), "total": r.total} for r in rows]


@router.get("/actions")
def get_action_breakdown(db: Session = Depends(get_db)):
    rows = (
        db.query(FirewallLog.action, func.count().label("count"))
        .group_by(FirewallLog.action)
        .order_by(desc("count"))
        .all()
    )
    return [{"action": r.action or "UNKNOWN", "count": r.count} for r in rows]


@router.get("/protocols")
def get_protocol_breakdown(db: Session = Depends(get_db)):
    rows = (
        db.query(FirewallLog.protocol, func.count().label("count"))
        .group_by(FirewallLog.protocol)
        .order_by(desc("count"))
        .all()
    )
    return [{"protocol": r.protocol or "UNKNOWN", "count": r.count} for r in rows]


@router.get("/severity")
def get_severity_breakdown(db: Session = Depends(get_db)):
    rows = (
        db.query(FirewallLog.severity, func.count().label("count"))
        .group_by(FirewallLog.severity)
        .order_by(desc("count"))
        .all()
    )
    return [{"severity": r.severity or "UNKNOWN", "count": r.count} for r in rows]
