from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any
from app.core.database import get_db
from app.models.log import FirewallLog
from app.schemas.log import Log, LogCreate
from app.services.analyzer import LogAnalyzer
from sqlalchemy import func

router = APIRouter()

@router.post("/", response_model=Log)
def create_log(log: LogCreate, db: Session = Depends(get_db)):
    # 1. Analyze the log
    analyzed_data = LogAnalyzer.analyze(log)
    
    # 2. Create DB Object
    db_log = FirewallLog(**analyzed_data)
    
    # 3. Save to DB
    db.add(db_log)
    db.commit()
    db.refresh(db_log)
    
    return db_log

@router.get("/", response_model=List[Log])
def read_logs(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    logs = db.query(FirewallLog).order_by(FirewallLog.timestamp.desc()).offset(skip).limit(limit).all()
    return logs

@router.get("/stats")
def read_stats(db: Session = Depends(get_db)):
    total_logs = db.query(FirewallLog).count()
    total_attacks = db.query(FirewallLog).filter(FirewallLog.log_type == "Attack").count()
    total_bugs = db.query(FirewallLog).filter(FirewallLog.log_type == "Bug").count()
    
    # Severity counts
    critical = db.query(FirewallLog).filter(FirewallLog.severity == "High").count()
    medium = db.query(FirewallLog).filter(FirewallLog.severity == "Medium").count()
    low = db.query(FirewallLog).filter(FirewallLog.severity == "Low").count()
    
    # Recent attacks
    recent_attacks = db.query(FirewallLog)\
        .filter(FirewallLog.log_type == "Attack")\
        .order_by(FirewallLog.timestamp.desc())\
        .limit(5)\
        .all()
        
    return {
        "total_logs": total_logs,
        "total_attacks": total_attacks,
        "total_bugs": total_bugs,
        "severity": {
            "critical": critical,
            "medium": medium,
            "low": low
        },
        "recent_attacks": recent_attacks
    }
