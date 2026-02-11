"""
Firewall Logs Analysis - Classification & Severity Scoring
Analyse complète des logs firewall avec détection d'attaques, bugs et scoring de sévérité
Optimisé avec LazyFrame pour performances maximales
"""

import polars as pl
import glob
from pathlib import Path

# ============================================================================
# CONFIGURATION
# ============================================================================

INPUT_FOLDER = "/home/theo/Documents/projects/hackathon_dirisi/data/*.csv"
OUTPUT_FILE = "/home/theo/Documents/projects/hackathon_dirisi/firewall_logs_analyzed.csv"

# Patterns d'attaques
ATTACK_PATTERNS_REASON = [
    r'port scan', r'ssh brute force', r'brute force',
    r'XSS attempt', r'malware', r'DDoS', r'Potential DDoS',
    r'SQL injection', r'Suspicious SQL payload',
    r'Multiple auth failures', r'Known malicious domain',
    r'Command injection', r'Path traversal', r'Buffer overflow', r'Ransomware'
]

ATTACK_PATTERNS_FLAGS = [
    r'SCAN', r'AUTH_FAIL', r'XSS', r'MALWARE', r'DDOS', r'SQLI', r'EXPLOIT'
]

# Patterns d'attaques par sévérité
HIGH_SEVERITY_ATTACKS = [
    'ssh brute force', 'brute force', 'multiple auth failures',
    'malware', 'known malicious domain',
    'sql injection', 'suspicious sql payload',
    'ddos', 'potential ddos'
]

MEDIUM_SEVERITY_ATTACKS = ['port scan', 'xss attempt']

SUSPICIOUS_NORMAL_PATTERNS = [
    'suspicious payload', 'protocol violation', 'state mismatch', 'no policy'
]

# ============================================================================
# FONCTIONS DE DÉTECTION DES BUGS
# ============================================================================

def create_bug_detection_expressions():
    """Crée les expressions de détection des bugs"""
    
    # High severity bugs
    high_bugs = {
        'corrupted_line': pl.col('timestamp').cast(pl.Utf8).str.starts_with('CORRUPTED_LINE'),
        'malformed_timestamp': (
            pl.col('timestamp').cast(pl.Utf8).str.contains('99:99:99') |
            pl.col('timestamp').cast(pl.Utf8).str.contains('-13-') |
            pl.col('timestamp').cast(pl.Utf8).str.contains('-99T')
        ),
        'invalid_src_ip': pl.col('src_ip').cast(pl.Utf8).str.contains('999.999.999.999'),
        'invalid_dst_ip': pl.col('dst_ip').cast(pl.Utf8).str.contains('999.999.999.999')
    }
    
    # Medium severity bugs
    medium_bugs = {
        'negative_bytes': pl.col('bytes').cast(pl.Float64) < 0,
        'nonnumeric_src_port': pl.col('src_port').cast(pl.Utf8).str.contains(r'[^0-9]'),
        'nonnumeric_dst_port': pl.col('dst_port').cast(pl.Utf8).str.contains(r'[^0-9]'),
        'invalid_src_port': pl.col('src_port').cast(pl.Float64) > 65535,
        'invalid_dst_port': pl.col('dst_port').cast(pl.Float64) > 65535,
        'missing_src_port': pl.col('src_port').is_null(),
        'missing_dst_port': pl.col('dst_port').is_null()
    }
    
    # Low severity bugs
    low_bugs = {
        'missing_src_ip': pl.col('src_ip').is_null(),
        'missing_dst_ip': pl.col('dst_ip').is_null(),
        'missing_timestamp': pl.col('timestamp').is_null(),
        'missing_protocol': pl.col('protocol').is_null(),
        'missing_action': (pl.col('action').is_null()) | (pl.col('action').cast(pl.Utf8) == ''),
        'missing_reason': (pl.col('reason').is_null()) | (pl.col('reason').cast(pl.Utf8) == ''),
        'missing_firewall_id': (pl.col('firewall_id').is_null()) | (pl.col('firewall_id').cast(pl.Utf8) == ''),
        'invalid_session_id': (
            (pl.col('session_id').is_not_null()) & 
            (~pl.col('session_id').cast(pl.Utf8).str.contains(r'^[a-zA-Z0-9]{12}$'))
        ),
        'missing_rule_id': pl.col('rule_id').is_null()
    }
    
    return high_bugs, medium_bugs, low_bugs

