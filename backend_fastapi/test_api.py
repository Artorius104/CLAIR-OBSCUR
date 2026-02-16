from fastapi.testclient import TestClient
from app.main import app
from app.core.config import settings

client = TestClient(app)

def test_create_log():
    log_data = {
        "timestamp": "2026-02-11T12:00:00",
        "src_ip": "192.168.1.10",
        "dst_ip": "10.0.0.5",
        "reason": "SSH Brute Force",
        "action": "DROP",
        "protocol": "TCP",
        "dst_port": 22
    }
    
    response = client.post(f"{settings.API_V1_STR}/logs/", json=log_data)
    assert response.status_code == 200
    data = response.json()
    print("Create Log Response:", data)
    assert data["src_ip"] == "192.168.1.10"
    assert data["log_type"] == "Attack" # Detection logic
    assert data["severity"] == "High" # Severity logic
    assert data["attack_type"] == "brute_force_ssh"

def test_read_stats():
    response = client.get(f"{settings.API_V1_STR}/logs/stats")
    assert response.status_code == 200
    data = response.json()
    print("Stats Response:", data)
    assert "total_logs" in data
    assert "severity" in data

if __name__ == "__main__":
    try:
        test_create_log()
        test_read_stats()
        print("ALL TESTS PASSED")
    except Exception as e:
        print(f"TEST FAILED: {e}")
        exit(1)
