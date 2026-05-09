const BASE = import.meta.env.VITE_API_BASE_URL || ''

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json', ...options?.headers },
    ...options,
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || `HTTP ${res.status}`)
  }
  return res.json()
}

export interface TMDBSearchParams {
  query: string
  year?: number | null
  media_type?: 'movie' | 'tv' | 'animation' | null
  genre_id?: number | null
  vote_min?: number | null
  sort_by?: 'popularity' | 'vote_average' | 'release_date' | null
}

export interface TMDBGenre { id: number; name: string }

export const getGenres = () =>
  request<{ genres: TMDBGenre[] }>('/api/tmdb/genres')

export const searchTMDB = ({ query, year, media_type, genre_id, vote_min, sort_by }: TMDBSearchParams) => {
  const p = new URLSearchParams({ query })
  if (year       != null) p.set('year',       String(year))
  if (media_type != null) p.set('media_type', media_type)
  if (genre_id   != null) p.set('genre_id',   String(genre_id))
  if (vote_min   != null) p.set('vote_min',   String(vote_min))
  if (sort_by    != null) p.set('sort_by',    sort_by)
  return request<{ results: TMDBResult[]; total: number }>(`/api/tmdb/search?${p.toString()}`)
}

export interface HomeRows {
  trending_movies: TMDBResult[]
  trending_tv:     TMDBResult[]
  upcoming_movies: TMDBResult[]
  upcoming_tv:     TMDBResult[]
}

export const getHomeRows = () =>
  request<HomeRows>('/api/tmdb/home-rows')

export interface QualityProfile { id: number; name: string }

export interface MonitorStatusResult {
  monitored:      boolean
  status:         string | null   // announced/inCinemas/released | continuing/ended
  hasFile:        boolean
  title:          string
  qualityProfile: number | null
  monitored_flag: boolean
}

export const getMonitorStatus = (tmdbId: number, mediaType: string) =>
  request<MonitorStatusResult>(
    `/api/monitor/status?tmdb_id=${tmdbId}&media_type=${mediaType}`
  )

export const getRadarrProfiles = () =>
  request<QualityProfile[]>('/api/radarr/profiles')

export const getSonarrProfiles = () =>
  request<QualityProfile[]>('/api/sonarr/profiles')

export const getTMDBDetails = (mediaType: string, id: number) =>
  request<any>(`/api/tmdb/details/${mediaType}/${id}`)

export const searchReleases = (query: string) =>
  request<{ results: Release[]; count: number }>(`/api/releases?query=${encodeURIComponent(query)}`)

export const downloadTorrent = (guid: string, category = 'manual') =>
  request<{ status: string }>('/api/download', {
    method: 'POST',
    body: JSON.stringify({ guid, category }),
  })

export const monitorMedia = (
  tmdb_id: number,
  title: string,
  media_type: string,
  quality_profile_id?: number | null
) =>
  request<{ status: string; message: string }>('/api/monitor', {
    method: 'POST',
    body: JSON.stringify({ tmdb_id, title, media_type, quality_profile_id: quality_profile_id ?? null }),
  })

export interface TMDBResult {
  id: number
  media_type: 'movie' | 'tv'
  title: string
  original_title: string
  overview: string
  poster_path: string | null
  backdrop_path: string | null
  release_date: string
  vote_average: number
  vote_count: number
}

export interface Release {
  guid: string
  title: string
  size: number
  indexer: string
  seeders: number
  leechers: number
  downloadUrl?: string
  magnetUrl?: string
}

export type ReleaseType = 'Intégrale' | 'Saison' | 'Épisode' | 'Film'

export const detectReleaseType = (title: string): ReleaseType => {
  const t = title.toUpperCase()
  if (/\bS\d{2}E\d{2}\b/.test(t))           return 'Épisode'
  if (/\bS\d{2}\b/.test(t) && !/E\d{2}/.test(t)) return 'Saison'
  if (/\bINTEGRALE\b|COMPLETE.SERIES|SAISONS/.test(t)) return 'Intégrale'
  return 'Film'
}