import pandas as pd
import psycopg2
import os
from sqlalchemy import create_engine

def get_database_connection():
    """Créer une connexion psycopg2 à la base de données PostgreSQL"""
    conn = psycopg2.connect(
        host=os.getenv("DATABASE_HOST", "localhost"),
        port=os.getenv("DATABASE_PORT", 5432),
        dbname=os.getenv("DATABASE_NAME", "spark_streaming_db"),
        user=os.getenv("DATABASE_USER", "user"),
        password=os.getenv("DATABASE_PASSWORD", "password")
    )
    return conn

def get_sqlalchemy_engine():
    """Créer un engine SQLAlchemy pour pandas"""
    connection_string = (
        f"postgresql://{os.getenv('DATABASE_USER', 'user')}:"
        f"{os.getenv('DATABASE_PASSWORD', 'password')}@"
        f"{os.getenv('DATABASE_HOST', 'localhost')}:"
        f"{os.getenv('DATABASE_PORT', 5432)}/"
        f"{os.getenv('DATABASE_NAME', 'spark_streaming_db')}"
    )
    engine = create_engine(connection_string)
    return engine

def close_database_connection(conn):
    """Fermer une connexion à la base de données"""
    conn.close()

def query_db(query):
    """Exécuter une requête SQL et retourner un DataFrame pandas"""
    try:
        engine = get_sqlalchemy_engine()
        df = pd.read_sql_query(query, engine)
        engine.dispose()
        return df
    except Exception as e:
        raise Exception(f"Erreur lors de la récupération de données: {e}")

def get_last_log_time():
    """Récupérer la date du dernier log"""
    query = "SELECT MAX(timestamp) as last_time FROM firewall_logs"
    df = query_db(query)
    if not df.empty and df.iloc[0]['last_time']:
        return pd.to_datetime(df.iloc[0]['last_time'])
    return None

# ===== Requêtes spécifiques =====

def get_global_stats(start_time=None):
    """Récupérer les statistiques globales"""
    query = """
        SELECT 
            COUNT(*) as total_logs,
            COUNT(DISTINCT firewall_id) as total_firewalls,
            COUNT(DISTINCT src_ip) as unique_src_ips,
            COUNT(DISTINCT dst_ip) as unique_dst_ips,
            SUM(CASE WHEN action = 'ALLOW' THEN 1 ELSE 0 END) as allowed_count,
            SUM(CASE WHEN action = 'DENY' THEN 1 ELSE 0 END) as denied_count,
            SUM(bytes) as total_bytes,
            AVG(duration_ms) as avg_duration_ms,
            MIN(timestamp) as first_log_time,
            MAX(timestamp) as last_log_time
        FROM firewall_logs
    """
    
    if start_time:
        query += f" WHERE timestamp >= '{start_time}'"
        
    return query_db(query)

def get_stats_by_firewall(start_time=None):
    """Récupérer les statistiques par firewall"""
    where_clause = f"WHERE timestamp >= '{start_time}'" if start_time else ""
    
    query = f"""
        SELECT 
            firewall_id,
            COUNT(*) as total_logs,
            SUM(CASE WHEN action = 'ALLOW' THEN 1 ELSE 0 END) as allowed_count,
            SUM(CASE WHEN action = 'DENY' THEN 1 ELSE 0 END) as denied_count,
            SUM(bytes) as total_bytes,
            AVG(duration_ms) as avg_duration_ms,
            COUNT(DISTINCT src_ip) as unique_src_ips,
            COUNT(DISTINCT dst_ip) as unique_dst_ips
        FROM firewall_logs
        {where_clause}
        GROUP BY firewall_id
        ORDER BY total_logs DESC;
    """
    return query_db(query)

def get_stats_by_protocol(start_time=None):
    """Récupérer les statistiques par protocole"""
    where_clause = f"WHERE timestamp >= '{start_time}'" if start_time else ""
    
    query = f"""
        SELECT 
            protocol,
            COUNT(*) as total_logs,
            SUM(CASE WHEN action = 'ALLOW' THEN 1 ELSE 0 END) as allowed_count,
            SUM(CASE WHEN action = 'DENY' THEN 1 ELSE 0 END) as denied_count,
            SUM(bytes) as total_bytes,
            AVG(duration_ms) as avg_duration_ms
        FROM firewall_logs
        {where_clause}
        GROUP BY protocol
        ORDER BY total_logs DESC;
    """
    return query_db(query)

def get_recent_logs(limit=100):
    """Récupérer les logs les plus récents"""
    query = f"""
        SELECT * FROM firewall_logs 
        ORDER BY timestamp DESC 
        LIMIT {limit};
    """
    return query_db(query)

