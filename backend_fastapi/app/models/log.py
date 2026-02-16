from sqlalchemy import Column, Integer, String, DateTime, BigInteger, Float
from app.core.database import Base
from datetime import datetime


class FirewallLog(Base):
    __tablename__ = "firewall_logs"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime, index=True)
    firewall_id = Column(String(50), index=True, nullable=True)
    src_ip = Column(String(45), index=True, nullable=True)
    dst_ip = Column(String(45), index=True, nullable=True)
    src_port = Column(Integer, nullable=True)
    dst_port = Column(Integer, nullable=True)
    protocol = Column(String(20), nullable=True)
    action = Column(String(20), nullable=True)
    bytes = Column(Integer, nullable=True)
    duration_ms = Column(Integer, nullable=True)
    rule_id = Column(String(50), nullable=True)
    session_id = Column(String(100), nullable=True)
    user_name = Column(String(255), nullable=True)
    reason = Column(String(255), nullable=True)
    status = Column(String(50), nullable=True)
    flags = Column(String(50), nullable=True)
    bug_type = Column(String(100), nullable=True)
    log_category = Column(String(50), nullable=True)
    severity = Column(String(20), index=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FirewallStatsHourly(Base):
    __tablename__ = "firewall_stats_hourly"

    id = Column(Integer, primary_key=True, index=True)
    hour_timestamp = Column(DateTime, nullable=False)
    firewall_id = Column(String(50), nullable=False)
    protocol = Column(String(20), nullable=False)
    action = Column(String(20), nullable=False)
    total_events = Column(Integer, nullable=False)
    total_bytes = Column(BigInteger, nullable=False)
    avg_duration_ms = Column(Float, nullable=True)
    unique_src_ips = Column(Integer, nullable=True)
    unique_dst_ips = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)


class FirewallTopPort(Base):
    __tablename__ = "firewall_top_ports"

    id = Column(Integer, primary_key=True, index=True)
    port = Column(Integer, nullable=False)
    port_type = Column(String(20), nullable=False)
    protocol = Column(String(20), nullable=False)
    total_connections = Column(Integer, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow)


class FirewallSuspiciousIP(Base):
    __tablename__ = "firewall_suspicious_ips"

    id = Column(Integer, primary_key=True, index=True)
    ip_address = Column(String(45), nullable=False)
    ip_type = Column(String(20), nullable=False)
    blocked_count = Column(Integer, nullable=False)
    last_blocked = Column(DateTime, nullable=False)
    risk_level = Column(String(20), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