def create_bug_columns(high_bugs, medium_bugs, low_bugs):
    """Crée les colonnes de bugs avec les noms appropriés"""
    
    bug_columns_expr = []
    bug_column_names = []
    
    # High severity bugs
    bug_columns_expr.extend([
        pl.when(high_bugs['corrupted_line']).then(pl.lit('CORRUPT_LINE')).alias('bug_corrupt'),
        pl.when(high_bugs['malformed_timestamp']).then(pl.lit('MALFORMED_TIMESTAMP')).alias('bug_malformed_ts'),
        pl.when(high_bugs['invalid_src_ip']).then(pl.lit('INVALID_IP_SRC')).alias('bug_invalid_src_ip'),
        pl.when(high_bugs['invalid_dst_ip']).then(pl.lit('INVALID_IP_DST')).alias('bug_invalid_dst_ip')
    ])
    bug_column_names.extend(['bug_corrupt', 'bug_malformed_ts', 'bug_invalid_src_ip', 'bug_invalid_dst_ip'])
    
    # Medium severity bugs
    bug_columns_expr.extend([
        pl.when(medium_bugs['negative_bytes']).then(pl.lit('NEGATIVE_BYTES')).alias('bug_neg_bytes'),
        pl.when(medium_bugs['nonnumeric_src_port'] | medium_bugs['invalid_src_port']).then(pl.lit('NONNUMERIC_PORT_SRC')).alias('bug_port_src'),
        pl.when(medium_bugs['nonnumeric_dst_port'] | medium_bugs['invalid_dst_port']).then(pl.lit('NONNUMERIC_PORT_DST')).alias('bug_port_dst'),
        pl.when(medium_bugs['missing_src_port']).then(pl.lit('MISSING_SRC_PORT')).alias('bug_missing_src_port'),
        pl.when(medium_bugs['missing_dst_port']).then(pl.lit('MISSING_DST_PORT')).alias('bug_missing_dst_port')
    ])
    bug_column_names.extend(['bug_neg_bytes', 'bug_port_src', 'bug_port_dst', 'bug_missing_src_port', 'bug_missing_dst_port'])
    
    # Low severity bugs
    bug_columns_expr.extend([
        pl.when(low_bugs['missing_src_ip']).then(pl.lit('MISSING_SRC_IP')).alias('bug_missing_src_ip'),
        pl.when(low_bugs['missing_dst_ip']).then(pl.lit('MISSING_DST_IP')).alias('bug_missing_dst_ip'),
        pl.when(low_bugs['missing_timestamp']).then(pl.lit('MISSING_TIMESTAMP')).alias('bug_missing_ts'),
        pl.when(low_bugs['missing_protocol']).then(pl.lit('MISSING_PROTOCOL')).alias('bug_missing_proto'),
        pl.when(low_bugs['missing_action']).then(pl.lit('MISSING_ACTION')).alias('bug_missing_action'),
        pl.when(low_bugs['missing_reason']).then(pl.lit('MISSING_REASON')).alias('bug_missing_reason'),
        pl.when(low_bugs['missing_firewall_id']).then(pl.lit('MISSING_FIREWALL_ID')).alias('bug_missing_firewall'),
        pl.when(low_bugs['invalid_session_id']).then(pl.lit('INVALID_SESSION_ID')).alias('bug_invalid_session'),
        pl.when(low_bugs['missing_rule_id']).then(pl.lit('MISSING_RULE_ID')).alias('bug_missing_rule')
    ])
    bug_column_names.extend([
        'bug_missing_src_ip', 'bug_missing_dst_ip', 'bug_missing_ts',
        'bug_missing_proto', 'bug_missing_action', 'bug_missing_reason',
        'bug_missing_firewall', 'bug_invalid_session', 'bug_missing_rule'
    ])
    
    return bug_columns_expr, bug_column_names

# ============================================================================
# FONCTIONS DE DÉTECTION DES ATTAQUES
# ============================================================================

def create_attack_detection_expressions():
    """Crée les expressions de détection des attaques"""
    
    reason_attack_pattern = '|'.join(f'(?:{p})' for p in ATTACK_PATTERNS_REASON)
    flags_attack_pattern = '|'.join(f'(?:{p})' for p in ATTACK_PATTERNS_FLAGS)
    
    is_attack_reason = pl.col('reason').cast(pl.Utf8).str.contains(f'(?i){reason_attack_pattern}')
    is_attack_flags = pl.col('flags').cast(pl.Utf8).str.contains(f'(?i){flags_attack_pattern}')
    
    return is_attack_reason | is_attack_flags

