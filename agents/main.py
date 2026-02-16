import os
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from openai import OpenAI
import psycopg2
import psycopg2.extras

app = FastAPI(title="CLAIR OBSCUR AI Agent")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# OpenAI client
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# Database config
DB_CONFIG = {
    "host": os.getenv("DATABASE_HOST", "postgres"),
    "port": int(os.getenv("DATABASE_PORT", 5432)),
    "user": os.getenv("DATABASE_USER", ""),
    "password": os.getenv("DATABASE_PASSWORD", ""),
    "dbname": os.getenv("DATABASE_NAME", ""),
}

SYSTEM_PROMPT = """Tu es un analyste expert en cybersécurité pour la plateforme CLAIR OBSCUR.
Tu analyses des logs firewall et tu aides les opérateurs à comprendre les menaces détectées.

Voici le contexte de la base de données :
- Table `firewall_logs` : logs réseau avec colonnes timestamp, firewall_id, src_ip, dst_ip, src_port, dst_port, protocol, action, bytes, duration_ms, reason, severity, flags, bug_type, log_category
- Table `firewall_suspicious_ips` : IPs suspectes avec ip_address, blocked_count, risk_level
- Table `firewall_stats_hourly` : statistiques horaires agrégées
- Table `firewall_top_ports` : ports les plus utilisés

Réponds de manière concise et professionnelle.
Quand tu mentionnes des données, cite les chiffres exacts de la base.
Utilise le français sauf si l'utilisateur parle en anglais.
"""


def get_db_context() -> str:
    """Fetch a summary of current DB state to give context to the LLM."""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

        context_parts = []

        # Total logs
        cur.execute("SELECT COUNT(*) as total FROM firewall_logs")
        total = cur.fetchone()["total"]
        context_parts.append(f"Total logs : {total}")

        if total > 0:
            # Severity breakdown
            cur.execute(
                "SELECT severity, COUNT(*) as cnt FROM firewall_logs "
                "GROUP BY severity ORDER BY cnt DESC"
            )
            rows = cur.fetchall()
            sev = ", ".join(f"{r['severity']}: {r['cnt']}" for r in rows if r["severity"])
            context_parts.append(f"Sévérité : {sev}")

            # Action breakdown
            cur.execute(
                "SELECT action, COUNT(*) as cnt FROM firewall_logs "
                "GROUP BY action ORDER BY cnt DESC LIMIT 5"
            )
            rows = cur.fetchall()
            acts = ", ".join(f"{r['action']}: {r['cnt']}" for r in rows if r["action"])
            context_parts.append(f"Actions : {acts}")

            # Top protocols
            cur.execute(
                "SELECT protocol, COUNT(*) as cnt FROM firewall_logs "
                "GROUP BY protocol ORDER BY cnt DESC LIMIT 5"
            )
            rows = cur.fetchall()
            protos = ", ".join(f"{r['protocol']}: {r['cnt']}" for r in rows if r["protocol"])
            context_parts.append(f"Protocoles : {protos}")

            # Recent critical logs
            cur.execute(
                "SELECT timestamp, src_ip, dst_ip, action, reason, severity "
                "FROM firewall_logs WHERE severity = 'High' "
                "ORDER BY timestamp DESC LIMIT 5"
            )
            rows = cur.fetchall()
            if rows:
                recent = []
                for r in rows:
                    recent.append(
                        f"  [{r['timestamp']}] {r['src_ip']} -> {r['dst_ip']} "
                        f"({r['action']}) {r['reason']}"
                    )
                context_parts.append("Derniers événements critiques :\n" + "\n".join(recent))

        # Suspicious IPs
        cur.execute(
            "SELECT ip_address, blocked_count, risk_level "
            "FROM firewall_suspicious_ips ORDER BY blocked_count DESC LIMIT 5"
        )
        rows = cur.fetchall()
        if rows:
            ips = ", ".join(
                f"{r['ip_address']} ({r['blocked_count']} blocs, {r['risk_level']})"
                for r in rows
            )
            context_parts.append(f"IPs suspectes : {ips}")

        cur.close()
        conn.close()

        return "\n".join(context_parts) if context_parts else "Base de données vide."

    except Exception as e:
        return f"Impossible de lire la base de données : {e}"


class ChatRequest(BaseModel):
    message: str


class ChatResponse(BaseModel):
    response: str


@app.post("/chat", response_model=ChatResponse)
async def chat(req: ChatRequest):
    try:
        db_context = get_db_context()

        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {
                "role": "system",
                "content": f"État actuel de la base de données :\n{db_context}",
            },
            {"role": "user", "content": req.message},
        ]

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            max_tokens=1024,
            temperature=0.3,
        )

        return ChatResponse(response=response.choices[0].message.content)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/health")
def health():
    return {"status": "ok"}
