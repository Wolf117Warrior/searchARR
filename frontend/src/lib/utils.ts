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

// ─── Valeurs normalisées (affichées dans les badges) ────────────────────────
export const NORM_RESOLUTION = {
  '4K':    '4K',
  '2160P': '4K',
  'UHD':   '4K',
  '1080P': '1080p',
  'FHD':   '1080p',
  '720P':  '720p',
} as const

export const NORM_SOURCE = {
  'BLURAY':   'BluRay',
  'BLU-RAY':  'BluRay',
  'BDRIP':    'BluRay',
  'REMUX':    'Remux',
  'BDREMUX':  'Remux',
  'WEB-DL':   'Web',
  'WEBDL':    'Web',
  'WEBRIP':   'WebRip',
  'WEB-RIP':  'WebRip',
  'HDTV':     'HDTV',
  'HDLIGHT':  'HDLight',
  'DVDRIP':   'DVDRip',
  'SDTV':     'SDTV',
} as const

export const NORM_CODEC = {
  'X265':  'H.265',
  'H265':  'H.265',
  'HEVC':  'H.265',
  'X264':  'H.264',
  'H264':  'H.264',
  'AVC':   'H.264',
  'AV1':   'AV1',
} as const

export const NORM_HDR = {
  'SDR':          'SDR',
  'HDR10PLUS':    'HDR10+',
  'HDR10+':       'HDR10+',
  'HDR10':        'HDR10',
  'HDR':          'HDR',
  'DOLBY.VISION': 'Dolby Vision',
  'DOLBYVISION':  'Dolby Vision',
  'DOVI':         'Dolby Vision',
  'DV':           'Dolby Vision',
} as const

export const NORM_AUDIO = {
  'DOLBY.ATMOS':  'Atmos',
  'DOLBYATMOS':   'Atmos',
  'TRUEHD.ATMOS': 'Atmos',
  'ATMOS':        'Atmos',
  'EAC3':         'EAC3',
  'E-AC-3':       'EAC3',
  'DDP5.1':       'Dolby Audio',
  'DDP':          'Dolby Audio',
  'DD+':          'Dolby Audio',
  'DOLBY.DIGITAL.PLUS': 'Dolby Audio',
  'DOLBY.DIGITAL':      'Dolby Audio',
  'DTS-HD.MA':    'DTS-HD MA',
  'DTS-HD':       'DTS-HD MA',
  'DTS.HD.MA':    'DTS-HD MA',
  'DTS:X':        'DTS:X',
  'DTSX':         'DTS:X',
  'DTS-ES':       'DTS',
  'DTS.ES':       'DTS',
  'DTS':          'DTS',
  'TRUEHD':       'TrueHD',
  'FLAC':         'FLAC',
  'AAC':          'AAC',
  'AC3':          'AC3',
  'OPUS':         'Opus',
} as const

export const NORM_LANG = {
  'MULTI':      'MULTI',
  'TRUEFRENCH': 'TRUEFRENCH',
  'VFQ':        'VFQ',
  'CA':         'VFQ',
  'FRENCH':     'FRENCH',
  'FR':         'FRENCH',
  'VFF':        'VF',
  'VF2':        'VF',
  'VF':         'VF',
  'VOSTFR':     'VOSTFR',
} as const

// ─── Helpers ─────────────────────────────────────────────────────────────────
const matchFirst = <T extends Record<string, string>>(
  t: string,
  map: T
): string => {
  for (const key of Object.keys(map)) {
    // Escape les caractères spéciaux pour le regex
    const escaped = key.replace(/[.+?^${}()|[\]\\]/g, '\\$&')
    if (new RegExp(`(?:^|[\\s.\\-_\\[\\]()])${escaped}(?=[\\s.\\-_\\[\\]()]|$)`, 'i').test(t)) {
      return (map as Record<string, string>)[key]
    }
  }
  return ''
}

