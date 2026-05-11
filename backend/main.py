import os, json, logging, asyncio, httpx, time
from pathlib import Path
from typing import Optional
from collections import defaultdict
from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration — chargée depuis /data/config.json (volume Docker persistant)
# Fallback : variables d'environnement (dev local sans volume)
# ---------------------------------------------------------------------------
CONFIG_PATH = Path(os.getenv("CONFIG_PATH", "/data/config.json"))

DEFAULT_CFG: dict = {
    "tmdb_api_key":           "",
    "prowlarr_url":           "http://localhost:9696",
    "prowlarr_api_key":       "",
    "radarr_url":             "http://localhost:7878",
    "radarr_api_key":         "",
    "radarr_root_folder":     "/data/torrents/films",
    "radarr_quality_profile": 1,
    "sonarr_url":             "http://localhost:8989",
    "sonarr_api_key":         "",
    "sonarr_root_folder":     "/data/torrents/series",
    "sonarr_quality_profile": 1,
    "qbit_url":               "http://localhost:8080",
    "qbit_user":              "admin",
    "qbit_pass":              "",
}

def _load_config() -> dict:
    """Charge config.json si présent, sinon retourne les défauts."""
    if CONFIG_PATH.exists():
        try:
            data = json.loads(CONFIG_PATH.read_text())
            return {**DEFAULT_CFG, **data}   # merge : les clés manquantes gardent leur défaut
        except Exception as e:
            logger.warning(f"config.json illisible ({e}), utilisation des défauts")
    return dict(DEFAULT_CFG)

def _keep_secret(old_value: str, new_value: str) -> str:
    if not new_value:
        return old_value
    if "*" in new_value:
        return old_value
    return new_value

def _save_config(data: dict) -> None:
    CONFIG_PATH.parent.mkdir(parents=True, exist_ok=True)
    CONFIG_PATH.write_text(json.dumps(data, indent=2, ensure_ascii=False))

# Chargement initial — réaffecté après POST /api/config
_cfg: dict = _load_config()

def cfg(key: str):
    """Accesseur thread-safe sur _cfg (rechargé après save)."""
    return _cfg.get(key, DEFAULT_CFG.get(key, ""))

# Raccourcis lisibles utilisés dans les routes
def TMDB_API_KEY()      -> str:  return cfg("tmdb_api_key")
def PROWLARR_URL()      -> str:  return cfg("prowlarr_url")
def PROWLARR_API_KEY()  -> str:  return cfg("prowlarr_api_key")
def RADARR_URL()        -> str:  return cfg("radarr_url")
def RADARR_API_KEY()    -> str:  return cfg("radarr_api_key")
def RADARR_ROOT()       -> str:  return cfg("radarr_root_folder")
def RADARR_QUALITY()    -> int:  return int(cfg("radarr_quality_profile") or 1)
def SONARR_URL()        -> str:  return cfg("sonarr_url")
def SONARR_API_KEY()    -> str:  return cfg("sonarr_api_key")
def SONARR_ROOT()       -> str:  return cfg("sonarr_root_folder")
def SONARR_QUALITY()    -> int:  return int(cfg("sonarr_quality_profile") or 1)
def QBIT_URL()          -> str:  return cfg("qbit_url")
def QBIT_USER()         -> str:  return cfg("qbit_user")
def QBIT_PASS()         -> str:  return cfg("qbit_pass")

# ---------------------------------------------------------------------------
app = FastAPI(title="searchARR API", version="2.0.0")