def get_logs_by_action(action, limit=1000):
    """Récupérer les logs par action (ALLOW/DENY)"""
    query = f"""
        SELECT * FROM firewall_logs 
        WHERE action = '{action}'
        ORDER BY timestamp DESC 
        LIMIT {limit};
    """
    return query_db(query)

def get_hourly_stats(hours=None):
    """Récupérer les statistiques horaires. Si hours est None, tout récupérer."""
    if hours:
        time_condition = f"WHERE hour_timestamp >= (SELECT MAX(timestamp) FROM firewall_logs) - INTERVAL '{hours} hours'"
    else:
        time_condition = ""
        
    query = f"""
        SELECT * FROM firewall_stats_hourly
        {time_condition}
        ORDER BY hour_timestamp DESC;
    """
    return query_db(query)

def get_top_ports(port_type='destination', limit=20):
    """Récupérer les ports les plus utilisés"""
    query = f"""
        SELECT * FROM firewall_top_ports
        WHERE port_type = '{port_type}'
        ORDER BY total_connections DESC
        LIMIT {limit};
    """
    return query_db(query)

def get_suspicious_ips(risk_level=None):
    """Récupérer les IPs suspectes"""
    if risk_level:
        query = f"""
            SELECT * FROM firewall_suspicious_ips
            WHERE risk_level = '{risk_level}'
            ORDER BY blocked_count DESC;
        """
    else:
        query = """
            SELECT * FROM firewall_suspicious_ips
            ORDER BY blocked_count DESC;
        """
    return query_db(query)

def get_top_blocked_ips(limit=20):
    """Récupérer les IPs les plus bloquées"""
    query = f"""
        SELECT src_ip, COUNT(*) as block_count, 
               MAX(timestamp) as last_blocked
        FROM firewall_logs
        WHERE action = 'DENY'
        GROUP BY src_ip
        ORDER BY block_count DESC
        LIMIT {limit};
    """
    return query_db(query)

def get_top_src_ips(limit=20):
    """Récupérer les IPs sources les plus actives"""
    query = f"""
        SELECT src_ip, COUNT(*) as connection_count,
               SUM(bytes) as total_bytes,
               MAX(timestamp) as last_seen
        FROM firewall_logs
        GROUP BY src_ip
        ORDER BY connection_count DESC
        LIMIT {limit};
    """
    return query_db(query)

def get_top_dst_ips(limit=20):
    """Récupérer les IPs destinations les plus sollicitées"""
    query = f"""
        SELECT dst_ip, COUNT(*) as connection_count,
               SUM(bytes) as total_bytes,
               MAX(timestamp) as last_seen
        FROM firewall_logs
        GROUP BY dst_ip
        ORDER BY connection_count DESC
        LIMIT {limit};
    """
    return query_db(query)

def get_traffic_timeline(hours=None, interval='hour'):
    """Récupérer l'évolution du trafic dans le temps"""
    if hours:
        time_condition = f"WHERE timestamp >= (SELECT MAX(timestamp) FROM firewall_logs) - INTERVAL '{hours} hours'"
    else:
        time_condition = ""

    query = f"""
        SELECT 
            DATE_TRUNC('{interval}', timestamp) as time_bucket,
            action,
            protocol,
            COUNT(*) as event_count,
            SUM(bytes) as total_bytes
        FROM firewall_logs
        {time_condition}
        GROUP BY time_bucket, action, protocol
        ORDER BY time_bucket;
    """
    return query_db(query)

def get_port_distribution():
    """Récupérer la distribution des ports destination"""
    query = """
        SELECT dst_port, protocol, COUNT(*) as count
        FROM firewall_logs
        GROUP BY dst_port, protocol
        ORDER BY count DESC
        LIMIT 50;
    """
    return query_db(query)

def search_logs(
    firewall_id=None, 
    src_ip=None, 
    dst_ip=None, 
    protocol=None, 
    action=None, 
    start_time=None, 
    end_time=None,
    limit=1000
):
    """Rechercher des logs avec des filtres"""
    conditions = []
    
    if firewall_id:
        conditions.append(f"firewall_id = '{firewall_id}'")
    if src_ip:
        conditions.append(f"src_ip = '{src_ip}'")
    if dst_ip:
        conditions.append(f"dst_ip = '{dst_ip}'")
    if protocol:
        conditions.append(f"protocol = '{protocol}'")
    if action:
        conditions.append(f"action = '{action}'")
    if start_time:
        conditions.append(f"timestamp >= '{start_time}'")
    if end_time:
        conditions.append(f"timestamp <= '{end_time}'")
    
    where_clause = " AND ".join(conditions) if conditions else "1=1"
    
    query = f"""
        SELECT * FROM firewall_logs
        WHERE {where_clause}
        ORDER BY timestamp DESC
        LIMIT {limit};
    """
    return query_db(query)