# ============================================================================
# FONCTIONS DE SCORING DE SÉVÉRITÉ
# ============================================================================

def create_severity_scoring_expressions():
    """Crée les expressions de scoring de sévérité"""
    
    # High severity attacks
    high_attack_pattern = '|'.join(f'(?:{p})' for p in HIGH_SEVERITY_ATTACKS)
    is_high_attack_reason = pl.col('reason').str.contains(high_attack_pattern)
    is_high_attack_flags = (
        pl.col('flags').str.contains('AUTH_FAIL') |
        pl.col('flags').str.contains('MALWARE') |
        pl.col('flags').str.contains('SQLI') |
        pl.col('flags').str.contains('DDOS')
    )
    is_high_attack = is_high_attack_reason | is_high_attack_flags
    
    # Medium severity attacks
    medium_attack_pattern = '|'.join(f'(?:{p})' for p in MEDIUM_SEVERITY_ATTACKS)
    is_medium_attack_reason = pl.col('reason').str.contains(medium_attack_pattern)
    is_medium_attack_flags = (
        pl.col('flags').str.contains('SCAN') |
        pl.col('flags').str.contains('XSS')
    )
    is_medium_attack = is_medium_attack_reason | is_medium_attack_flags
    
    # High severity bugs
    is_high_bug = (
        pl.col('bug_type').str.contains('CORRUPT_LINE') |
        pl.col('bug_type').str.contains('MALFORMED_TIMESTAMP') |
        pl.col('bug_type').str.contains('INVALID_IP')
    )
    
    # Medium severity bugs
    is_medium_bug = (
        pl.col('bug_type').str.contains('NEGATIVE_BYTES') |
        pl.col('bug_type').str.contains('NONNUMERIC_PORT') |
        pl.col('bug_type').str.contains('MISSING_SRC_PORT') |
        pl.col('bug_type').str.contains('MISSING_DST_PORT')
    )
    
    # Low severity bugs
    is_low_bug = (
        pl.col('bug_type').str.contains('MISSING_SRC_IP') |
        pl.col('bug_type').str.contains('MISSING_DST_IP') |
        pl.col('bug_type').str.contains('MISSING_TIMESTAMP') |
        pl.col('bug_type').str.contains('MISSING_PROTOCOL') |
        pl.col('bug_type').str.contains('MISSING_ACTION') |
        pl.col('bug_type').str.contains('MISSING_REASON') |
        pl.col('bug_type').str.contains('MISSING_FIREWALL_ID') |
        pl.col('bug_type').str.contains('INVALID_SESSION_ID') |
        pl.col('bug_type').str.contains('MISSING_RULE_ID')
    )
    
    # Suspicious normal patterns
    suspicious_pattern = '|'.join(f'(?:{p})' for p in SUSPICIOUS_NORMAL_PATTERNS)
    is_suspicious_normal = pl.col('reason').str.contains(suspicious_pattern)
    is_medium_normal = (
        is_suspicious_normal &
        pl.col('action').is_in(['DENY', 'DROP', 'REJECT'])
    )
    is_medium_normal_blocked = (
        ~is_suspicious_normal &
        pl.col('action').is_in(['DENY', 'DROP', 'REJECT'])
    )
    is_low_normal_suspicious = (
        is_suspicious_normal &
        ~pl.col('action').is_in(['DENY', 'DROP', 'REJECT'])
    )
    
    return {
        'high_attack': is_high_attack,
        'medium_attack': is_medium_attack,
        'high_bug': is_high_bug,
        'medium_bug': is_medium_bug,
        'low_bug': is_low_bug,
        'medium_normal': is_medium_normal,
        'medium_normal_blocked': is_medium_normal_blocked,
        'low_normal_suspicious': is_low_normal_suspicious
    }

def create_attack_type_column():
    """Crée la colonne attack_type"""
    
    return pl.when(pl.col('type') == 'Attack').then(
        pl.when(pl.col('reason').str.contains('sql injection|suspicious sql payload')).then(pl.lit('sql_injection'))
        .when(pl.col('reason').str.contains('ssh brute force|brute force|multiple auth failures')).then(pl.lit('brute_force_ssh'))
        .when(pl.col('reason').str.contains('malware|known malicious domain')).then(pl.lit('malware_download'))
        .when(pl.col('reason').str.contains('ddos|potential ddos')).then(pl.lit('ddos'))
        .when(pl.col('reason').str.contains('port scan')).then(pl.lit('port_scan'))
        .when(pl.col('reason').str.contains('xss attempt')).then(pl.lit('xss'))
        .otherwise(None)
    ).otherwise(None).alias('attack_type')

