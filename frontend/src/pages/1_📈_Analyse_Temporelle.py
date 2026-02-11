import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database.getDataFromDatabase import *
from datetime import datetime, timedelta
import time

st.set_page_config(
    page_title="Analyse Temporelle",
    page_icon="📈",
    layout="wide"
)

st.title("📈 Analyse Temporelle des Logs Firewall")
st.markdown("---")

# Sidebar pour les filtres
with st.sidebar:
    st.header("⚙️ Paramètres")
    
    time_range = st.selectbox(
        "Période d'analyse",
        ["Dernières 6 heures", "Dernières 24 heures", "Derniers 3 jours", "Derniers 7 jours"],
        index=1
    )
    
    interval = st.selectbox(
        "Intervalle d'agrégation",
        ["5 minutes", "15 minutes", "hour", "day"],
        index=2
    )
    
    # Auto-refresh removed as requested
    
# Mapping des périodes
time_mapping = {
    "Dernières 6 heures": 6,
    "Dernières 24 heures": 24,
    "Derniers 3 jours": 72,
    "Derniers 7 jours": 168
}

hours = time_mapping.get(time_range, 24)

# Charger les données
@st.cache_data(ttl=60)
def load_temporal_data(hours, interval):
    try:
        timeline = get_traffic_timeline(hours, interval)
        hourly_stats = get_hourly_stats(hours)
        return timeline, hourly_stats
    except Exception as e:
        st.error(f"Erreur: {e}")
        return None, None

with st.spinner("Chargement des données temporelles..."):
    timeline, hourly_stats = load_temporal_data(hours, interval)

if timeline is not None and not timeline.empty:
    
    # Graphique principal : Évolution du trafic
    st.subheader("🌊 Évolution du Trafic dans le Temps")
    
    # Graphique par action
    fig = go.Figure()
    
    for action in timeline['action'].unique():
        data = timeline[timeline['action'] == action]
        fig.add_trace(go.Scatter(
            x=data['time_bucket'],
            y=data['event_count'],
            name=action,
            mode='lines+markers',
            line=dict(color='green' if action == 'ALLOW' else 'red', width=2),
            fill='tonexty' if action == 'DENY' else None
        ))
    
    fig.update_layout(
        title="Nombre d'événements par action dans le temps",
        xaxis_title="Temps",
        yaxis_title="Nombre d'événements",
        hovermode='x unified',
        height=500
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Graphique du volume de données
    st.subheader("💾 Volume de Données Transférées")
    
    timeline['total_gb'] = timeline['total_bytes'] / (1024**3)
    
    fig = px.area(
        timeline,
        x='time_bucket',
        y='total_gb',
        color='action',
        title="",
        labels={'total_gb': 'Volume (GB)', 'time_bucket': 'Temps'},
        color_discrete_map={'ALLOW': '#28a745', 'DENY': '#dc3545'}
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Graphiques par protocole
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("🔌 Répartition par Protocole")
        
        protocol_timeline = timeline.groupby(['time_bucket', 'protocol'])['event_count'].sum().reset_index()
        
        fig = px.line(
            protocol_timeline,
            x='time_bucket',
            y='event_count',
            color='protocol',
            title="",
            labels={'event_count': 'Événements', 'time_bucket': 'Temps'},
            markers=True
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    with col2:
        st.subheader("📊 Distribution des Protocoles")
        
        protocol_totals = timeline.groupby('protocol')['event_count'].sum().reset_index()
        
        fig = px.pie(
            protocol_totals,
            values='event_count',
            names='protocol',
            title="",
            hole=0.4
        )
        fig.update_layout(height=400)
        st.plotly_chart(fig, use_container_width=True)
    
    st.markdown("---")
    
    # Heatmap des événements
    st.subheader("🔥 Heatmap de l'Activité")
    
    # Préparer les données pour la heatmap
    timeline['hour'] = pd.to_datetime(timeline['time_bucket']).dt.hour
    timeline['day'] = pd.to_datetime(timeline['time_bucket']).dt.day_name()
    
    heatmap_data = timeline.pivot_table(
        values='event_count',
        index='day',
        columns='hour',
        aggfunc='sum',
        fill_value=0
    )
    
    # Réorganiser les jours de la semaine
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    heatmap_data = heatmap_data.reindex([day for day in day_order if day in heatmap_data.index])
    
    fig = px.imshow(
        heatmap_data,
        labels=dict(x="Heure", y="Jour", color="Événements"),
        x=heatmap_data.columns,
        y=heatmap_data.index,
        color_continuous_scale='Reds',
        aspect="auto"
    )
    fig.update_layout(height=400)
    st.plotly_chart(fig, use_container_width=True)
    
else:
    st.warning("⚠️ Aucune donnée temporelle disponible pour la période sélectionnée.")

# Statistiques horaires détaillées
if hourly_stats is not None and not hourly_stats.empty:
    st.markdown("---")
    st.subheader("📑 Statistiques Horaires Détaillées")
    
    # Filtres
    col1, col2 = st.columns(2)
    with col1:
        selected_firewall = st.selectbox(
            "Firewall",
            ["Tous"] + hourly_stats['firewall_id'].unique().tolist()
        )
    with col2:
        selected_protocol = st.selectbox(
            "Protocole",
            ["Tous"] + hourly_stats['protocol'].unique().tolist()
        )
    
    # Filtrer les données
    filtered_stats = hourly_stats.copy()
    if selected_firewall != "Tous":
        filtered_stats = filtered_stats[filtered_stats['firewall_id'] == selected_firewall]
    if selected_protocol != "Tous":
        filtered_stats = filtered_stats[filtered_stats['protocol'] == selected_protocol]
    
    # Afficher le tableau
    st.dataframe(
        filtered_stats.sort_values('hour_timestamp', ascending=False).style.format({
            'total_events': '{:,.0f}',
            'total_bytes': '{:,.0f}',
            'avg_duration_ms': '{:.2f}',
            'unique_src_ips': '{:,.0f}',
            'unique_dst_ips': '{:,.0f}'
        }),
        use_container_width=True,
        height=400
    )
    
    # Téléchargement
    csv = filtered_stats.to_csv(index=False)
    st.download_button(
        label="📥 Télécharger les statistiques (CSV)",
        data=csv,
        file_name=f"hourly_stats_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
        mime="text/csv"
    )

st.markdown("---")
st.caption(f"Dashboard mis à jour le {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
