# 🖥️ CLAIR OBSCUR — Frontend

Interface web de la plateforme NDR, construite avec Next.js 15, React 19 et Tailwind CSS.

## Stack

- **Next.js 15** (App Router, standalone output)
- **React 19** + TypeScript
- **Tailwind CSS 4**
- **Three.js** / React Three Fiber (shader background)
- **Lucide React** (icônes)

## Pages

| Route                  | Description                                              |
| ---------------------- | -------------------------------------------------------- |
| `/`                    | Landing page avec shader animé                           |
| `/dashboard`           | Anomaly Tickets — logs temps réel (auto-refresh 10s)     |
| `/dashboard/analytics` | Overview, timeline, breakdowns action/protocole/sévérité |
| `/dashboard/logs`      | Recherche full-text, filtres, pagination                 |
| `/dashboard/network`   | IPs suspectes + top ports                                |
| `/dashboard/chat`      | Assistant IA (OpenAI)                                    |
| `/dashboard/settings`  | Configuration                                            |

## Structure

```
src/
├── app/
│   ├── page.tsx                  # Landing page
│   ├── layout.tsx                # Root layout (fonts, globals)
│   ├── globals.css               # Thème dark, glassmorphism
│   └── dashboard/
│       ├── layout.tsx            # Sidebar + navigation
│       ├── page.tsx              # Anomaly Tickets
│       ├── analytics/page.tsx    # Analytics
│       ├── logs/page.tsx         # Log Search
│       ├── network/page.tsx      # Network Map
│       └── chat/page.tsx         # AI Assistant
├── components/
│   └── ui/ShaderBackground.tsx   # Shader Three.js
└── lib/
    └── api.ts                    # Client API typé
```

## Développement

```bash
# Installer les dépendances
npm install

# Serveur de dev
npm run dev
# → http://localhost:3000

# Build production
npm run build
```

## Variables d'Environnement

| Variable              | Défaut                  | Description          |
| --------------------- | ----------------------- | -------------------- |
| `NEXT_PUBLIC_API_URL` | `http://localhost:8000` | URL de l'API backend |

## Docker

Le frontend est conteneurisé via un Dockerfile multi-stage (deps → build → runner).

```bash
# Build et run via docker-compose (depuis la racine)
docker-compose up frontend
```