ALLOWED_ORIGINS = [o.strip() for o in os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")]
app.add_middleware(
    CORSMiddleware,
    allow_origins=ALLOWED_ORIGINS,
    allow_credentials=True,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# --- Rate limiting simple en mémoire (par IP, 60 req/min) ---
_rate_store: dict[str, list[float]] = defaultdict(list)
RATE_LIMIT = int(os.getenv("RATE_LIMIT", "60"))

@app.get("/health", include_in_schema=False)
async def health():
    configured = bool(cfg("tmdb_api_key") and cfg("prowlarr_api_key"))
    return {"status": "ok", "configured": configured}

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = request.client.host if request.client else "unknown"
    now = time.time()
    window = [t for t in _rate_store[ip] if now - t < 60]
    if len(window) >= RATE_LIMIT:
        return JSONResponse(status_code=429, content={"detail": "Too many requests"})
    window.append(now)
    _rate_store[ip] = window
    return await call_next(request)

# ---------------------------------------------------------------------------
# Endpoints configuration
# ---------------------------------------------------------------------------
class ConfigModel(BaseModel):
    tmdb_api_key:           str  = ""
    prowlarr_url:           str  = "http://localhost:9696"
    prowlarr_api_key:       str  = ""
    radarr_url:             str  = "http://localhost:7878"
    radarr_api_key:         str  = ""
    radarr_root_folder:     str  = "/data/torrents/films"
    radarr_quality_profile: int  = 1
    sonarr_url:             str  = "http://localhost:8989"
    sonarr_api_key:         str  = ""
    sonarr_root_folder:     str  = "/data/torrents/series"
    sonarr_quality_profile: int  = 1
    qbit_url:               str  = "http://localhost:8080"
    qbit_user:              str  = "admin"
    qbit_pass:              str  = ""

@app.get("/api/config")
async def get_config():
    """Retourne la config courante — API keys masquées (4 derniers chars)."""
    safe = dict(_cfg)
    for key in ("tmdb_api_key", "prowlarr_api_key", "radarr_api_key", "sonarr_api_key", "qbit_pass"):
        v = safe.get(key, "")
        safe[key] = ("*" * (len(v) - 4) + v[-4:]) if len(v) > 4 else ("*" * len(v))
    safe["configured"] = bool(cfg("tmdb_api_key") and cfg("prowlarr_api_key"))
    return safe

@app.post("/api/config")
async def save_config(body: ConfigModel, request: Request):
    ip = request.client.host if request.client else "unknown"
    now = __import__("time").time()
    key = f"config:{ip}"
    window = [t for t in _rate_store[key] if now - t < 60]
    if len(window) >= 5:
        raise HTTPException(429, "Trop de tentatives de configuration (max 5/min)")
    window.append(now)
    _rate_store[key] = window
    global _cfg
    incoming = body.model_dump()
    for field in ("tmdb_api_key", "prowlarr_api_key", "radarr_api_key", "sonarr_api_key", "qbit_pass"):
        incoming[field] = _keep_secret(_cfg.get(field, ""), incoming.get(field, ""))
    _cfg = incoming
    try:
        _save_config(_cfg)
    except Exception as e:
        raise HTTPException(500, f"Impossible d'écrire config.json : {e}")
    logger.info("Configuration mise à jour et sauvegardée dans %s (clés masquées)", CONFIG_PATH)
    return {"status": "ok", "message": "Configuration sauvegardée."}

@app.get("/api/tmdb/search")
async def tmdb_search(
    query: str = Query(..., min_length=1),
    language: str = "fr-FR",
    year: Optional[int] = Query(default=None, ge=1900, le=2099),
    media_type: Optional[str] = Query(default=None, pattern="^(movie|tv|animation|documentary)$"),
    genre_id: Optional[int] = Query(default=None),
    vote_min: Optional[float] = Query(default=None, ge=0.0, le=10.0),
    sort_by: Optional[str] = Query(default=None, pattern="^(popularity|vote_average|release_date)$"),
):
    if not TMDB_API_KEY(): raise HTTPException(503, "TMDB_API_KEY manquante")

    # Pseudo media_types gérés côté Python via genre_ids
    # animation   → genre 16  (film ET série)
    # documentary → genre 99  (film ET série)
    is_animation   = media_type == "animation"
    is_documentary = media_type == "documentary"
    is_pseudo_type = is_animation or is_documentary
    tmdb_type      = None if is_pseudo_type else media_type  # movie | tv | None
    forced_genre   = 16 if is_animation else (99 if is_documentary else None)

    async with httpx.AsyncClient() as c:
        endpoint = f"search/{tmdb_type}" if tmdb_type else "search/multi"

        params: dict = {
            "api_key": TMDB_API_KEY(),
            "query": query,
            "language": language,
            "include_adult": False,
        }
        if year:
            params["primary_release_year" if tmdb_type == "movie" else "first_air_date_year"] = year
            if not tmdb_type:
                params["primary_release_year"] = year

        r = await c.get(f"https://api.themoviedb.org/3/{endpoint}", params=params, timeout=10.0)
        r.raise_for_status()
        data = r.json()

        raw = data.get("results", [])
        results = []
        for x in raw:
            mt = x.get("media_type") or tmdb_type
            if mt not in ("movie", "tv"): continue
            if not x.get("poster_path"): continue
            # Filtre pseudo-type (animation / documentaire) : genre forcé
            if forced_genre and forced_genre not in x.get("genre_ids", []): continue
            # Filtres avancés
            if genre_id is not None and genre_id not in x.get("genre_ids", []): continue
            if vote_min is not None and x.get("vote_average", 0) < vote_min: continue
            results.append({
                "id": x["id"],
                "media_type": mt,
                "title": x.get("title") or x.get("name", ""),
                "original_title": x.get("original_title") or x.get("original_name", ""),
                "overview": x.get("overview", ""),
                "poster_path": x.get("poster_path"),
                "backdrop_path": x.get("backdrop_path"),
                "release_date": x.get("release_date") or x.get("first_air_date", ""),
                "vote_average": x.get("vote_average", 0),
                "vote_count": x.get("vote_count", 0),
                "genre_ids": x.get("genre_ids", []),
            })
        # Tri optionnel
        if sort_by == "vote_average":
            results.sort(key=lambda x: x["vote_average"], reverse=True)
        elif sort_by == "release_date":
            results.sort(key=lambda x: x["release_date"] or "", reverse=True)
        # popularity = ordre naturel TMDB, pas de tri supplémentaire nécessaire
        return {"results": results, "total": len(results)}


@app.get("/api/tmdb/search/person")
async def tmdb_search_person(
    query: str = Query(..., min_length=1),
    language: str = "fr-FR",
    media_type: Optional[str] = Query(default=None, pattern="^(movie|tv)$"),
    vote_min: Optional[float] = Query(default=None, ge=0.0, le=10.0),
    sort_by: Optional[str] = Query(default=None, pattern="^(popularity|vote_average|release_date)$"),
):
    """Recherche par nom d'acteur/actrice → retourne sa filmographie TMDB."""
    if not TMDB_API_KEY(): raise HTTPException(503, "TMDB_API_KEY manquante")

    async with httpx.AsyncClient() as c:
        # 1. Trouver la personne
        r_person = await c.get(
            "https://api.themoviedb.org/3/search/person",
            params={"api_key": TMDB_API_KEY(), "query": query, "language": language},
            timeout=10.0,
        )
        r_person.raise_for_status()
        persons = r_person.json().get("results", [])
        if not persons:
            return {"results": [], "total": 0, "person": None}

        # On prend la personne la plus populaire
        person = max(persons, key=lambda p: p.get("popularity", 0))
        person_id = person["id"]

        # 2. Récupérer les crédits combinés (movies + tv)
        r_credits = await c.get(
            f"https://api.themoviedb.org/3/person/{person_id}/combined_credits",
            params={"api_key": TMDB_API_KEY(), "language": language},
            timeout=10.0,
        )
        r_credits.raise_for_status()
        credits_data = r_credits.json()

    cast = credits_data.get("cast", [])
    results = []
    seen: set[int] = set()

    for x in cast:
        mt = x.get("media_type")
        if mt not in ("movie", "tv"): continue
        if not x.get("poster_path"): continue
        if x["id"] in seen: continue
        seen.add(x["id"])
        # Filtres
        if media_type and mt != media_type: continue
        if vote_min is not None and x.get("vote_average", 0) < vote_min: continue
        results.append({
            "id":             x["id"],
            "media_type":     mt,
            "title":          x.get("title") or x.get("name", ""),
            "original_title": x.get("original_title") or x.get("original_name", ""),
            "overview":       x.get("overview", ""),
            "poster_path":    x.get("poster_path"),
            "backdrop_path":  x.get("backdrop_path"),
            "release_date":   x.get("release_date") or x.get("first_air_date", ""),
            "vote_average":   x.get("vote_average", 0),
            "vote_count":     x.get("vote_count", 0),
            "genre_ids":      x.get("genre_ids", []),
            "character":      x.get("character", ""),
        })

    if sort_by == "vote_average":
        results.sort(key=lambda x: x["vote_average"], reverse=True)
    elif sort_by == "release_date":
        results.sort(key=lambda x: x["release_date"] or "", reverse=True)
    else:
        results.sort(key=lambda x: x.get("vote_count", 0), reverse=True)

    return {
        "results": results,
        "total": len(results),
        "person": {
            "id":           person_id,
            "name":         person.get("name", ""),
            "profile_path": person.get("profile_path"),
            "known_for_department": person.get("known_for_department", ""),
        },
    }


def _normalize_tmdb(x: dict, media_type: str) -> dict:
    return {
        "id":             x["id"],
        "media_type":     media_type,
        "title":          x.get("title") or x.get("name", ""),
        "original_title": x.get("original_title") or x.get("original_name", ""),
        "overview":       x.get("overview", ""),
        "poster_path":    x.get("poster_path"),
        "backdrop_path":  x.get("backdrop_path"),
        "release_date":   x.get("release_date") or x.get("first_air_date", ""),
        "vote_average":   x.get("vote_average", 0),
        "vote_count":     x.get("vote_count", 0),
        "genre_ids":      x.get("genre_ids", []),
    }

@app.get("/api/tmdb/discover")
async def tmdb_discover(
    genre_id: int = Query(...),
    language: str = "fr-FR",
    sort_by: str = "popularity.desc",
    media_type: Optional[str] = Query(default=None, pattern="^(movie|tv)$"),
    row_type: Optional[str] = Query(default=None, pattern="^(trending|upcoming)$"),
):
    """
    Discover films/séries par genre.
    - row_type=trending  : trending/movie/week ou trending/tv/week filtré par genre
    - row_type=upcoming  : movie/upcoming ou tv/on_the_air filtré par genre
    - row_type=None      : /discover/{mt} trié par popularité (documentaires)
    """
    if not TMDB_API_KEY(): raise HTTPException(503, "TMDB_API_KEY manquante")
    if not media_type:
        raise HTTPException(400, "media_type requis pour row_type trending/upcoming")

    async with httpx.AsyncClient() as c:
        if row_type == "trending":
            r = await c.get(
                f"https://api.themoviedb.org/3/trending/{media_type}/week",
                params={"api_key": TMDB_API_KEY(), "language": language},
                timeout=10.0,
            )
            r.raise_for_status()
            raw = [
                x for x in r.json().get("results", [])
                if x.get("poster_path") and genre_id in x.get("genre_ids", [])
            ]
            results = [_normalize_tmdb(x, media_type) for x in raw]

        elif row_type == "upcoming":
            endpoint = "movie/upcoming" if media_type == "movie" else "tv/on_the_air"
            params_up = {"api_key": TMDB_API_KEY(), "language": language}
            if media_type == "movie":
                params_up["region"] = "FR"
            r = await c.get(
                f"https://api.themoviedb.org/3/{endpoint}",
                params=params_up, timeout=10.0,
            )
            r.raise_for_status()
            raw = [
                x for x in r.json().get("results", [])
                if x.get("poster_path") and genre_id in x.get("genre_ids", [])
            ]
            results = [_normalize_tmdb(x, media_type) for x in raw]

            # Si upcoming filtré vide, fallback sur discover
            if not results:
                params_disc = {
                    "api_key": TMDB_API_KEY(), "language": language,
                    "with_genres": genre_id, "sort_by": sort_by,
                    "include_adult": False, "page": 1,
                }
                r2 = await c.get(
                    f"https://api.themoviedb.org/3/discover/{media_type}",
                    params=params_disc, timeout=10.0,
                )
                r2.raise_for_status()
                results = [
                    _normalize_tmdb(x, media_type)
                    for x in r2.json().get("results", [])
                    if x.get("poster_path")
                ]

        else:
            # Pas de row_type — discover pur (documentaires)
            params_base = {
                "api_key": TMDB_API_KEY(), "language": language,
                "with_genres": genre_id, "sort_by": sort_by,
                "include_adult": False, "page": 1,
            }
            types_to_fetch = ([media_type] if media_type else ["movie", "tv"])
            reqs = await asyncio.gather(*[
                c.get(f"https://api.themoviedb.org/3/discover/{mt}",
                      params=params_base, timeout=10.0)
                for mt in types_to_fetch
            ])
            results = []
            for mt, r in zip(types_to_fetch, reqs):
                r.raise_for_status()
                for x in r.json().get("results", []):
                    if not x.get("poster_path"): continue
                    results.append(_normalize_tmdb(x, mt))
            results.sort(key=lambda x: x.get("vote_count", 0), reverse=True)

    return {"results": results, "total": len(results)}


@app.get("/api/tmdb/home-rows")
async def tmdb_home_rows(language: str = "fr-FR"):
    """Retourne 4 rows séparées : films tendance, séries tendance, films à venir, séries à venir."""
    if not TMDB_API_KEY(): raise HTTPException(503, "TMDB_API_KEY manquante")
    async with httpx.AsyncClient() as c:
        reqs = await asyncio.gather(
            c.get("https://api.themoviedb.org/3/trending/movie/week",
                  params={"api_key": TMDB_API_KEY(), "language": language}, timeout=10.0),
            c.get("https://api.themoviedb.org/3/trending/tv/week",
                  params={"api_key": TMDB_API_KEY(), "language": language}, timeout=10.0),
            c.get("https://api.themoviedb.org/3/movie/upcoming",
                  params={"api_key": TMDB_API_KEY(), "language": language, "region": "FR"}, timeout=10.0),
            c.get("https://api.themoviedb.org/3/tv/on_the_air",
                  params={"api_key": TMDB_API_KEY(), "language": language}, timeout=10.0),
        )
    for r in reqs:
        r.raise_for_status()

    def extract(r, mt):
        return [
            _normalize_tmdb(x, mt)
            for x in r.json().get("results", [])
            if x.get("poster_path")
        ]

    return {
        "trending_movies": extract(reqs[0], "movie"),
        "trending_tv":     extract(reqs[1], "tv"),
        "upcoming_movies": extract(reqs[2], "movie"),
        "upcoming_tv":     extract(reqs[3], "tv"),
    }

@app.get("/api/services/status")
async def services_status():
    """Ping rapide de chaque service — retourne online/offline + latence ms."""
    async def ping(name: str, url: str, headers: dict = {}) -> dict:
        try:
            t0 = asyncio.get_event_loop().time()
            async with httpx.AsyncClient() as c:
                r = await c.get(url, headers=headers, timeout=3.0)
            ms = round((asyncio.get_event_loop().time() - t0) * 1000)
            return {"name": name, "online": r.status_code < 500, "ms": ms}
        except Exception:
            return {"name": name, "online": False, "ms": None}

    results = await asyncio.gather(
        ping("Radarr",   f"{RADARR_URL()}/api/v3/system/status",   {"X-Api-Key": RADARR_API_KEY()}),
        ping("Sonarr",   f"{SONARR_URL()}/api/v3/system/status",   {"X-Api-Key": SONARR_API_KEY()}),
        ping("Prowlarr", f"{PROWLARR_URL()}/api/v1/system/status", {"X-Api-Key": PROWLARR_API_KEY()}),
        ping("qBit",     f"{QBIT_URL()}/api/v2/app/version",       {}),
    )
    return {"services": list(results)}

@app.get("/api/radarr/profiles")
async def radarr_profiles():
    if not RADARR_API_KEY(): raise HTTPException(503, "RADARR_API_KEY manquante")
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{RADARR_URL()}/api/v3/qualityprofile",
                        headers={"X-Api-Key": RADARR_API_KEY()}, timeout=8.0)
        r.raise_for_status()
        return [{"id": p["id"], "name": p["name"]} for p in r.json()]

@app.get("/api/sonarr/profiles")
async def sonarr_profiles():
    if not SONARR_API_KEY(): raise HTTPException(503, "SONARR_API_KEY manquante")
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{SONARR_URL()}/api/v3/qualityprofile",
                        headers={"X-Api-Key": SONARR_API_KEY()}, timeout=8.0)
        r.raise_for_status()
        return [{"id": p["id"], "name": p["name"]} for p in r.json()]

