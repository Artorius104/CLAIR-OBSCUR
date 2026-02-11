FROM python:3.10-slim

WORKDIR /app

# Installation des dépendances
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copier les fichiers de l'application
COPY src/ ./src/

# Exposer le port Streamlit
EXPOSE 8501

# Lancer l'application Streamlit
CMD ["streamlit", "run", "src/FirewallDashboard.py", "--server.port=8501", "--server.address=0.0.0.0"]
