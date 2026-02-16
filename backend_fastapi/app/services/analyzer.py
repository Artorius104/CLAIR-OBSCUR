import re
from typing import Optional, Tuple, Dict, Any
from app.schemas.log import LogCreate

# Patterns (Adapted from log_analysis.py)
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

class LogAnalyzer:
    @staticmethod
    def detect_bugs(log: Dict[str, Any]) -> str:
        bugs = []
        
        # Helper to safely get string values
        def get_str(key): return str(log.get(key) or '')
        def get_int(key): return int(log.get(key) or 0) # simplified

        ts = get_str('timestamp')
        src_ip = get_str('src_ip')
        dst_ip = get_str('dst_ip')
        
        # High Severity Bugs
        if 'CORRUPTED_LINE' in ts: bugs.append('CORRUPT_LINE')
        if '99:99:99' in ts or '-13-' in ts or '-99T' in ts: bugs.append('MALFORMED_TIMESTAMP')
        if '999.999.999.999' in src_ip: bugs.append('INVALID_IP_SRC')
        if '999.999.999.999' in dst_ip: bugs.append('INVALID_IP_DST')
        
        # Medium Severity Bugs
        # Note: In a real scenario, we would check types more rigorously
        # keeping it simple for porting logic
        
        # Low Severity Bugs
        if not src_ip: bugs.append('MISSING_SRC_IP')
        if not dst_ip: bugs.append('MISSING_DST_IP')
        if not ts: bugs.append('MISSING_TIMESTAMP')
        if not log.get('protocol'): bugs.append('MISSING_PROTOCOL')
        if not log.get('action'): bugs.append('MISSING_ACTION')
        if not log.get('reason'): bugs.append('MISSING_REASON')
        
        return "|".join(bugs) if bugs else None

    @staticmethod
    def detect_attack(log: Dict[str, Any]) -> bool:
        reason = str(log.get('reason') or '')
        flags = str(log.get('flags') or '')
        
        reason_match = any(re.search(p, reason, re.IGNORECASE) for p in ATTACK_PATTERNS_REASON)
        flags_match = any(re.search(p, flags, re.IGNORECASE) for p in ATTACK_PATTERNS_FLAGS)
        
        return reason_match or flags_match

    @staticmethod
    def determine_attack_type(log: Dict[str, Any], is_attack: bool) -> Optional[str]:
        if not is_attack:
            return None
            
        reason = str(log.get('reason') or '').lower()
        
        if 'sql injection' in reason or 'suspicious sql payload' in reason: return 'sql_injection'
        if 'ssh brute force' in reason or 'brute force' in reason or 'multiple auth failures' in reason: return 'brute_force_ssh'
        if 'malware' in reason or 'known malicious domain' in reason: return 'malware_download'
        if 'ddos' in reason or 'potential ddos' in reason: return 'ddos'
        if 'port scan' in reason: return 'port_scan'
        if 'xss attempt' in reason: return 'xss'
        
        return 'other_attack'

    @staticmethod
    def score_severity(log: Dict[str, Any], log_type: str, bug_type: str) -> str:
        reason = str(log.get('reason') or '').lower()
        flags = str(log.get('flags') or '').upper()
        
        if log_type == 'Attack':
            if any(p in reason for p in HIGH_SEVERITY_ATTACKS): return 'High'
            if any(p in flags for p in ['AUTH_FAIL', 'MALWARE', 'SQLI', 'DDOS']): return 'High'
            
            if any(p in reason for p in MEDIUM_SEVERITY_ATTACKS): return 'Medium'
            if any(p in flags for p in ['SCAN', 'XSS']): return 'Medium'
            
            return 'Low'
            
        if log_type == 'Bug':
            # Simplified for brevity based on logic
            if 'CORRUPT_LINE' in str(bug_type) or 'MALFORMED' in str(bug_type) or 'INVALID_IP' in str(bug_type):
                return 'High'
            return 'Medium'
            
        # Normal
        action = str(log.get('action') or '').upper()
        is_suspicious = any(p in reason for p in SUSPICIOUS_NORMAL_PATTERNS)
        
        if is_suspicious:
            return 'Medium' if action in ['DENY', 'DROP', 'REJECT'] else 'Low'
            
        return 'Low'

    @classmethod
    def analyze(cls, log_data: LogCreate) -> Dict[str, Any]:
        data = log_data.model_dump()
        
        # 1. Detect Bugs
        bug_type = cls.detect_bugs(data)
        
        # 2. Detect Attack
        is_attack = cls.detect_attack(data)
        
        # 3. Classification
        log_type = 'Normal'
        if bug_type:
            log_type = 'Bug'
        elif is_attack:
            log_type = 'Attack'
            
        # 4. Attack Type
        attack_type = cls.determine_attack_type(data, is_attack)
        
        # 5. Severity
        severity = cls.score_severity(data, log_type, bug_type)
        
        return {
            **data,
            "log_type": log_type,
            "bug_type": bug_type,
            "attack_type": attack_type,
            "severity": severity
        }