@app.get("/api/tmdb/details/{media_type}/{tmdb_id}")
async def tmdb_details(media_type: str, tmdb_id: int, language: str = "fr-FR"):
    if media_type not in ("movie", "tv"): raise HTTPException(400, "media_type invalide")
    if not TMDB_API_KEY(): raise HTTPException(503, "TMDB_API_KEY manquante")
    async with httpx.AsyncClient() as c:
        r, providers = await asyncio.gather(
            c.get(
                f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}",
                params={
                    "api_key": TMDB_API_KEY(),
                    "language": language,
                    "append_to_response": "credits,external_ids",
                },
                timeout=10.0,
            ),
            c.get(
                f"https://api.themoviedb.org/3/{media_type}/{tmdb_id}/watch/providers",
                params={"api_key": TMDB_API_KEY()},
                timeout=10.0,
            ),
        )
    r.raise_for_status()
    data = r.json()

    # Providers FR uniquement
    prov_fr: dict = {}
    if providers.status_code == 200:
        prov_fr = providers.json().get("results", {}).get("FR", {})

    # Casting : top 12 acteurs + réalisateur(s)
    credits = data.get("credits", {})
    cast = [
        {"id": p["id"], "name": p["name"], "character": p.get("character", ""),
         "profile_path": p.get("profile_path")}
        for p in credits.get("cast", [])[:12]
    ]
    crew = credits.get("crew", [])
    directors = [
        {"id": p["id"], "name": p["name"], "job": p["job"]}
        for p in crew if p.get("job") in ("Director", "Creator")
    ][:3]

    # Genres
    genres = [g["name"] for g in data.get("genres", [])]

    # Durée
    runtime = data.get("runtime") or (data.get("episode_run_time") or [None])[0]

    # Date complète
    release_date = data.get("release_date") or data.get("first_air_date", "")

    data["_enriched"] = {
        "cast":         cast,
        "directors":    directors,
        "genres":       genres,
        "runtime":      runtime,         # minutes
        "release_date": release_date,
        "providers_fr": {
            "flatrate": prov_fr.get("flatrate", []),  # SVOD (Netflix, Disney+…)
            "rent":     prov_fr.get("rent", []),       # Location
            "buy":      prov_fr.get("buy", []),        # Achat
            "link":     prov_fr.get("link", ""),       # Lien JustWatch
        },
    }
    return data