export const extractMeta = (title: string) => {
  const t = title

  // Résolution
  const resolution = (() => {
    const m = t.match(/\b(2160[pP]|4[Kk]|[Uu][Hh][Dd]|1080[pP]|[Ff][Hh][Dd]|720[pP])\b/)
    if (!m) return 'SD'
    const k = m[0].toUpperCase()
    return (NORM_RESOLUTION as Record<string, string>)[k] ?? 'SD'
  })()

  // Source — ordre priorité : Remux avant BluRay, HDLight avant WEB
  const source = (() => {
    const order = [
      ['BDREMUX', 'Remux'], ['REMUX', 'Remux'],
      ['BLURAY', 'BluRay'], ['BLU-RAY', 'BluRay'], ['BDRIP', 'BluRay'],
      ['HDLIGHT', 'HDLight'],
      ['WEB-DL', 'Web'], ['WEBDL', 'Web'],
      ['WEB-RIP', 'WebRip'], ['WEBRIP', 'WebRip'],
      ['HDTV', 'HDTV'],
      ['DVDRIP', 'DVDRip'], ['SDTV', 'SDTV'],
    ] as [string, string][]
    const u = t.toUpperCase()
    for (const [token, norm] of order) {
      const escaped = token.replace(/[.+?^${}()|[\]\\]/g, '\\$&')
      if (new RegExp(`(?:^|[\\s.\\-_\\[\\]()])${escaped}(?=[\\s.\\-_\\[\\]()]|$)`).test(u)) {
        return norm
      }
    }
    return ''
  })()

  // Codec
  const codec = (() => {
    const u = t.toUpperCase()
    if (/\bAV1\b/.test(u))                    return 'AV1'
    if (/\b(X265|H265|H\.265|HEVC)\b/.test(u)) return 'H.265'
    if (/\b(X264|H264|H\.264|AVC)\b/.test(u))  return 'H.264'
    return ''
  })()

  // HDR — ordre priorité strict (plus spécifique en premier)
  const hdr = (() => {
    const u = t.toUpperCase().replace(/\s+/g, '.')
    if (/DV[.+]HDR10[+PLUS]/.test(u))                            return 'DV+HDR10+'
    if (/DV[.+]HDR10/.test(u))                                   return 'DV+HDR10'
    if (/HDR10[+PLUS]/.test(u) || /HDR10PLUS/.test(u))           return 'HDR10+'
    if (/HDR10/.test(u))                                         return 'HDR10'
    if (/DOLBY\.VISION|DOLBYVISION|\bDOVI\b/.test(u))            return 'Dolby Vision'
    if (/\bDV\b/.test(u))                                        return 'Dolby Vision'
    if (/\bHDR\b/.test(u))                                       return 'HDR'
    return 'SDR'
  })()

  // Audio — ordre priorité (plus spécifique en premier)
  const audio = (() => {
    const u = t.toUpperCase().replace(/\s+/g, '.')
    if (/TRUEHD\.ATMOS|DOLBY\.ATMOS|DOLBYATMOS|\bATMOS\b/.test(u)) return 'Atmos'
    if (/DTS:X|DTSX/.test(u))                                      return 'DTS:X'
    if (/DTS-HD\.MA|DTS\.HD\.MA|DTS-HD/.test(u))                   return 'DTS-HD MA'
    if (/DTS-ES|DTS\.ES/.test(u))                                  return 'DTS'
    if (/\bDTS\b/.test(u))                                         return 'DTS'
    if (/\bTRUEHD\b/.test(u))                                      return 'TrueHD'
    if (/DOLBY\.DIGITAL\.PLUS|DDP5|\bDDP\b|\bDD\+\b/.test(u))     return 'Dolby Audio'
    if (/\bEAC3\b|E-AC-3/.test(u))                                 return 'EAC3'
    if (/DOLBY\.DIGITAL|\bAC3\b/.test(u))                          return 'Dolby Audio'
    if (/\bFLAC\b/.test(u))                                        return 'FLAC'
    if (/\bAAC\b/.test(u))                                         return 'AAC'
    if (/\bOPUS\b/.test(u))                                        return 'Opus'
    return ''
  })()

  // Canaux
  const channels = t.match(/\b(7\.1|5\.1|2\.1|2\.0)\b/)?.[0] ?? ''

  // Langue — ordre priorité (TRUEFRENCH avant FRENCH, VFQ avant VF)
  const language = (() => {
    const u = t.toUpperCase()
    if (/\bMULTI\b/.test(u))      return 'MULTI'
    if (/\bTRUEFRENCH\b/.test(u)) return 'TRUEFRENCH'
    if (/\bVFQ\b|\bCA\b/.test(u)) return 'VFQ'
    if (/\bFRENCH\b|\bFR\b/.test(u)) return 'FRENCH'
    if (/\bVFF\b|\bVF2\b|\bVF\b/.test(u)) return 'VF'
    if (/\bVOSTFR\b/.test(u))     return 'VOSTFR'
    return ''
  })()

  return { resolution, source, codec, hdr, audio, channels, language }
}

