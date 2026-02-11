import streamlit as st
import time

st.set_page_config(
    page_title="Assistant IA",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Assistant Cyber-Sécurité IA")
st.markdown("discutez avec l'assistant pour obtenir des analyses sur les logs ou de l'aide sur les incidents.")
st.markdown("---")

# Initialiser l'historique de chat
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "Bonjour ! Je suis votre assistant de sécurité. Comment puis-je vous aider aujourd'hui ? Je peux analyser des IPs, expliquer des alertes ou suggérer des remédiations."}
    ]

# Afficher les messages précédents
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Zone de saisie utilisateur
if prompt := st.chat_input("Posez votre question ici..."):
    # Afficher le message utilisateur
    with st.chat_message("user"):
        st.markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    # Réponse simulée de l'IA (Mock)
    with st.chat_message("assistant"):
        message_placeholder = st.empty()
        full_response = ""
        
        # Simulation de délai et de réponse contextuelle simple
        response_text = "Je ne suis pas encore connecté à un véritable LLM, mais voici une réponse simulée basés sur votre demande."
        
        if "ip" in prompt.lower():
            response_text = "J'ai analysé cette IP dans les logs. Elle a été bloquée 15 fois au cours de la dernière heure. Elle est connue pour des activités de scan de ports. Je recommande de la bloquer définitivement."
        elif "alerte" in prompt.lower() or "ticket" in prompt.lower():
            response_text = "L'alerte la plus critique actuelle concerne une tentative d'intrusion SSH brute force. Le ticket TICKET-8392 est ouvert. Voulez-vous que je génère un rapport ?"
        elif "playbook" in prompt.lower():
            response_text = "Je peux vous rediriger vers la page des Playbooks pour lancer une procédure automatique."
        
        # Effet de 'typing'
        for chunk in response_text.split():
            full_response += chunk + " "
            time.sleep(0.05)
            message_placeholder.markdown(full_response + "▌")
        message_placeholder.markdown(full_response)
    
    st.session_state.messages.append({"role": "assistant", "content": full_response})

# Sidebar avec infos contextuelles
with st.sidebar:
    st.header("🧠 Contexte IA")
    st.info("Modèle: Security-LLM-v1 (Simulé)")
    st.success("Statut: Connecté")
    
    st.subheader("💡 Suggestions")
    st.caption("- Analyse l'IP 192.168.1.50")
    st.caption("- Quels sont les incidents critiques ?")
    st.caption("- Explique l'alerte SSH Brute Force")
    
    if st.button("🗑️ Effacer la conversation"):
        st.session_state.messages = []
        st.rerun()
