export const poster = (path: string | null, size = 'w342') =>
  path ? `https://image.tmdb.org/t/p/${size}${path}` : '/placeholder.png'

export const backdrop = (path: string | null, size = 'original') =>
  path ? `https://image.tmdb.org/t/p/${size}${path}` : ''

export const formatYear = (date?: string) =>
  date ? new Date(date).getFullYear().toString() : '—'

export const formatBytes = (bytes: number): string => {
  if (!bytes) return '—'
  const gb = bytes / 1_073_741_824
  return gb >= 1 ? `${gb.toFixed(1)} GB` : `${(bytes / 1_048_576).toFixed(0)} MB`
}

const NORM: Record<string, string> = {
  '4K': '4K', '1080P': '1080p', '720P': '720p', 'SD': 'SD',
  'BLURAY': 'BluRay', 'BLU-RAY': 'BluRay', 'REMUX': 'BluRay', 'BDRIP': 'BluRay',
  'WEB-DL': 'WEB', 'WEBRIP': 'WEBRip', 'DVDRIP': 'DVDRip',
  'HDTV': 'HDTV', 'SDTV': 'SDTV', 'HDLIGHT': 'WEB',
  'X265': 'H.265', 'HEVC': 'H.265', 'H265': 'H.265',
  'X264': 'H.264', 'H264': 'H.264',
  'X263': 'H.263', 'H263': 'H.263',
  'X262': 'H.262', 'H262': 'H.262',
  'AV1': 'AV1',
  'DV+HDR10+': 'DV+HDR10+', 'DV+HDR10': 'DV+HDR10',
  'DOLBY.VISION': 'Dolby Vision', 'DOLBY VISION': 'Dolby Vision',
  'DOVI': 'Dolby Vision', 'HDR10+': 'HDR10+', 'HDR10': 'HDR10',
  'HDR': 'HDR10', 'DV': 'DV+HDR10', 'SDR': 'SDR',
  'TRUEHD': 'Lossless', 'DTS-HD': 'Lossless', 'FLAC': 'Lossless', 'ATMOS': 'Lossless',
  'DDP': 'Lossy', 'EAC3': 'Lossy', 'AC3': 'Lossy', 'AAC': 'Lossy',
  'DTS': 'Lossy', 'OPUS': 'Lossy',
  'TRUEFRENCH': 'TRUEFRENCH', 'VOSTFR': 'VOSTFR',
  'VFF': 'VFF', 'VF2': 'VF2', 'VFQ': 'VFQ', 'MULTI': 'MULTI', 'VF': 'VF',
}

const n = (val: string): string => NORM[val.toUpperCase()] ?? val

export const extractMeta = (title: string) => {
  const t = title.toUpperCase()

  const resolution = n(
    t.match(/\b(2160P|4K|1080P|720P)\b/)?.[0]?.replace('2160P', '4K') ?? 'SD'
  )

  const source = n(
    t.match(/\b(BLURAY|BLU-RAY|REMUX|WEB-DL|WEBRIP|DVDRIP|HDTV|SDTV|HDLIGHT|BDRIP)\b/)?.[0] ?? ''
  )

  const codec = n(
    t.match(/\b(X265|HEVC|X264|AV1|H265|H264)\b/)?.[0] ?? ''
  )

  const hdrRaw =
    t.match(/\bDV\+HDR10\+/)?.[0] ??
    t.match(/\bDV\+HDR10\b/)?.[0] ??
    t.match(/\b(DOLBY\.VISION|DOVI|HDR10\+|HDR10|HDR|DV)\b/)?.[0] ??
    'SDR'
  const hdr = n(hdrRaw)

  const audio = n(
    t.match(/\b(TRUEHD|DTS-HD|FLAC|ATMOS|DDP|EAC3|AC3|AAC|DTS|OPUS)\b/)?.[0] ?? ''
  )

  const channels =
    t.match(/\b(7\.1|5\.1|2\.0|1\.0)\b/)?.[0] ?? ''

  const language = n(
    t.match(/\b(TRUEFRENCH|VFF|VF2|VFQ|VOSTFR|MULTI)\b/)?.[0] ??
    (t.match(/\bVF\b/) ? 'VF' : '')
  )

  const type3d =
    t.match(/\b3D[. ]?FSBS\b/) ? '3D FSBS' :
    t.match(/\b3D[. ]?HSBS\b/) ? '3D HSBS' :
    t.match(/\b3D\b/)          ? '3D'      : '2D'

  return { resolution, source, codec, hdr, audio, channels, language, type3d }
}