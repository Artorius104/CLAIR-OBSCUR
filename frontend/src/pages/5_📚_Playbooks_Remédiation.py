import streamlit as st
import time

st.set_page_config(
    page_title="Playbooks de Remédiation",
    page_icon="📚",
    layout="wide"
)

st.title("📚 Playbooks de Remédiation Automatisés")
st.markdown("---")

# Sidebar
with st.sidebar:
    st.header("🔧 Bibliothèque")
    category = st.selectbox("Catégorie", ["Tous", "Réseau", "Système", "Utilisateur", "Cloud"])
    search = st.text_input("Rechercher un playbook")

# Mock Playbooks
playbooks = [
    {
        "id": "PB-001",
        "title": "Blocage IP Malveillante",
        "description": "Bloque une IP sur tous les firewalls et termine les sessions actives.",
        "category": "Réseau",
        "tags": ["Firewall", "Urgent", "Automatique"],
        "steps": ["Vérification IP", "Backup Config Firewall", "Ajout Règle DROP", "Kill Sessions", "Notification SOC"]
    },
    {
        "id": "PB-002",
        "title": "Isolation Hôte infecté",
        "description": "Isole une machine du réseau via le switch ou l'EDR.",
        "category": "Système",
        "tags": ["Endpoint", "Virus", "Manuel"],
        "steps": ["Identification MAC", "Switch Port Shutdown", "EDR Isolation", "Notification Utilisateur"]
    },
    {
        "id": "PB-003",
        "title": "Reset Compte Compromis",
        "description": "Réinitialise le mot de passe et révoque les tokens.",
        "category": "Utilisateur",
        "tags": ["IAM", "Phishing"],
        "steps": ["Verrouillage Compte", "Révocation Tokens", "Force Password Reset", "Analyse Logs Connexion"]
    }
]

# Filtrage
filtered_playbooks = playbooks
if category != "Tous":
    filtered_playbooks = [p for p in filtered_playbooks if p["category"] == category]
if search:
    filtered_playbooks = [p for p in filtered_playbooks if search.lower() in p["title"].lower()]

# Affichage en Grille/Cartes
col1, col2 = st.columns([1, 2])

with col1:
    st.subheader("📖 Liste des Playbooks")
    for pb in filtered_playbooks:
        with st.expander(f"{pb['id']} - {pb['title']}"):
            st.caption(pb['description'])
            st.write(f"**Tags:** {', '.join(pb['tags'])}")
            if st.button("Détails", key=f"btn_{pb['id']}"):
                st.session_state.selected_playbook = pb

# Zone d'exécution
with col2:
    st.subheader("⚙️ Exécution")
    
    if "selected_playbook" in st.session_state:
        pb = st.session_state.selected_playbook
        
        st.markdown(f"### {pb['title']}")
        st.info(f"**Description:** {pb['description']}")
        
        st.write("**Étapes du Playbook :**")
        for i, step in enumerate(pb['steps']):
            st.markdown(f"{i+1}. {step}")
            
        st.markdown("---")
        
        # Configuration de l'exécution
        target = st.text_input("Cible (IP, Hostname, Username)", placeholder="ex: 192.168.1.50")
        approval = st.checkbox("Je confirme avoir l'autorisation d'exécuter ce playbook")
        
        if st.button("🚀 Lancer l'exécution", disabled=not (target and approval)):
            with st.status("Exécution en cours...", expanded=True) as status:
                for step in pb['steps']:
                    st.write(f"🔄 Exécution: {step}...")
                    time.sleep(1) # Simulation
                    st.write(f"✅ {step} terminé.")
                status.update(label="Exécution terminée avec succès !", state="complete", expanded=False)
            
            st.balloons()
            st.success(f"Playbook {pb['id']} exécuté sur {target}")
            
    else:
        st.info("👈 Sélectionnez un playbook dans la liste pour voir les détails.")

st.markdown("---")
st.caption("Généré par Agent IA - Hackathon CND")