@app.get("/api/tmdb/genres")
async def tmdb_genres(language: str = "fr-FR"):
    """Retourne la liste des genres TMDB (films + séries fusionnés, dédoublonnés)."""
    if not TMDB_API_KEY(): raise HTTPException(503, "TMDB_API_KEY manquante")
    async with httpx.AsyncClient() as c:
        movies_r, tv_r = await asyncio.gather(
            c.get("https://api.themoviedb.org/3/genre/movie/list",
                  params={"api_key": TMDB_API_KEY(), "language": language}, timeout=8.0),
            c.get("https://api.themoviedb.org/3/genre/tv/list",
                  params={"api_key": TMDB_API_KEY(), "language": language}, timeout=8.0),
        )
    movies_r.raise_for_status()
    tv_r.raise_for_status()
    seen: set[int] = set()
    genres = []
    for g in movies_r.json().get("genres", []) + tv_r.json().get("genres", []):
        if g["id"] not in seen:
            seen.add(g["id"])
            genres.append({"id": g["id"], "name": g["name"]})
    genres.sort(key=lambda x: x["name"])
    return {"genres": genres}


@app.get("/api/releases")
async def search_releases(query: str = Query(..., min_length=1)):
    if not PROWLARR_API_KEY(): raise HTTPException(503, "PROWLARR_API_KEY manquante")
    async with httpx.AsyncClient() as c:
        r = await c.get(f"{PROWLARR_URL()}/api/v1/search", params={"query":query,"type":"search"}, headers={"X-Api-Key":PROWLARR_API_KEY()}, timeout=20.0)
        r.raise_for_status()
        data = r.json()
        releases = data if isinstance(data, list) else data.get("results", [])
        return {"results": releases, "count": len(releases)}