# ============================================================================
# FONCTION PRINCIPALE
# ============================================================================

def load_data(input_folder):
    """Charge les données CSV en mode lazy"""
    print("="*80)
    print(" CHARGEMENT DES DONNÉES (LAZY MODE)")
    print("="*80)
    
    csv_files = glob.glob(input_folder)
    print(f" Fichiers trouvés: {len(csv_files)}")
    
    df_list = []
    for f in csv_files:
        df_temp = pl.read_csv(f, null_values=["N/A", "NA", ""], infer_schema_length=10000)
        df_list.append(df_temp.lazy())
    
    df = pl.concat(df_list, how="diagonal")
    
    # Formater les timestamps
    df = df.with_columns([
        pl.col('timestamp')
        .str.to_datetime(format='%Y-%m-%dT%H:%M:%SZ', strict=False)
        .dt.strftime('%Y-%m-%d %H:%M:%S')
        .alias('timestamp')
    ])
    
    print(f" Données préparées en mode lazy")
    return df

def classify_logs(df):
    """Classifie les logs en Attack, Bug ou Normal"""
    print("="*80)
    print(" CLASSIFICATION DES LOGS")
    print("="*80)
    
    # Détection des bugs
    high_bugs, medium_bugs, low_bugs = create_bug_detection_expressions()
    bug_columns_expr, bug_column_names = create_bug_columns(high_bugs, medium_bugs, low_bugs)
    
    # Détection des attaques
    is_attack = create_attack_detection_expressions()
    
    # Ajouter les colonnes de détection
    df = df.with_columns(bug_columns_expr + [is_attack.alias('is_attack')])
    
    # Combiner tous les bugs en une seule colonne
    df = df.with_columns([
        pl.concat_str(
            [pl.col(col) for col in bug_column_names],
            separator='|',
            ignore_nulls=True
        ).alias('bug_type')
    ])
    
    # Remplacer les chaînes vides par null
    df = df.with_columns([
        pl.when(pl.col('bug_type') == '').then(None).otherwise(pl.col('bug_type')).alias('bug_type')
    ])
    
    # Classification finale: BUG > ATTACK > NORMAL
    df = df.with_columns([
        pl.when(pl.col('bug_type').is_not_null())
            .then(pl.lit('Bug'))
            .when(pl.col('is_attack'))
            .then(pl.lit('Attack'))
            .otherwise(pl.lit('Normal'))
            .alias('type')
    ])
    
    # Nettoyer colonnes temporaires
    df = df.drop(bug_column_names + ['is_attack'])
    
    print(" Classification terminée")
    return df

def score_severity(df):
    """Applique le scoring de sévérité"""
    print("="*80)
    print(" SCORING DE SÉVÉRITÉ")
    print("="*80)
    
    # Préparation des colonnes
    df = df.with_columns([
        pl.col('type').fill_null('NORMAL'),
        pl.col('reason').cast(pl.Utf8).fill_null('').str.to_lowercase(),
        pl.col('flags').cast(pl.Utf8).fill_null('').str.to_uppercase(),
        pl.col('action').cast(pl.Utf8).fill_null('').str.to_uppercase(),
        pl.col('bug_type').cast(pl.Utf8).fill_null(''),
        pl.col('protocol').cast(pl.Utf8).fill_null('').str.to_uppercase(),
    ])
    
    # Créer les expressions de scoring
    severity_exprs = create_severity_scoring_expressions()
    
    # Appliquer le scoring
    df = df.with_columns([
        pl.when(pl.col('type') == 'Attack')
            .then(
                pl.when(severity_exprs['high_attack']).then(pl.lit('High'))
                .when(severity_exprs['medium_attack']).then(pl.lit('Medium'))
                .otherwise(pl.lit('Low'))
            )
        .when(pl.col('type') == 'Bug')
            .then(
                pl.when(severity_exprs['high_bug']).then(pl.lit('High'))
                .when(severity_exprs['medium_bug']).then(pl.lit('Medium'))
                .when(severity_exprs['low_bug']).then(pl.lit('Low'))
                .otherwise(pl.lit('Medium'))
            )
        .otherwise(
            pl.when(severity_exprs['medium_normal'] | severity_exprs['medium_normal_blocked']).then(pl.lit('Medium'))
            .when(severity_exprs['low_normal_suspicious']).then(pl.lit('Low'))
            .otherwise(pl.lit('Low'))
        )
        .alias('severity')
    ])
    
    # Ajouter la colonne attack_type
    df = df.with_columns([create_attack_type_column()])
    
    print(" Scoring terminé")
    return df