// ─── Labels de filtre ─────────────────────────────────────────────────────────
// Structure : { label: string (affiché), value: string (clé interne), aliases: string[] (valeurs normalisées matchées) }
export interface FilterOption {
  label:   string
  value:   string
  aliases: string[]
}

export const FILTER_RESOLUTION: FilterOption[] = [
  { label: '4K / UHD',  value: '4K',    aliases: ['4K']    },
  { label: '1080p',     value: '1080p', aliases: ['1080p'] },
  { label: '720p',      value: '720p',  aliases: ['720p']  },
  { label: 'SD',        value: 'SD',    aliases: ['SD']    },
]

export const FILTER_SOURCE: FilterOption[] = [
  { label: 'Remux',   value: 'Remux',   aliases: ['Remux']   },
  { label: 'BluRay',  value: 'BluRay',  aliases: ['BluRay']  },
  { label: 'Web',     value: 'Web',     aliases: ['Web']     },
  { label: 'WebRip',  value: 'WebRip',  aliases: ['WebRip']  },
  { label: 'HDLight', value: 'HDLight', aliases: ['HDLight'] },
  { label: 'HDTV',    value: 'HDTV',   aliases: ['HDTV']    },
  { label: 'DVDRip',  value: 'DVDRip', aliases: ['DVDRip']  },
]

export const FILTER_CODEC: FilterOption[] = [
  { label: 'AV1',   value: 'AV1',   aliases: ['AV1']   },
  { label: 'H.265 / x265', value: 'H.265', aliases: ['H.265'] },
  { label: 'H.264 / x264', value: 'H.264', aliases: ['H.264'] },
]

export const FILTER_HDR: FilterOption[] = [
  { label: 'SDR',          value: 'SDR',          aliases: ['SDR']          },
  { label: 'HDR',          value: 'HDR',          aliases: ['HDR']          },
  { label: 'HDR10 / 10bits', value: 'HDR10',      aliases: ['HDR10']        },
  { label: 'HDR10+',       value: 'HDR10+',       aliases: ['HDR10+']       },
  { label: 'Dolby Vision (DV)', value: 'Dolby Vision', aliases: ['Dolby Vision', 'DV+HDR10', 'DV+HDR10+'] },
]

export const FILTER_AUDIO: FilterOption[] = [
  { label: 'Atmos',        value: 'Atmos',       aliases: ['Atmos']       },
  { label: 'EAC3',         value: 'EAC3',        aliases: ['EAC3']        },
  { label: 'Dolby Audio (DDP)', value: 'Dolby Audio', aliases: ['Dolby Audio'] },
  { label: 'DTS',          value: 'DTS',         aliases: ['DTS']         },
  { label: 'DTS-HD MA',    value: 'DTS-HD MA',   aliases: ['DTS-HD MA']   },
  { label: 'DTS:X',        value: 'DTS:X',       aliases: ['DTS:X']       },
  { label: 'TrueHD',       value: 'TrueHD',      aliases: ['TrueHD']      },
]

export const FILTER_CHANNELS: FilterOption[] = [
  { label: '7.1', value: '7.1', aliases: ['7.1'] },
  { label: '5.1', value: '5.1', aliases: ['5.1'] },
  { label: '2.1', value: '2.1', aliases: ['2.1'] },
  { label: '2.0', value: '2.0', aliases: ['2.0'] },
]

export const FILTER_LANG: FilterOption[] = [
  { label: 'MULTI',      value: 'MULTI',      aliases: ['MULTI']      },
  { label: 'TRUEFRENCH', value: 'TRUEFRENCH', aliases: ['TRUEFRENCH'] },
  { label: 'VFQ (CA)',   value: 'VFQ',        aliases: ['VFQ']        },
  { label: 'FRENCH (FR)', value: 'FRENCH',   aliases: ['FRENCH']      },
  { label: 'VF (VFF/VF2)', value: 'VF',      aliases: ['VF']         },
  { label: 'VOSTFR',     value: 'VOSTFR',    aliases: ['VOSTFR']     },
]
