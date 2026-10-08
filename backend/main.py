import os, json, logging, asyncio, httpx, time, uuid
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
    "jellyfin_url":           "http://localhost:8096",
    "jellyfin_api_key":       "",
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
def JELLYFIN_URL()      -> str:  return cfg("jellyfin_url")
def JELLYFIN_API_KEY()  -> str:  return cfg("jellyfin_api_key")
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
    checks = {
        "tmdb": {
            "configured": bool(cfg("tmdb_api_key")),
            "base_url": "https://api.themoviedb.org/3",
        },
        "prowlarr": {
            "configured": bool(cfg("prowlarr_api_key") and cfg("prowlarr_url")),
            "url": PROWLARR_URL(),
        },
        "radarr": {
            "configured": bool(cfg("radarr_api_key") and cfg("radarr_url")),
            "url": RADARR_URL(),
            "root_folder": bool(cfg("radarr_root_folder")),
        },
        "sonarr": {
            "configured": bool(cfg("sonarr_api_key") and cfg("sonarr_url")),
            "url": SONARR_URL(),
            "root_folder": bool(cfg("sonarr_root_folder")),
        },
        "jellyfin": {
            "configured": bool(cfg("jellyfin_api_key") and cfg("jellyfin_url")),
            "url": JELLYFIN_URL(),
        },
        "qbit": {
            "configured": bool(cfg("qbit_url") and cfg("qbit_user") and cfg("qbit_pass")),
            "url": QBIT_URL(),
            "username": QBIT_USER(),
        },
    }

    configured = checks["tmdb"]["configured"] and checks["prowlarr"]["configured"]
    all_configured = all(
        check["configured"]
        for check in checks.values()
    )

    if not configured:
        status = "error"
    elif all_configured:
        status = "ok"
    else:
        status = "degraded"

    return {
        "status": status,
        "app": "searchARR API",
        "version": app.version,
        "configured": configured,
        "timestamp": round(time.time()),
        "checks": checks,
    }

# --- Observabilité : métriques simples en mémoire ---
_metrics = {
    "started_at": time.time(),
    "requests_total": 0,
    "responses_total": 0,
    "errors_total": 0,
    "duration_ms_total": 0.0,
    "status_codes": defaultdict(int),
    "paths": defaultdict(int),
}

@app.get("/metrics", include_in_schema=False)
async def metrics():
    requests_total = _metrics["requests_total"]
    responses_total = _metrics["responses_total"]
    duration_total = _metrics["duration_ms_total"]
    return {
        "uptime_seconds": round(time.time() - _metrics["started_at"], 2),
        "requests_total": requests_total,
        "responses_total": responses_total,
        "errors_total": _metrics["errors_total"],
        "average_duration_ms": round(duration_total / responses_total, 2) if responses_total else 0,
        "status_codes": dict(_metrics["status_codes"]),
        "top_paths": dict(sorted(_metrics["paths"].items(), key=lambda item: item[1], reverse=True)[:20]),
    }

@app.middleware("http")
async def request_logging_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
    request.state.request_id = request_id
    start = time.time()
    _metrics["requests_total"] += 1

    try:
        response = await call_next(request)
    except Exception:
        duration_ms = round((time.time() - start) * 1000, 2)
        _metrics["errors_total"] += 1
        _metrics["status_codes"][500] += 1
        _metrics["paths"][request.url.path] += 1
        _metrics["duration_ms_total"] += duration_ms
        logger.exception(
            "request_completed method=%s path=%s status=%s duration_ms=%s client=%s request_id=%s",
            request.method, request.url.path, 500, duration_ms,
            request.client.host if request.client else "unknown", request_id,
        )
        raise

    duration_ms = round((time.time() - start) * 1000, 2)
    _metrics["responses_total"] += 1
    _metrics["duration_ms_total"] += duration_ms
    _metrics["status_codes"][response.status_code] += 1
    _metrics["paths"][request.url.path] += 1
    if response.status_code >= 500:
        _metrics["errors_total"] += 1
    response.headers["X-Request-ID"] = request_id
    logger.info(
        "request_completed method=%s path=%s status=%s duration_ms=%s client=%s request_id=%s",
        request.method, request.url.path, response.status_code, duration_ms,
        request.client.host if request.client else "unknown", request_id,
    )
    return response

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
    jellyfin_url:           str  = "http://localhost:8096"
    jellyfin_api_key:       str  = ""
    qbit_url:               str  = "http://localhost:8080"
    qbit_user:              str  = "admin"
    qbit_pass:              str  = ""

