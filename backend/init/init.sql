-- ============================================
-- Tables pour les logs firewall
-- ============================================

-- Table principale des logs firewall
-- Colonnes nullables pour gérer les données incomplètes
DROP TABLE IF EXISTS firewall_logs CASCADE;
CREATE TABLE firewall_logs (
    id                  SERIAL PRIMARY KEY,
    timestamp           TIMESTAMP,
    firewall_id         VARCHAR(50),
    src_ip              VARCHAR(45),
    dst_ip              VARCHAR(45),
    src_port            INTEGER,
    dst_port            INTEGER,
    protocol            VARCHAR(20),
    action              VARCHAR(20),
    bytes               INTEGER,
    duration_ms         INTEGER,
    rule_id             VARCHAR(50),
    session_id          VARCHAR(100),
    user_name           VARCHAR(255),
    reason              VARCHAR(255),
    status              VARCHAR(50),
    flags               VARCHAR(50),
    bug_type            VARCHAR(100),
    log_category        VARCHAR(50),
    severity            VARCHAR(20),
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Index pour améliorer les performances
CREATE INDEX idx_firewall_logs_timestamp ON firewall_logs(timestamp);
CREATE INDEX idx_firewall_logs_firewall_id ON firewall_logs(firewall_id);
CREATE INDEX idx_firewall_logs_action ON firewall_logs(action);
CREATE INDEX idx_firewall_logs_protocol ON firewall_logs(protocol);
CREATE INDEX idx_firewall_logs_src_ip ON firewall_logs(src_ip);
CREATE INDEX idx_firewall_logs_dst_ip ON firewall_logs(dst_ip);
CREATE INDEX idx_firewall_logs_severity ON firewall_logs(severity);
CREATE INDEX idx_firewall_logs_log_category ON firewall_logs(log_category);

-- Table des statistiques agrégées par heure
DROP TABLE IF EXISTS firewall_stats_hourly CASCADE;
CREATE TABLE firewall_stats_hourly (
    id                  SERIAL PRIMARY KEY,
    hour_timestamp      TIMESTAMP NOT NULL,
    firewall_id         VARCHAR(50) NOT NULL,
    protocol            VARCHAR(20) NOT NULL,
    action              VARCHAR(20) NOT NULL,
    total_events        INTEGER NOT NULL,
    total_bytes         BIGINT NOT NULL,
    avg_duration_ms     DOUBLE PRECISION,
    unique_src_ips      INTEGER,
    unique_dst_ips      INTEGER,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(hour_timestamp, firewall_id, protocol, action)
);

CREATE INDEX idx_stats_hourly_timestamp ON firewall_stats_hourly(hour_timestamp);
CREATE INDEX idx_stats_hourly_firewall_id ON firewall_stats_hourly(firewall_id);

-- Table des top ports utilisés
DROP TABLE IF EXISTS firewall_top_ports CASCADE;
CREATE TABLE firewall_top_ports (
    id                  SERIAL PRIMARY KEY,
    port                INTEGER NOT NULL,
    port_type           VARCHAR(20) NOT NULL, -- 'source' ou 'destination'
    protocol            VARCHAR(20) NOT NULL,
    total_connections   INTEGER NOT NULL,
    last_seen           TIMESTAMP NOT NULL,
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(port, port_type, protocol)
);

CREATE INDEX idx_top_ports_port ON firewall_top_ports(port);
CREATE INDEX idx_top_ports_protocol ON firewall_top_ports(protocol);

-- Table des IPs suspectes (trop de connexions bloquées)
DROP TABLE IF EXISTS firewall_suspicious_ips CASCADE;
CREATE TABLE firewall_suspicious_ips (
    id                  SERIAL PRIMARY KEY,
    ip_address          VARCHAR(45) NOT NULL,
    ip_type             VARCHAR(20) NOT NULL, -- 'source' ou 'destination'
    blocked_count       INTEGER NOT NULL,
    last_blocked        TIMESTAMP NOT NULL,
    risk_level          VARCHAR(20), -- 'LOW', 'MEDIUM', 'HIGH', 'CRITICAL'
    created_at          TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(ip_address, ip_type)
);

CREATE INDEX idx_suspicious_ips_address ON firewall_suspicious_ips(ip_address);
CREATE INDEX idx_suspicious_ips_risk ON firewall_suspicious_ips(risk_level);

-- Les vues ont été remplacées par des requêtes directes dans l'application
-- pour éviter les problèmes quand la table est vide au démarrage
