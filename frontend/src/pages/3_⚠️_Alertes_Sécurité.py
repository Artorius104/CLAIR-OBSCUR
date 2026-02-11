import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import random
from datetime import datetime, timedelta
import time

# Configuration de la page
st.set_page_config(
    page_title="Alertes de Sécurité",
    page_icon="⚠️",
    layout="wide"
)

st.title("⚠️ Alertes et Menaces de Sécurité")
st.markdown("---")

# Simulation de données ML (Mock)
@st.cache_data(ttl=600)
def generate_ml_tickets(n=25):
    tickets = []
    types = ["Cyberattaque", "Panne Système", "Anomalie Réseau", "Intrusion Suspecte"]
    criticalities = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]
    statuses = ["Open", "Investigating", "Resolved", "False Positive"]
    
    for i in range(n):
        ticket_id = f"TICKET-{random.randint(1000, 9999)}"
        timestamp = datetime.now() - timedelta(minutes=random.randint(1, 1440))
        anomaly_type = random.choice(types)
        criticality = random.choices(criticalities, weights=[0.1, 0.3, 0.4, 0.2])[0]
        status = random.choices(statuses, weights=[0.4, 0.3, 0.2, 0.1])[0]
        confidence = random.uniform(0.75, 0.99)
        src_ip = f"192.168.{random.randint(1, 255)}.{random.randint(1, 255)}"
        
        description = ""
        if anomaly_type == "Cyberattaque":
            description = f"Détection de tentative d'intrusion depuis {src_ip} (Pattern match: SSH Brute Force)"
        elif anomaly_type == "Panne Système":
            description = f"Latence anormale détectée sur le Firewall FW-{random.choice(['A', 'B', 'C'])}"
        elif anomaly_type == "Anomalie Réseau":
            description = f"Pic de trafic inhabituel sur le port {random.randint(1024, 65535)}"
        else:
            description = f"Comportement suspect détecté pour l'utilisateur {random.choice(['admin', 'user1', 'service_account'])}"
            
        tickets.append({
            "Ticket ID": ticket_id,
            "Date/Heure": timestamp,
            "Type d'Anomalie": anomaly_type,
            "Criticité": criticality,
            "Status": status,
            "Confiance ML": f"{confidence:.2%}",
            "Description": description,
            "IP Source": src_ip
        })
    
    df = pd.DataFrame(tickets)
    return df.sort_values("Date/Heure", ascending=False)

# Chargement des tickets
tickets_df = generate_ml_tickets()

# Sidebar
with st.sidebar:
    st.header("⚙️ Filtres d'Alertes")
    
    selected_criticality = st.multiselect(
        "Criticité",
        ["CRITICAL", "HIGH", "MEDIUM", "LOW"],
        default=["CRITICAL", "HIGH"]
    )
    
    selected_status = st.multiselect(
        "Status",
        ["Open", "Investigating", "Resolved", "False Positive"],
        default=["Open", "Investigating"]
    )
    
    if st.button("🔄 Rafraîchir les Tickets", use_container_width=True):
        st.cache_data.clear()
        st.rerun()

# Filtrage
filtered_tickets = tickets_df.copy()
if selected_criticality:
    filtered_tickets = filtered_tickets[filtered_tickets['Criticité'].isin(selected_criticality)]
if selected_status:
    filtered_tickets = filtered_tickets[filtered_tickets['Status'].isin(selected_status)]

# KPIs
st.subheader("📊 Vue d'ensemble des Incidents")
col1, col2, col3, col4 = st.columns(4)

with col1:
    critical_count = len(tickets_df[tickets_df['Criticité'] == 'CRITICAL'])
    st.metric("Alertes CRITICAL", critical_count, delta="Prioritaire", delta_color="inverse")

with col2:
    open_count = len(tickets_df[tickets_df['Status'] == 'Open'])
    st.metric("Tickets Ouverts", open_count)

with col3:
    cyber_count = len(tickets_df[tickets_df["Type d'Anomalie"] == 'Cyberattaque'])
    st.metric("Cyberattaques Détectées", cyber_count, delta_color="inverse")

with col4:
    avg_conf = float(tickets_df['Confiance ML'].str.rstrip('%').astype(float).mean())
    st.metric("Confiance ML Moyenne", f"{avg_conf:.1f}%")

st.markdown("---")

# Affichage des Tickets
st.subheader("📋 Tickets d'Anomalies ML")

# Style conditionnel pour la table
def color_criticality(val):
    if val == 'CRITICAL':
        return 'color: red; font-weight: bold'
    elif val == 'HIGH':
        return 'color: orange; font-weight: bold'
    return ''

st.dataframe(
    filtered_tickets.style.map(color_criticality, subset=['Criticité']),
    use_container_width=True,
    height=400,
    column_config={
        "Confiance ML": st.column_config.ProgressColumn(
            "Confiance ML",
            min_value=0,
            max_value=100,
            format="%f%%",
        ),
    }
)

# Détails et Actions
st.markdown("### 🕵️ Investigation Rapide")
selected_ticket_id = st.selectbox("Sélectionner un ticket pour investigation", filtered_tickets['Ticket ID'].unique())

if selected_ticket_id:
    ticket_details = filtered_tickets[filtered_tickets['Ticket ID'] == selected_ticket_id].iloc[0]
    
    with st.container():
        st.info(f"Détails du Ticket: {selected_ticket_id}")
        col_det1, col_det2 = st.columns(2)
        
        with col_det1:
            anomaly_type = ticket_details.get('Type d\'Anomalie', 'Inconnu')
            st.write(f"**Type:** {anomaly_type}")
            st.write(f"**Date:** {ticket_details['Date/Heure']}")
            st.write(f"**Source:** {ticket_details['IP Source']}")
        
        with col_det2:
            st.write(f"**Status:** {ticket_details['Status']}")
            st.write(f"**Criticité:** {ticket_details['Criticité']}")
            st.write(f"**Confiance:** {ticket_details['Confiance ML']}")
            
        st.markdown("**Description:**")
        st.warning(ticket_details['Description'])
        
        st.markdown("#### Actions Recommandées (Générées par IA)")
        
        # Mock Actions
        if ticket_details["Type d'Anomalie"] == "Cyberattaque":
            st.code("1. Bloquer l'IP source sur le Firewall Périphérique\n2. Isoler le segment réseau infecté\n3. Analyser les logs d'authentification", language="text")
        elif ticket_details["Type d'Anomalie"] == "Panne Système":
             st.code("1. Vérifier l'état du service Firewall\n2. Redémarrer le service si nécessaire\n3. Vérifier la charge CPU/RAM", language="text")
        else:
             st.code("1. Vérifier les logs détaillés\n2. Contacter l'utilisateur concerné", language="text")
             
        col_act1, col_act2 = st.columns(2)
        with col_act1:
            if st.button("🚀 Lancer le Playbook de Remédiation", key="playbook"):
                st.success("Playbook initié avec succès ! (Simulation)")
        with col_act2:
             if st.button("❌ Fermer le Ticket (Faux Positif)", key="close"):
                st.info("Ticket marqué comme faux positif.")