@app.get("/api/config")
async def get_config():
    """Retourne la config courante — API keys masquées (4 derniers chars)."""
    safe = dict(_cfg)
    for key in ("tmdb_api_key", "prowlarr_api_key", "radarr_api_key", "sonarr_api_key", "jellyfin_api_key", "qbit_pass"):
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
    for field in ("tmdb_api_key", "prowlarr_api_key", "radarr_api_key", "sonarr_api_key", "jellyfin_api_key", "qbit_pass"):
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
            return {
                "name": name,
                "online": r.status_code < 500,
                "ms": ms,
                "url": (
                    RADARR_URL() if name == "Radarr" else
                    SONARR_URL() if name == "Sonarr" else
                    PROWLARR_URL() if name == "Prowlarr" else
                    QBIT_URL() if name == "qBit" else
                    JELLYFIN_URL().rstrip("/") if name == "Jellyfin" else None
                ),
            }
        except Exception:
            return {
                "name": name,
                "online": False,
                "ms": None,
                "url": (
                    RADARR_URL() if name == "Radarr" else
                    SONARR_URL() if name == "Sonarr" else
                    PROWLARR_URL() if name == "Prowlarr" else
                    QBIT_URL() if name == "qBit" else
                    JELLYFIN_URL().rstrip("/") if name == "Jellyfin" else None
                ),
            }

    results = await asyncio.gather(
        ping("Radarr",   f"{RADARR_URL()}/api/v3/system/status",   {"X-Api-Key": RADARR_API_KEY()}),
        ping("Sonarr",   f"{SONARR_URL()}/api/v3/system/status",   {"X-Api-Key": SONARR_API_KEY()}),
        ping("Prowlarr", f"{PROWLARR_URL()}/api/v1/system/status", {"X-Api-Key": PROWLARR_API_KEY()}),
        ping("qBit",     f"{QBIT_URL()}/api/v2/app/version",       {}),
        ping("Jellyfin", f"{JELLYFIN_URL().rstrip('/')}/System/Info", {"X-Emby-Token": JELLYFIN_API_KEY()}),
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


def _jf_headers() -> dict:
    api_key = JELLYFIN_API_KEY().strip()
    return {
        "X-Emby-Token": api_key,
        "Authorization": f'MediaBrowser Token="{api_key}"',
        "Accept": "application/json",
    }


def _jf_norm(text: str) -> str:
    return "".join(ch.lower() for ch in (text or "") if ch.isalnum())


def _jf_pick_version_labels(sources: list[dict]) -> list[str]:
    labels: list[str] = []
    for src in sources or []:
        width = int(src.get("Width") or 0)
        height = int(src.get("Height") or 0)
        video_codec = (src.get("VideoCodec") or "").lower()
        container = (src.get("Container") or "").lower()
        name = (src.get("Name") or "").lower()
        path = (src.get("Path") or "").lower()

        stream_bits = []
        for stream in (src.get("MediaStreams") or []):
            title = (stream.get("DisplayTitle") or "").lower()
            codec = (stream.get("Codec") or "").lower()
            stream_type = str(stream.get("Type") or "").lower()
            if stream_type == "videostream":
                stream_bits.extend([title, codec])
                width = width or int(stream.get("Width") or 0)
                height = height or int(stream.get("Height") or 0)

        candidates = f" {video_codec} {container} {name} {path} {' '.join(stream_bits)} ".lower()

        if width >= 3800 or height >= 2100 or any(x in candidates for x in ["2160p", "uhd", "4k"]):
            labels.append("4K")
        elif width >= 1900 or height >= 1000 or any(x in candidates for x in ["1080p", "fhd"]):
            labels.append("FHD")
        elif width >= 1200 or height >= 700 or any(x in candidates for x in ["720p", "hd"]):
            labels.append("HD")

        if any(x in candidates for x in ["hevc", "x265", "h265"]):
            labels.append("x265")
        elif any(x in candidates for x in ["avc", "x264", "h264"]):
            labels.append("x264")

        if any(x in candidates for x in ["dolby vision", "dovi", " dv "]):
            labels.append("DV")
        elif "hdr" in candidates:
            labels.append("HDR")

        if "remux" in candidates:
            labels.append("Remux")

    out: list[str] = []
    seen = set()
    for label in labels:
        if label not in seen:
            seen.add(label)
            out.append(label)
    return out


@app.get("/api/jellyfin/status")
async def jellyfin_status(
    tmdb_id: int,
    media_type: str,
    title: str = "",
    year: Optional[int] = None,
):
    if media_type not in ("movie", "tv"):
        raise HTTPException(400, "media_type invalide")

    if not JELLYFIN_API_KEY():
        return {
            "present": False,
            "matched_by": None,
            "jellyfin_id": None,
            "title": None,
            "year": None,
            "versions": [],
            "path": None,
            "error": "missing_api_key",
        }

    base = JELLYFIN_URL().rstrip("/")

    try:
        async with httpx.AsyncClient() as c:
            r = await c.get(
                f"{base}/Items",
                params={
                    "Recursive": "true",
                    "IncludeItemTypes": "Movie,Series",
                    "Fields": "ProviderIds,Path,ProductionYear",
                    "SearchTerm": title or "",
                },
                headers=_jf_headers(),
                timeout=10.0,
            )

        if r.status_code in (401, 403):
            return {
                "present": False,
                "matched_by": None,
                "jellyfin_id": None,
                "title": None,
                "year": None,
                "versions": [],
                "path": None,
                "error": "auth_failed",
            }

        r.raise_for_status()
        items = r.json().get("Items", [])
    except httpx.HTTPError as e:
        logger.warning(f"Jellyfin lookup failed: {e}")
        return {
            "present": False,
            "matched_by": None,
            "jellyfin_id": None,
            "title": None,
            "year": None,
            "versions": [],
            "path": None,
            "error": "request_failed",
        }

    tmdb_str = str(tmdb_id)
    wanted_type = "Movie" if media_type == "movie" else "Series"

    exact = []
    fallback = []

    for item in items:
        if item.get("Type") != wanted_type:
            continue

        provider_ids = item.get("ProviderIds") or {}
        item_tmdb = str(provider_ids.get("Tmdb") or provider_ids.get("TMDB") or "").strip()

        if item_tmdb and item_tmdb == tmdb_str:
            exact.append(item)
            continue

        item_title = item.get("Name") or ""
        item_year = item.get("ProductionYear")
        if _jf_norm(item_title) == _jf_norm(title) and (year is None or item_year == year):
            fallback.append(item)

    picked = exact[0] if exact else (fallback[0] if fallback else None)

    if not picked:
        return {
            "present": False,
            "matched_by": None,
            "jellyfin_id": None,
            "title": None,
            "year": None,
            "versions": [],
            "path": None,
            "error": None,
        }

    versions: list[str] = []
    try:
        async with httpx.AsyncClient() as c:
            item_r = await c.get(
                f"{base}/Items/{picked.get('Id')}",
                params={"Fields": "MediaSources,MediaStreams,Path,ProductionYear"},
                headers=_jf_headers(),
                timeout=10.0,
            )
        if item_r.status_code < 400:
            item_data = item_r.json()
            media_sources = item_data.get("MediaSources") or picked.get("MediaSources") or []
            versions = _jf_pick_version_labels(media_sources)
    except httpx.HTTPError as e:
        logger.warning(f"Jellyfin item details lookup failed: {e}")

    return {
        "present": True,
        "matched_by": "tmdb" if exact else "title_year",
        "jellyfin_id": picked.get("Id"),
        "title": picked.get("Name"),
        "year": picked.get("ProductionYear"),
        "versions": versions,
        "path": picked.get("Path"),
        "web_url": f"{base}/web/#/details?id={picked.get('Id')}",
        "error": None,
    }

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
async def search_releases(
    query: str = Query(..., min_length=1),
    tmdb_id: Optional[int] = Query(default=None),
    media_type: Optional[str] = Query(default=None, pattern="^(movie|tv)$"),
    title: Optional[str] = Query(default=None),
    year: Optional[int] = Query(default=None),
):
    if not PROWLARR_API_KEY(): raise HTTPException(503, "PROWLARR_API_KEY manquante")

    def _norm_release_text(value: str) -> str:
        return " ".join((value or "").lower().replace("&", " ").replace("'", " ").split())

    def _tokenize_release_text(value: str) -> list[str]:
        text = _norm_release_text(value)
        parts = []
        for chunk in text.replace('.', ' ').replace('-', ' ').replace('_', ' ').replace(':', ' ').split():
            if chunk:
                parts.append(chunk)
        return parts

    def _extract_years(value: str) -> list[int]:
        import re
        years = []
        for match in re.findall(r"\b(19\d{2}|20\d{2}|21\d{2})\b", value or ""):
            try:
                years.append(int(match))
            except ValueError:
                pass
        return years

    def _extract_season_episode(value: str) -> tuple[bool, bool]:
        import re
        upper = (value or "").upper()
        has_episode = bool(re.search(r"\bS\d{1,2}E\d{1,2}\b", upper))
        has_season = bool(re.search(r"\bS\d{1,2}\b", upper)) or "SAISON" in upper or "SEASON" in upper
        return has_season, has_episode

    def _looks_like_non_video_release(rel: dict) -> bool:
        import re

        title_upper = (rel.get("title") or "").upper()

        category_labels = []
        def _walk_categories(items):
            for cat in items or []:
                if isinstance(cat, dict):
                    category_labels.extend([
                        str(cat.get("name") or ""),
                        str(cat.get("label") or ""),
                    ])
                    _walk_categories(cat.get("subCategories") or [])
                else:
                    category_labels.append(str(cat))

        _walk_categories(rel.get("categories") or [])
        category_blob = " ".join(category_labels).upper()
        combined = f"{title_upper} {category_blob}"

        blocked_category_patterns = [
            r"\bBOOKS?\b", r"\bCOMICS?\b", r"\bEBOOK\b", r"\bAUDIOBOOK\b",
            r"\bMUSIC\b", r"\bAUDIO\b", r"\bLOSSLESS\b",
            r"\bXXX\b",
            r"\bPC\b", r"\bCONSOLE\b", r"\bGAMES?\b", r"\bAPPS?\b",
        ]

        blocked_title_patterns = [
            r"\bEBOOK\b", r"\bEPUB\b", r"\bPDF\b", r"\bMOBI\b", r"\bAZW3\b", r"\bCBZ\b", r"\bCBR\b",
            r"\bAUDIOBOOK\b", r"\bFLAC\b", r"\bMP3\b", r"\bALBUM\b", r"\bVINYL\b",
            r"\bDISCOGRAPHY\b", r"\bOST\b", r"\bSOUNDTRACK\b",
            r"\bFITGIRL\b", r"\bRAZOR1911\b", r"\bRELOADED\b", r"\bSKIDROW\b",
            r"\bCODEX\b", r"\bDODI\b", r"\bELAMIGOS\b", r"\bGOG\b", r"\bSTEAM\b",
            r"\bSWITCH\b", r"\bXCI\b", r"\bNSP\b", r"\bPS4\b", r"\bPS5\b", r"\bXBOX\b",
            r"\bWIN64\b", r"\bPORTABLE\b", r"\bPREACTIVATED\b", r"\bBUILD\s*\d+\b",
            r"\bDLC\b", r"\bBONUSES\b", r"\bHENTAI\b", r"\bXXX\b",
        ]

        if any(re.search(pattern, category_blob) for pattern in blocked_category_patterns):
            return True

        return any(re.search(pattern, title_upper) for pattern in blocked_title_patterns)

    def _release_matches_detail(rel: dict) -> bool:
        if tmdb_id is None or not media_type or not title:
            return True

        if _looks_like_non_video_release(rel):
            return False

        rel_title = rel.get("title") or ""
        rel_tokens = _tokenize_release_text(rel_title)
        expected_tokens = _tokenize_release_text(title)
        expected_set = {t for t in expected_tokens if len(t) > 1}
        rel_set = set(rel_tokens)

        if not expected_set:
            return True

        matched_tokens = expected_set.intersection(rel_set)
        token_ratio = len(matched_tokens) / len(expected_set)

        rel_years = _extract_years(rel_title)
        has_expected_year = year is None or year in rel_years or not rel_years

        has_season, has_episode = _extract_season_episode(rel_title)
        if media_type == "movie" and (has_season or has_episode):
            return False

        if media_type == "tv":
            if len(expected_set) >= 2 and token_ratio < 0.6:
                return False
        else:
            if len(expected_set) >= 2 and token_ratio < 0.75:
                return False

        if not has_expected_year:
            return False

        return True

    async with httpx.AsyncClient() as c:
        r = await c.get(
            f"{PROWLARR_URL()}/api/v1/search",
            params={"query": query, "type": "search"},
            headers={"X-Api-Key": PROWLARR_API_KEY()},
            timeout=20.0,
        )
        r.raise_for_status()
        data = r.json()
        releases = data if isinstance(data, list) else data.get("results", [])

        normalized = []
        for rel in releases:
            rel = dict(rel)
            info_url = rel.get("infoUrl") or rel.get("detailsUrl") or rel.get("comments") or rel.get("commentUrl")
            download_url = rel.get("downloadUrl") or rel.get("guid")
            rel["sourceUrl"] = info_url if isinstance(info_url, str) and info_url.startswith(("http://", "https://")) else None
            rel["downloadUrl"] = download_url
            normalized.append(rel)

        if tmdb_id is not None and media_type and title:
            normalized = [rel for rel in normalized if _release_matches_detail(rel)]

        return {"results": normalized, "count": len(normalized)}

class DownloadRequest(BaseModel):
    guid: str
    category: str = "manual"

@app.post("/api/download")
async def download(req: DownloadRequest):
    # Client persistant pour conserver le cookie SID qBittorrent
    async with httpx.AsyncClient(verify=False) as c:
        auth = await c.post(
            f"{QBIT_URL()}/api/v2/auth/login",
            data={"username": QBIT_USER(), "password": QBIT_PASS()},
            timeout=10.0,
        )
        # qBit >= 5.x répond 204 No Content (succès) ou 200 avec body "Fails."
        if auth.status_code not in (200, 204):
            logger.warning("qBit auth failed — status: %d body: %r", auth.status_code, auth.text)
            raise HTTPException(401, "Auth qBittorrent echouee")
        if auth.status_code == 200 and auth.text.strip() == "Fails.":
            logger.warning("qBit auth failed — bad credentials")
            raise HTTPException(401, "Auth qBittorrent echouee")

        # Cookie: SID ou QBT_SID_<port> selon la version qBit
        sid = None
        for name, value in auth.cookies.items():
            if "sid" in name.lower():
                sid = value
                break
        if not sid:
            for name, value in c.cookies.items():
                if "sid" in name.lower():
                    sid = value
                    break
        if not sid:
            raise HTTPException(401, "Auth qBittorrent echouee (SID manquant)")

        # Récupérer le nom exact du cookie pour le renvoyer
        cookie_name = next((n for n in {**auth.cookies, **dict(c.cookies)} if "sid" in n.lower()), "SID")
        headers = {"Cookie": f"{cookie_name}={sid}"}

        if req.guid.startswith("magnet:"):
            res = await c.post(
                f"{QBIT_URL()}/api/v2/torrents/add",
                data={"urls": req.guid, "category": req.category},
                headers=headers,
                timeout=15.0,
            )
        else:
            # Télécharger le .torrent (sans cookie)
            async with httpx.AsyncClient(verify=False) as dl:
                t = await dl.get(req.guid, follow_redirects=True, timeout=15.0)
                t.raise_for_status()
            res = await c.post(
                f"{QBIT_URL()}/api/v2/torrents/add",
                data={"category": req.category},
                files={"torrents": ("dl.torrent", t.content, "application/x-bittorrent")},
                headers=headers,
                timeout=15.0,
            )
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
