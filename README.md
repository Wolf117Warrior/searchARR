# SearchARR

> Interface web unifiée pour rechercher, surveiller et télécharger des films et séries via **TMDB**, **Radarr**, **Sonarr**, **Prowlarr** et **qBittorrent**.

![Version](https://img.shields.io/badge/version-1.0.0-blue)
![Docker](https://img.shields.io/badge/docker-hub-2496ED?logo=docker&logoColor=white)
![License](https://img.shields.io/badge/license-MIT-green)

---

## Fonctionnalités

- 🔍 **Recherche TMDB** — films, séries, animations, documentaires, par acteur
- 🎬 **Page détail enrichie** — casting, plateformes SVOD, genres, durée, lien TMDB
- 📡 **Surveillance** — ajout direct dans Radarr / Sonarr avec choix du profil qualité
- 🔎 **Recherche avancée** — filtres par genre, note minimale, année, tri
- 📥 **Releases Prowlarr** — filtres résolution, source, codec, HDR, audio, langue, indexeur
- ⚙️ **Page de configuration UI** — aucun fichier `.env` à éditer, tout se configure via l'interface
- 🏠 **Homepage Netflix-style** — Tendances / À venir (Films, Séries, Animations, Documentaires)
- 🔗 **Statut des services** en temps réel dans le header

---
/!\ C'est du Vibe-coding /!\ 
La version anglaise arrive prochainement.
---

## Prérequis

- Docker + Docker Compose V2
- Instances fonctionnelles de : **Radarr**, **Sonarr**, **Prowlarr**, **qBittorrent**
- Clé API **TMDB** (gratuite) : https://www.themoviedb.org/settings/api

---

## Démarrage rapide

### 1. Créer le `docker-compose.yml`

```yaml
services:

  searcharr-backend:
    image: wolf117warrior/searcharr-backend:latest
    container_name: searcharr-backend
    restart: unless-stopped
    expose:
      - "8000"
    networks:
      - searcharr
    volumes:
      - searcharr_config:/data
    healthcheck:
      test: ["CMD", "curl", "-sf", "http://localhost:8000/health"]
      interval: 30s
      timeout: 5s
      retries: 3
      start_period: 10s

  searcharr-frontend:
    image: wolf117warrior/searcharr-frontend:latest
    container_name: searcharr-frontend
    restart: unless-stopped
    ports:
      - "3120:80"        # Changer 3120 par le port souhaité
    networks:
      - searcharr
    depends_on:
      searcharr-backend:
        condition: service_healthy
    healthcheck:
      test: ["CMD", "wget", "-qO-", "http://localhost/health.txt"]
      interval: 30s
      timeout: 3s
      retries: 3
      start_period: 5s

networks:
  searcharr:
    driver: bridge

volumes:
  searcharr_config:
    driver: local
```

### 2. Lancer

```bash
docker compose up -d
```

### 3. Configurer

Ouvrir **http://localhost:3120** → cliquer sur ⚙️ **Configuration** dans le header.

Renseigner :

| Champ | Description | Exemple |
|---|---|---|
| TMDB API Key | Clé API The Movie DB | `abc123...` |
| Prowlarr URL | URL de ton instance | `http://192.168.1.10:9696` |
| Prowlarr API Key | Clé API Prowlarr | `abc123...` |
| Radarr URL | URL de ton instance | `http://192.168.1.10:7878` |
| Radarr API Key | Clé API Radarr | `abc123...` |
| Radarr Root Folder | Dossier racine films | `/data/torrents/films` |
| Radarr Quality Profile | ID du profil qualité | `1` |
| Sonarr URL | URL de ton instance | `http://192.168.1.10:8989` |
| Sonarr API Key | Clé API Sonarr | `abc123...` |
| Sonarr Root Folder | Dossier racine séries | `/data/torrents/series` |
| Sonarr Quality Profile | ID du profil qualité | `1` |
| qBittorrent URL | URL de ton instance | `http://192.168.1.10:8080` |
| qBittorrent User | Identifiant | `admin` |
| qBittorrent Password | Mot de passe | `...` |

> La configuration est **persistante** via un volume Docker — elle survit aux mises à jour et rebuilds.

---

## Mise à jour

```bash
docker compose pull
docker compose up -d
```

La configuration est préservée (volume `searcharr_config`).

---

## Stack technique

| Composant | Technologie |
|---|---|
| Backend | FastAPI (Python 3.12-slim) |
| Frontend | SvelteKit + TailwindCSS (adapter-static) |
| Serveur | nginx 1.27 Alpine |
| Config persistante | Volume Docker (`/data/config.json`) |

---

## Sécurité

- Backend non exposé directement (proxy nginx uniquement)
- User non-root `appuser:1000` dans le container backend
- Headers HTTP : `Content-Security-Policy`, `X-Frame-Options`, `X-Content-Type-Options`, `Referrer-Policy`, `Permissions-Policy`
- Aucune donnée personnelle dans l'image — configuration via volume
- Rate-limiting : 60 req/min global, 5 req/min sur l'endpoint de configuration

---

## Variables d'environnement optionnelles

Ces variables peuvent être passées au service backend dans le `docker-compose.yml` :

| Variable | Défaut | Description |
|---|---|---|
| `ALLOWED_ORIGINS` | `http://localhost:3120` | Origines CORS autorisées |
| `RATE_LIMIT` | `60` | Requêtes max/min par IP |
| `CONFIG_PATH` | `/data/config.json` | Chemin du fichier de config |

---

## Ports

| Service | Port interne | Port exposé (défaut) |
|---|---|---|
| Frontend (nginx) | 80 | 3120 |
| Backend (FastAPI) | 8000 | non exposé |

---

## Auteur

**Wolf117Warrior** — https://github.com/Wolf117Warrior
**Claud Sonnet 4.6**
---

## License

MIT