class DownloadRequest(BaseModel):
    guid: str
    category: str = "manual"

@app.post("/api/download")
async def download(req: DownloadRequest):
    async with httpx.AsyncClient(verify=False) as c:
        auth = await c.post(f"{QBIT_URL()}/api/v2/auth/login", data={"username":QBIT_USER(),"password":QBIT_PASS()}, timeout=10.0)
        if auth.text != "Ok.": raise HTTPException(401, "Auth qBittorrent echouee")
        if req.guid.startswith("magnet:"):
            res = await c.post(f"{QBIT_URL()}/api/v2/torrents/add", data={"urls":req.guid,"category":req.category}, cookies=auth.cookies)
        else:
            t = await c.get(req.guid, follow_redirects=True, timeout=15.0)
            t.raise_for_status()
            res = await c.post(f"{QBIT_URL()}/api/v2/torrents/add", data={"category":req.category}, files={"torrents":("dl.torrent",t.content,"application/x-bittorrent")}, cookies=auth.cookies)
        res.raise_for_status()
        return {"status": "success"}

@app.get("/api/monitor/status")
async def monitor_status(tmdb_id: int, media_type: str):
    """Vérifie si un media est déjà dans Radarr ou Sonarr."""
    if media_type not in ("movie", "tv"): raise HTTPException(400, "media_type invalide")
    async with httpx.AsyncClient() as c:
        if media_type == "movie":
            if not RADARR_API_KEY(): return {"monitored": False, "status": None}
            r = await c.get(f"{RADARR_URL()}/api/v3/movie",
                            params={"tmdbId": tmdb_id},
                            headers={"X-Api-Key": RADARR_API_KEY()}, timeout=8.0)
            r.raise_for_status()
            movies = r.json()
            if not movies:
                return {"monitored": False, "status": None}
            m = movies[0]
            return {
                "monitored":     True,
                "status":        m.get("status", "unknown"),      # announced/inCinemas/released
                "hasFile":       m.get("hasFile", False),
                "title":         m.get("title", ""),
                "qualityProfile": m.get("qualityProfileId"),
                "monitored_flag": m.get("monitored", True),
            }
        else:
            if not SONARR_API_KEY(): return {"monitored": False, "status": None}
            r = await c.get(f"{SONARR_URL()}/api/v3/series/lookup",
                            params={"term": f"tmdb:{tmdb_id}"},
                            headers={"X-Api-Key": SONARR_API_KEY()}, timeout=8.0)
            r.raise_for_status()
            results = r.json()
            if not results: return {"monitored": False, "status": None}
            # Le lookup retourne des résultats même non ajoutés — on vérifie avec /api/v3/series
            tvdb_id = results[0].get("tvdbId")
            if not tvdb_id: return {"monitored": False, "status": None}
            s_all = await c.get(f"{SONARR_URL()}/api/v3/series",
                                headers={"X-Api-Key": SONARR_API_KEY()}, timeout=8.0)
            s_all.raise_for_status()
            match = next((s for s in s_all.json() if s.get("tvdbId") == tvdb_id), None)
            if not match:
                return {"monitored": False, "status": None}
            return {
                "monitored":      True,
                "status":         match.get("status", "unknown"),  # continuing/ended
                "hasFile":        match.get("statistics", {}).get("episodeFileCount", 0) > 0,
                "title":          match.get("title", ""),
                "qualityProfile": match.get("qualityProfileId"),
                "monitored_flag": match.get("monitored", True),
            }