def save_results(df, output_file):
    """Sauvegarde les résultats"""
    print("\n" + "="*80)
    print(" EXÉCUTION ET SAUVEGARDE")
    print("="*80)
    
    # Collecter les résultats
    df_result = df.collect()
    
    # Supprimer les lignes corrompues
    df_result = df_result.filter(~pl.col('bug_type').cast(pl.Utf8).str.contains('CORRUPT_LINE'))
    
    print(f" Pipeline exécuté: {len(df_result):,} logs traités")
    
    # Statistiques
    print_statistics(df_result)
    
    # Sauvegarder
    print(f"\n Sauvegarde en cours...")
    print(f"   Colonnes: {df_result.columns}")
    print(f"   Shape: {df_result.shape}")
    
    if len(df_result) == 0:
        print(" ERREUR: DataFrame vide!")
        return None
    
    try:
        df_result.write_csv(output_file)
        print(f" Fichier sauvegardé: {output_file}")
        
        import os
        file_size = os.path.getsize(output_file)
        print(f"   Taille du fichier: {file_size:,} bytes")
        
        if file_size == 0:
            print("  Fichier vide détecté! Tentative avec méthode alternative...")
            df_result.to_pandas().to_csv(output_file, index=False)
            file_size = os.path.getsize(output_file)
            print(f"   Nouvelle taille: {file_size:,} bytes")
            
    except Exception as e:
        print(f" Erreur lors de la sauvegarde: {e}")
        print("   Tentative avec pandas...")
        df_result.to_pandas().to_csv(output_file, index=False)
        print(f" Sauvegardé via pandas")
    
    return df_result

def print_statistics(df_result):
    """Affiche les statistiques"""
    print("\n Statistiques:")
    print(f"  • Attaques:  {len(df_result.filter(pl.col('type') == 'Attack')):,}")
    print(f"  • Bugs:      {len(df_result.filter(pl.col('type') == 'Bug')):,}")
    print(f"  • Normal:    {len(df_result.filter(pl.col('type') == 'Normal')):,}")
    print(f"\n  • High:      {len(df_result.filter(pl.col('severity') == 'High')):,}")
    print(f"  • Medium:    {len(df_result.filter(pl.col('severity') == 'Medium')):,}")
    print(f"  • Low:       {len(df_result.filter(pl.col('severity') == 'Low')):,}")

def print_results_preview(df_result):
    """Affiche un aperçu des résultats"""
    print("\n" + "="*80)
    print("  APERÇU DES RÉSULTATS")
    print("="*80)
    
    print(f"Lignes dans df_result: {len(df_result)}")
    print(f"Colonnes: {df_result.columns}")
    
    if len(df_result) > 0:
        print(df_result.select(['timestamp', 'src_ip', 'dst_ip', 'type', 'severity', 'attack_type', 'reason']).head(10))
    else:
        print("  DataFrame vide - aucune donnée à afficher")

def print_summary():
    """Affiche le résumé final"""
    print("\n" + "="*80)
    print(" ANALYSE TERMINÉE")
    print("="*80)
    print(f"\n Colonnes générées:")
    print(f"  • type: Attack | Bug | Normal")
    print(f"  • severity: High | Medium | Low")
    print(f"  • attack_type: sql_injection | brute_force_ssh | malware_download | ddos | port_scan | xss")
    print(f"  • bug_type: Détail des anomalies détectées")
    print(f"  • timestamp: Format yyyy-MM-dd HH:mm:ss")
    print("="*80)

# ============================================================================
# POINT D'ENTRÉE
# ============================================================================

def main():
    """Fonction principale"""
    # Chargement des données
    df = load_data(INPUT_FOLDER)
    
    # Classification
    df = classify_logs(df)
    
    # Scoring de sévérité
    df = score_severity(df)
    
    # Sauvegarde
    df_result = save_results(df, OUTPUT_FILE)
    
    if df_result is not None:
        # Aperçu
        print_results_preview(df_result)
        
        # Résumé
        print_summary()

if __name__ == "__main__":
    main()