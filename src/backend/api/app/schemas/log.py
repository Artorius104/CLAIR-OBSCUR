from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional


class LogBase(BaseModel):
    timestamp: Optional[datetime] = None
    firewall_id: Optional[str] = None
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    protocol: Optional[str] = None
    action: Optional[str] = None
    bytes: Optional[int] = None
    duration_ms: Optional[int] = None
    rule_id: Optional[str] = None
    session_id: Optional[str] = None
    user_name: Optional[str] = None
    reason: Optional[str] = None
    status: Optional[str] = None
    flags: Optional[str] = None
    bug_type: Optional[str] = None
    log_category: Optional[str] = None
    severity: Optional[str] = None


class LogCreate(LogBase):
    pass


class Log(LogBase):
    id: int
    created_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


# --- Analytics schemas ---

class OverviewStats(BaseModel):
    total_logs: int
    total_blocked: int
    total_allowed: int
    severity_high: int
    severity_medium: int
    severity_low: int
    unique_src_ips: int
    unique_dst_ips: int


class TimelinePoint(BaseModel):
    hour: str
    total: int
    blocked: int
    allowed: int


class ActionBreakdown(BaseModel):
    action: str
    count: int


class ProtocolBreakdown(BaseModel):
    protocol: str
    count: int


class SuspiciousIPOut(BaseModel):
    ip_address: str
    ip_type: str
    blocked_count: int
    last_blocked: Optional[datetime] = None
    risk_level: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class TopPortOut(BaseModel):
    port: int
    port_type: str
    protocol: str
    total_connections: int
    last_seen: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
