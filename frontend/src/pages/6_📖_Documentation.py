import streamlit as st

st.set_page_config(
    page_title="Documentation",
    page_icon="📖",
    layout="wide"
)

st.title("📖 Documentation de la Plateforme")
st.markdown("---")

# Navigation rapide
st.sidebar.markdown("## Sommaire")
st.sidebar.markdown("[1. Vue d'ensemble](#1-vue-d-ensemble)")
st.sidebar.markdown("[2. Structure des Logs](#2-structure-des-logs)")
st.sidebar.markdown("[3. Types d'Anomalies](#3-types-d-anomalies)")
st.sidebar.markdown("[4. Cyberattaques](#4-cyberattaques-communes)")

# 1. Vue d'ensemble
st.header("1. Vue d'ensemble")
st.markdown("""
Cette plateforme d'analyse de sécurité (SOC Dashboard) permet de surveiller, détecter et réagir aux incidents de sécurité en temps réel.
Elle est composée de plusieurs modules :
*   **Dashboard** : Vue synthétique de l'activité du réseau.
*   **Analyse Temporelle** : Étude de l'évolution du trafic pour détecter des tendances ou des pics anormaux.
*   **Recherche de Logs** : Outil d'investigation précis.
*   **Alertes de Sécurité** : Système de tickets générés automatiquement par nos algorithmes de Machine Learning.
*   **Playbooks** : Procédures de réponse aux incidents automatisées ou guidées.
""")

st.markdown("---")

# 2. Structure des Logs
st.header("2. Structure des Logs")
st.markdown("""
Les logs collectés proviennent des pare-feu et contiennent les informations suivantes :

| Champ | Description | Exemple |
|-------|-------------|---------|
| `timestamp` | Date et heure de l'événement | `2025-04-02 10:15:30` |
| `src_ip` | Adresse IP source (initiant la connexion) | `192.168.1.50` |
| `dst_ip` | Adresse IP destination (cible) | `10.0.0.5` |
| `src_port` | Port source | `49152` |
| `dst_port` | Port destination | `80` (HTTP) |
| `protocol` | Protocole de transport | `TCP`, `UDP`, `ICMP` |
| `action` | Action prise par le pare-feu | `ALLOW` (Autorisé), `DENY` (Bloqué) |
| `bytes` | Volume de données échangées (octets) | `1540` |
""")

st.markdown("---")

# 3. Types d'Anomalies
st.header("3. Types d'Anomalies")
st.markdown("""
Notre système de détection classe les incidents en deux catégories principales :

### 🔧 Pannes Système (Failure)
Incidents liés au fonctionnement de l'infrastructure, sans intention malveillante.
*   **Symptômes** : Perte de connectivité, latence élevée, redémarrage inattendu d'un service.
*   **Exemples** :
    *   *Surcharge CPU/RAM* sur un pare-feu.
    *   *Panne lien WAN* : Interruption de la connexion internet.
    *   *Erreur de configuration* : Règle de pare-feu mal configurée bloquant du trafic légitime.

### ⚔️ Cyberattaques (Security Incident)
Actions malveillantes visant à compromettre la confidentialité, l'intégrité ou la disponibilité du système.
*   **Symptômes** : Pics de trafic inexpliqués, connexions depuis des IP inconnues/suspectes, multiples échecs d'authentification.
""")

st.markdown("---")

# 4. Cyberattaques Communes
st.header("4. Cyberattaques Communes")

with st.expander("🔍 Port Scanning (Balayage de Ports)"):
    st.markdown("""
    **Définition** : Technique utilisée par les attaquants pour découvrir les services ouverts sur une machine cible.
    **Détection** : Une seule IP source tente de se connecter à de nombreux ports différents sur une courte période.
    **Dangerosité** : Faible (Reconnaissance), mais précède souvent une attaque plus ciblée.
    """)

with st.expander("🔨 Brute Force (Attaque par Force Brute)"):
    st.markdown("""
    **Définition** : Tentative de deviner un mot de passe en essayant toutes les combinaisons possibles.
    **Détection** : Nombre élevé de connexions (souvent sur le port 22/SSH ou 3389/RDP) avec un faible volume de données, suivies d'échecs.
    **Dangerosité** : Élevée. Si réussie, l'attaquant gagne un accès au système.
    """)

with st.expander("🌊 DDoS (Déni de Service Distribué)"):
    st.markdown("""
    **Définition** : Attaque visant à rendre un service indisponible en le surchargeant de trafic provenant de multiples sources.
    **Détection** : Augmentation massive et soudaine du volume de logs et du trafic réseau (bytes).
    **Dangerosité** : Critique. Peut paralyser toute l'entreprise.
    """)

with st.expander("🕵️ Man-in-the-Middle (MITM)"):
    st.markdown("""
    **Définition** : L'attaquant s'intercepte dans la communication entre deux parties sans qu'elles le sachent.
    **Indices** : Changements suspects dans les routes réseaux ou les certificats SSL (difficile à voir uniquement avec des logs firewall basiques).
    """)

st.info("💡 Pour plus de détails techniques, consultez la documentation interne du SOC ou demandez à l'Assistant IA.")

st.markdown("---")
st.caption("Documentation générée pour le Hackathon CND")