class MonitorRequest(BaseModel):
    tmdb_id: int
    title: str
    media_type: str
    quality_profile_id: Optional[int] = None  # None = fallback var d'env

@app.post("/api/monitor")
async def monitor(req: MonitorRequest):
    if req.media_type not in ("movie","tv"): raise HTTPException(400, "media_type invalide")
    async with httpx.AsyncClient() as c:
        if req.media_type == "movie":
            qp = req.quality_profile_id or RADARR_QUALITY()
            lookup = await c.get(f"{RADARR_URL()}/api/v3/movie/lookup",
                                 params={"term": f"tmdb:{req.tmdb_id}"},
                                 headers={"X-Api-Key": RADARR_API_KEY()}, timeout=10.0)
            lookup.raise_for_status()
            ld = lookup.json()
            if not ld: raise HTTPException(404, "Film introuvable dans Radarr")
            m = ld[0]
            payload = {
                "title":           m["title"],
                "tmdbId":          m["tmdbId"],
                "year":            m.get("year", 0),
                "qualityProfileId": qp,
                "rootFolderPath":  RADARR_ROOT(),
                "monitored":       True,
                "addOptions":      {"searchForMovie": True},
            }
            res = await c.post(f"{RADARR_URL()}/api/v3/movie", json=payload, headers={"X-Api-Key":RADARR_API_KEY()}, timeout=10.0)
        else:
            qp = req.quality_profile_id or SONARR_QUALITY()
            lookup = await c.get(f"{SONARR_URL()}/api/v3/series/lookup", params={"term":f"tmdb:{req.tmdb_id}"}, headers={"X-Api-Key":SONARR_API_KEY()}, timeout=10.0)
            lookup.raise_for_status()
            sd = lookup.json()
            if not sd: raise HTTPException(404, "Serie introuvable dans Sonarr")
            s = sd[0]
            payload = {"title":s["title"],"tvdbId":s["tvdbId"],"qualityProfileId":qp,"rootFolderPath":SONARR_ROOT(),"monitored":True,"addOptions":{"searchForMissingEpisodes":True}}
            res = await c.post(f"{SONARR_URL()}/api/v3/series", json=payload, headers={"X-Api-Key":SONARR_API_KEY()}, timeout=10.0)
        if res.status_code == 400:
            body = res.text.lower()
            logger.warning("Radarr/Sonarr 400 — already exists check")
            if "already exists" in body:
                return {"status":"exists","message":"Ce media est deja surveille."}
            raise HTTPException(400, f"Erreur arr: {res.text}")
        res.raise_for_status()
        return {"status":"success","message":f"'{req.title}' ajoute avec le profil #{qp}."}
