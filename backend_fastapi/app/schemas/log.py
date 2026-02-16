from pydantic import BaseModel, ConfigDict
from datetime import datetime
from typing import Optional

class LogBase(BaseModel):
    timestamp: datetime
    src_ip: Optional[str] = None
    dst_ip: Optional[str] = None
    src_port: Optional[int] = None
    dst_port: Optional[int] = None
    protocol: Optional[str] = None
    action: Optional[str] = None
    reason: Optional[str] = None
    flags: Optional[str] = None
    firewall_id: Optional[str] = None
    session_id: Optional[str] = None
    rule_id: Optional[str] = None
    bytes_count: Optional[int] = None

class LogCreate(LogBase):
    pass

class LogUpdate(LogBase):
    pass

class Log(LogBase):
    id: int
    log_type: Optional[str] = None
    severity: Optional[str] = None
    attack_type: Optional[str] = None
    bug_type: Optional[str] = None
    
    model_config = ConfigDict(from_attributes=True)
