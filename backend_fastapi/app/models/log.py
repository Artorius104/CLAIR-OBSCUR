from sqlalchemy import Column, Integer, String, DateTime, Float
from app.core.database import Base
from datetime import datetime

class FirewallLog(Base):
    __tablename__ = "firewall_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True, default=datetime.utcnow)
    
    # Original Fields
    src_ip = Column(String, index=True, nullable=True)
    dst_ip = Column(String, index=True, nullable=True)
    src_port = Column(Integer, nullable=True)
    dst_port = Column(Integer, nullable=True)
    protocol = Column(String, nullable=True)
    action = Column(String, nullable=True)
    reason = Column(String, nullable=True)
    flags = Column(String, nullable=True)
    firewall_id = Column(String, nullable=True)
    session_id = Column(String, nullable=True)
    rule_id = Column(String, nullable=True)
    bytes_count = Column(Integer, nullable=True) # Renamed from bytes to avoid keyword conflict
    
    # Analyzed Fields
    log_type = Column(String, index=True, nullable=True) # Attack, Bug, Normal
    severity = Column(String, index=True, nullable=True) # High, Medium, Low
    attack_type = Column(String, index=True, nullable=True)
    bug_type = Column(String, nullable=True)
