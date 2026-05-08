<script lang="ts">
  import { page } from '$app/stores'
  import { onMount } from 'svelte'
  import { getTMDBDetails, searchReleases, downloadTorrent, monitorMedia,
           getRadarrProfiles, getSonarrProfiles, getMonitorStatus,
           type Release, type QualityProfile, type MonitorStatusResult } from '$lib/api'
  import { backdrop, poster, formatYear, extractMeta } from '$lib/utils'
  import ReleaseRow from '$lib/ReleaseRow.svelte'
  import FilterBar from '$lib/FilterBar.svelte'
import { detectReleaseType, type ReleaseType } from '$lib/api'

const RELEASE_TYPES: ReleaseType[] = ['Film', 'Intégrale', 'Saison', 'Épisode']
let activeTypes = new Set<ReleaseType>()


  const id       = Number($page.url.searchParams.get('id'))
  const type     = $page.url.searchParams.get('type') || 'movie'
  const rawTitle = $page.url.searchParams.get('title') || ''

  let details: any = null
  let releases: Release[] = []
  let downloaded = new Set<string>()
  let loadingDetails = true
  let loadingReleases = false
  let monitorStatus: 'idle'|'loading'|'success'|'exists'|'error' = 'idle'
  let monitorMsg    = ''
  let errorDetails  = ''

  // Profils qualité
  let profiles:        QualityProfile[] = []
  let loadingProfiles  = false
  let showDropdown     = false
  let selectedProfile: QualityProfile | null = null

  // Statut de surveillance
  let monitorInfo: MonitorStatusResult | null = null
  let loadingMonitorInfo = true

  // Filtres
  let activeRes   = new Set<string>()
  let activeSrc   = new Set<string>()
  let activeLang  = new Set<string>()
  let activeCodec = new Set<string>()
  let activeHdr      = new Set<string>()
  let activeAudio    = new Set<string>()
  let activeChannels = new Set<string>()
  let activeType3d   = new Set<string>()

  // Filtres saison / épisode (séries uniquement)
  let filterSeason:  number | null = null
  let filterEpisode: number | null = null

  // Filtre année (tous médias)
  let filterYear: number | null = null

  const RESOLUTIONS = ['4K', '1080p', '720p', 'SD']
  const SOURCES     = ['BluRay', 'WEB', 'WEBRip', 'DVDRip', 'HDTV', 'SDTV']
  const CODECS      = ['H.265', 'H.264', 'H.263', 'H.262', 'AV1']
  const HDR         = ['SDR', 'HDR10', 'HDR10+', 'Dolby Vision', 'DV+HDR10', 'DV+HDR10+']
  const AUDIO_TYPE  = ['Lossless', 'Lossy']
  const CHANNELS    = ['7.1', '5.1', '2.0', '1.0']
  const LANGUAGES   = ['MULTI', 'VFF', 'TRUEFRENCH', 'VOSTFR', 'VFQ', 'VF', 'MULTI.VF2', 'VF2']
  const TYPES_3D    = ['2D', '3D FSBS', '3D', '3D HSBS']

  onMount(async () => {
    try {
      details = await getTMDBDetails(type, id)
    } catch(e: any) {
      errorDetails = e.message
    } finally {
      loadingDetails = false
    }
    // Check statut Radarr/Sonarr en parallèle avec les releases
    Promise.all([
      loadReleases(),
      getMonitorStatus(id, type)
        .then(s => {
          monitorInfo = s
          // Si déjà surveillé, on pré-remplace le statut du bouton
          if (s.monitored) monitorStatus = 'exists'
        })
        .catch(() => {})
        .finally(() => { loadingMonitorInfo = false })
    ])
  })

  const loadReleases = async () => {
    if (!rawTitle) return
    loadingReleases = true
    try {
      const data = await searchReleases(rawTitle)
      releases = (data.results || []).sort((a: Release, b: Release) => (b.seeders ?? 0) - (a.seeders ?? 0))
    } catch {}
    finally { loadingReleases = false }
  }

  const handleDownload = async (url: string) => {
    try {
      await downloadTorrent(url)
      downloaded = new Set([...downloaded, url])
    } catch(e: any) {
      alert(`Erreur download: ${e.message}`)
    }
  }

  const openDropdown = async () => {
    if (profiles.length === 0) {
      loadingProfiles = true
      try {
        profiles = type === 'movie'
          ? await getRadarrProfiles()
          : await getSonarrProfiles()
        if (profiles.length > 0) selectedProfile = profiles[0]
      } catch { profiles = [] }
      finally { loadingProfiles = false }
    }
    showDropdown = !showDropdown
  }

  const handleMonitor = async () => {
    if (!details) return
    showDropdown = false
    monitorStatus = 'loading'
    try {
      const res = await monitorMedia(
        id,
        details.title || details.name,
        type,
        selectedProfile?.id ?? null
      )
      monitorStatus = res.status === 'exists' ? 'exists' : 'success'
      monitorMsg = res.message
    } catch(e: any) {
      monitorStatus = 'error'
      monitorMsg = e.message
    }
  }

$: filteredReleases = releases.filter(r => {
  const m = extractMeta(r.title)
  if (activeRes.size      > 0 && !activeRes.has(m.resolution))   return false
  if (activeSrc.size      > 0 && !activeSrc.has(m.source))       return false
  if (activeLang.size     > 0 && !activeLang.has(m.language))    return false
  if (activeCodec.size    > 0 && !activeCodec.has(m.codec))      return false
  if (activeHdr.size      > 0 && !activeHdr.has(m.hdr))          return false
  if (activeAudio.size    > 0 && !activeAudio.has(m.audio))      return false
  if (activeChannels.size > 0 && !activeChannels.has(m.channels)) return false
  if (activeTypes.size    > 0 && !activeTypes.has(detectReleaseType(r.title))) return false
  if (activeType3d.size   > 0 && !activeType3d.has(m.type3d ?? '2D'))         return false
  if (filterSeason != null) {
    const s = String(filterSeason).padStart(2, '0')
    if (!r.title.toUpperCase().includes(`S${s}`)) return false
  }
  if (filterEpisode != null) {
    const e = String(filterEpisode).padStart(2, '0')
    if (!r.title.toUpperCase().includes(`E${e}`)) return false
  }
  if (filterYear != null) {
    if (!r.title.includes(String(filterYear))) return false
  }
  return true
})

$: hasFilters = [activeRes, activeSrc, activeLang, activeCodec,
                 activeHdr, activeAudio, activeChannels, activeTypes, activeType3d]
  .some(s => s.size > 0) || filterSeason != null || filterEpisode != null || filterYear != null

const resetFilters = () => {
  activeRes = new Set(); activeSrc = new Set()
  activeLang = new Set(); activeCodec = new Set()
  activeHdr = new Set(); activeAudio = new Set()
  activeChannels = new Set(); activeTypes = new Set()
  activeType3d = new Set()
  filterSeason = null; filterEpisode = null
  filterYear = null
}
</script>

<svelte:head><title>{rawTitle} — searchARR</title></svelte:head>

{#if loadingDetails}
  <div class="flex items-center justify-center py-32">
    <svg class="w-8 h-8 animate-spin text-indigo-500" fill="none" viewBox="0 0 24 24">
      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
    </svg>
  </div>

{:else if errorDetails}
  <div class="text-center text-red-400 py-20">{errorDetails}</div>

{:else if details}
  <!-- Backdrop -->
  {#if details.backdrop_path}
    <div class="relative h-56 sm:h-72 overflow-hidden">
      <img src={backdrop(details.backdrop_path)} alt=""
        class="absolute inset-0 w-full h-full object-cover object-top" loading="lazy" />
      <div class="absolute inset-0 bg-gradient-to-b from-transparent via-[#0d0f14]/60 to-[#0d0f14]"></div>
    </div>
  {/if}

  <div class="max-w-7xl mx-auto px-4 sm:px-6 {details.backdrop_path ? '-mt-24 relative z-10' : 'pt-8'}">

    <!-- Header media -->
    <div class="flex gap-6 mb-10">
      {#if details.poster_path}
        <img src={poster(details.poster_path, 'w342')} alt={details.title || details.name}
          class="hidden sm:block w-36 rounded-xl shadow-2xl ring-1 ring-white/10 flex-shrink-0" loading="lazy" />
      {/if}
      <div class="flex flex-col gap-3 justify-end pb-1">
        <div class="flex items-center gap-2 flex-wrap">
          <span class="badge {type === 'movie' ? 'bg-blue-500/20 text-blue-300 border border-blue-500/30' : 'bg-purple-500/20 text-purple-300 border border-purple-500/30'}">
            {type === 'movie' ? 'Film' : 'Série'}
          </span>
          {#if details.release_date || details.first_air_date}
            <span class="text-xs text-gray-500">{formatYear(details.release_date || details.first_air_date)}</span>
          {/if}
          {#if details.vote_average > 0}
            <span class="badge bg-black/40 text-yellow-400">★ {details.vote_average.toFixed(1)}</span>
          {/if}
        </div>
        <h1 class="text-2xl sm:text-3xl font-bold text-white leading-tight">
          {details.title || details.name}
        </h1>
        {#if details.overview}
          <p class="text-sm text-gray-400 leading-relaxed max-w-2xl line-clamp-3">{details.overview}</p>
        {/if}

        <!-- Monitor button + dropdown profil -->
        <div class="mt-1 relative">

          <!-- Badge statut fichier (toujours visible si surveillé) -->
          {#if monitorInfo?.monitored && monitorInfo?.hasFile}
            <div class="inline-flex items-center gap-1.5 text-xs text-emerald-400
                        bg-emerald-400/10 border border-emerald-400/20
                        px-3 py-1 rounded-full mb-2">
              <svg class="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414L8.414 15l-4.121-4.121a1 1 0 111.414-1.414L8.414 12.172l7.879-7.879a1 1 0 011.414 0z" clip-rule="evenodd"/>
              </svg>
              Fichier disponible
            </div>
          {/if}

          {#if monitorStatus === 'idle'}
            <!-- Bouton split : étiquette | chevron -->
            <div class="inline-flex rounded-xl overflow-hidden ring-1 ring-indigo-500/60">
              <!-- Action principale -->
              <button
                class="btn-primary rounded-none rounded-l-xl border-r border-indigo-400/30 pr-3"
                disabled={loadingProfiles}
                on:click={handleMonitor}
              >
                <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                {type === 'movie' ? 'Surveiller (Radarr)' : 'Surveiller (Sonarr)'}
                {#if selectedProfile}
                  <span class="ml-1.5 text-indigo-200/70 text-xs font-normal">· {selectedProfile.name}</span>
                {/if}
              </button>
              <!-- Toggle dropdown profil -->
              <button
                class="btn-primary rounded-none rounded-r-xl px-2.5"
                aria-label="Choisir le profil qualité"
                on:click={openDropdown}
              >
                {#if loadingProfiles}
                  <svg class="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
                  </svg>
                {:else}
                  <svg class="w-3 h-3 transition-transform {showDropdown ? 'rotate-180' : ''}" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
                  </svg>
                {/if}
              </button>
            </div>

            <!-- Dropdown liste profils -->
            {#if showDropdown && profiles.length > 0}
              <div class="absolute left-0 top-full mt-1.5 z-50
                          bg-surface-800 border border-white/10 rounded-xl shadow-2xl
                          py-1 min-w-[180px] animate-in">
                {#each profiles as p}
                  <button
                    class="w-full text-left px-4 py-2 text-sm transition-colors
                           {selectedProfile?.id === p.id
                             ? 'text-indigo-300 bg-indigo-500/15'
                             : 'text-gray-300 hover:bg-white/5'}"
                    on:click={() => { selectedProfile = p; showDropdown = false }}
                  >
                    {#if selectedProfile?.id === p.id}
                      <span class="mr-1.5">✓</span>
                    {/if}
                    {p.name}
                  </button>
                {/each}
              </div>
            {/if}

          {:else if monitorStatus === 'loading'}
            <div class="flex items-center gap-2 text-sm text-gray-400">
              <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
              </svg>
              Envoi en cours...
            </div>
          {:else if monitorStatus === 'success'}
            <div class="flex items-center gap-2 text-sm text-green-400 bg-green-400/10 px-4 py-2 rounded-xl border border-green-400/20">✓ {monitorMsg}</div>
          {:else if monitorStatus === 'exists'}
            <div class="flex flex-col gap-1.5">
              <div class="inline-flex items-center gap-2 text-sm text-yellow-400
                          bg-yellow-400/10 px-4 py-2 rounded-xl border border-yellow-400/20">
                <svg class="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                  <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                {type === 'movie' ? 'Surveillé dans Radarr' : 'Surveillé dans Sonarr'}
                {#if monitorInfo?.status}
                  <span class="text-xs text-yellow-300/60 font-normal">· {monitorInfo.status}</span>
                {/if}
                {#if monitorInfo?.hasFile}
                  <span class="text-xs text-emerald-400 font-normal ml-1">· ✓ fichier</span>
                {/if}
              </div>
              <button class="text-xs text-gray-600 hover:text-gray-400 text-left pl-1"
                on:click={() => { monitorStatus = 'idle'; monitorInfo = null }}>
                Surveiller à nouveau
              </button>
            </div>
          {:else if monitorStatus === 'error'}
            <div class="flex items-center gap-2 text-sm text-red-400 bg-red-400/10 px-4 py-2 rounded-xl border border-red-400/20">
              ✗ {monitorMsg}
              <button class="underline text-xs ml-2" on:click={() => monitorStatus = 'idle'}>Réessayer</button>
            </div>
          {/if}
        </div>
      </div>
    </div>

    <!-- Bloc enrichi : métadonnées + casting + SVOD -->
    {#if details._enriched}
      {@const e = details._enriched}
      <div class="mb-8 flex flex-col gap-6">

        <!-- Métadonnées inline -->
        <div class="flex flex-wrap gap-x-5 gap-y-2 text-sm text-gray-400">
          {#if e.directors?.length}
            <div class="flex items-center gap-1.5">
              <span class="text-gray-600">Réalisateur</span>
              <span class="text-gray-200">{e.directors.map((d) => d.name).join(', ')}</span>
            </div>
          {/if}
          {#if e.genres?.length}
            <div class="flex items-center gap-1.5">
              <span class="text-gray-600">Genres</span>
              <div class="flex flex-wrap gap-1">
                {#each e.genres as g}
                  <span class="px-2 py-0.5 rounded-md text-xs bg-white/5 border border-white/10 text-gray-300">{g}</span>
                {/each}
              </div>
            </div>
          {/if}
          {#if e.runtime}
            <div class="flex items-center gap-1.5">
              <span class="text-gray-600">Durée</span>
              <span class="text-gray-200">{Math.floor(e.runtime / 60)}h{String(e.runtime % 60).padStart(2, '0')}</span>
            </div>
          {/if}
          {#if e.release_date}
            <div class="flex items-center gap-1.5">
              <span class="text-gray-600">{type === 'movie' ? 'Sortie' : 'Début'}</span>
              <span class="text-gray-200">{new Date(e.release_date).toLocaleDateString('fr-FR', { day: 'numeric', month: 'long', year: 'numeric' })}</span>
            </div>
          {/if}
        </div>

        <!-- SVOD / Providers FR -->
        {#if e.providers_fr?.flatrate?.length || e.providers_fr?.rent?.length}
          <div class="flex flex-col gap-2">
            <span class="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">Disponible en FR</span>
            <div class="flex flex-wrap gap-3">
              {#each e.providers_fr.flatrate as p}
                <a
                  href={e.providers_fr.link || '#'}
                  target="_blank" rel="noopener noreferrer"
                  title="{p.provider_name} (streaming)"
                  class="group relative"
                >
                  <img
                    src="https://image.tmdb.org/t/p/w45{p.logo_path}"
                    alt={p.provider_name}
                    class="w-9 h-9 rounded-lg ring-1 ring-white/10 group-hover:ring-indigo-400/60 transition-all"
                    loading="lazy"
                  />
                </a>
              {/each}
              {#each e.providers_fr.rent as p}
                <a
                  href={e.providers_fr.link || '#'}
                  target="_blank" rel="noopener noreferrer"
                  title="{p.provider_name} (location)"
                  class="group relative opacity-60 hover:opacity-100 transition-opacity"
                >
                  <img
                    src="https://image.tmdb.org/t/p/w45{p.logo_path}"
                    alt={p.provider_name}
                    class="w-9 h-9 rounded-lg ring-1 ring-white/10 grayscale group-hover:grayscale-0 transition-all"
                    loading="lazy"
                  />
                </a>
              {/each}
            </div>
          </div>
        {/if}

        <!-- Casting -->
        {#if e.cast?.length}
          <div class="flex flex-col gap-3">
            <span class="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">Casting</span>
            <div class="flex gap-3 overflow-x-auto pb-1 scrollbar-thin">
              {#each e.cast as actor}
                <div class="flex flex-col items-center gap-1.5 flex-shrink-0 w-16">
                  {#if actor.profile_path}
                    <img
                      src="https://image.tmdb.org/t/p/w185{actor.profile_path}"
                      alt={actor.name}
                      class="w-14 h-14 rounded-full object-cover ring-1 ring-white/10"
                      loading="lazy"
                    />
                  {:else}
                    <div class="w-14 h-14 rounded-full bg-white/5 border border-white/10 flex items-center justify-center text-gray-600">
                      <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
                        <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0A17.933 17.933 0 0112 21.75c-2.676 0-5.216-.584-7.499-1.632z"/>
                      </svg>
                    </div>
                  {/if}
                  <span class="text-[10px] text-gray-400 text-center leading-tight line-clamp-2">{actor.name}</span>
                  {#if actor.character}
                    <span class="text-[9px] text-gray-600 text-center leading-tight line-clamp-1">{actor.character}</span>
                  {/if}
                </div>
              {/each}
            </div>
          </div>
        {/if}

      </div>
    {/if}

    <!-- Releases -->
    <div class="mb-4 flex items-center justify-between flex-wrap gap-3">
      <h2 class="text-lg font-semibold text-white">
        Releases
        {#if loadingReleases}
          <svg class="inline w-4 h-4 animate-spin ml-2 text-gray-500" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
        {:else}
          <span class="text-sm font-normal text-gray-600 ml-2">{filteredReleases.length} / {releases.length}</span>
        {/if}
      </h2>
      {#if hasFilters}
        <button class="btn-ghost text-red-400 hover:text-red-300" on:click={resetFilters}>
          Effacer les filtres
        </button>
      {/if}
    </div>

    <!-- Filter bar -->
{#if releases.length > 0}
  <div class="flex flex-col gap-4 p-4 rounded-xl bg-surface-800 border border-white/5 mb-4">
    <div class="grid grid-cols-1 md:grid-cols-3 gap-4">
      <FilterBar label="Résolution"    options={RESOLUTIONS} bind:active={activeRes} />
      <FilterBar label="Source"        options={SOURCES}     bind:active={activeSrc} />
      <FilterBar label="Codec Vidéo"   options={CODECS}      bind:active={activeCodec} />
    </div>
    <div class="border-t border-white/5 pt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
      <FilterBar label="Dynamic Range" options={HDR}         bind:active={activeHdr} />
      <FilterBar label="Audio"         options={AUDIO_TYPE}  bind:active={activeAudio} />
      <FilterBar label="Canaux"        options={CHANNELS}    bind:active={activeChannels} />
    </div>
    <div class="border-t border-white/5 pt-4 grid grid-cols-1 md:grid-cols-3 gap-4">
      <FilterBar label="Langue"        options={LANGUAGES}   bind:active={activeLang} />
      <FilterBar label="3D"            options={TYPES_3D}    bind:active={activeType3d} />
      <div class="flex items-start gap-3">
        <span class="text-[10px] font-semibold text-gray-500 uppercase tracking-widest w-20 flex-shrink-0 pt-1.5">Année</span>
        <input
          type="number" min="1900" max="2099"
          placeholder="—"
          bind:value={filterYear}
          on:input={() => { filterYear = filterYear }}
          class="w-24 bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-sm text-gray-200
                 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500
                 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
        />
      </div>
    </div>
    {#if type === 'tv'}
    <div class="border-t border-white/5 pt-4 flex flex-col gap-4">
      <FilterBar label="Type release"  options={RELEASE_TYPES} bind:active={activeTypes} />
      <div class="flex items-center gap-6 flex-wrap">
        <span class="text-[10px] font-semibold text-gray-500 uppercase tracking-widest w-20 flex-shrink-0">Saison / Ép.</span>
        <div class="flex items-center gap-2">
          <label class="text-xs text-gray-500" for="filter-season">S</label>
          <input
            id="filter-season"
            type="number" min="1" max="99"
            placeholder="—"
            bind:value={filterSeason}
            on:input={() => { filterSeason = filterSeason }}
            class="w-16 bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-sm text-gray-200
                   focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500
                   [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
          />
          <label class="text-xs text-gray-500" for="filter-episode">E</label>
          <input
            id="filter-episode"
            type="number" min="1" max="999"
            placeholder="—"
            bind:value={filterEpisode}
            on:input={() => { filterEpisode = filterEpisode }}
            class="w-16 bg-white/5 border border-white/10 rounded-lg px-2 py-1 text-sm text-gray-200
                   focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500
                   [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
          />
        </div>
      </div>
    </div>
    {/if}
  </div>
{/if}

    <!-- Release list -->
    <div class="flex flex-col gap-2 pb-16">
      {#if !loadingReleases && filteredReleases.length === 0}
        <div class="text-center text-gray-600 py-16 text-sm">
          {releases.length === 0 ? 'Aucune release trouvée.' : 'Aucune release ne correspond aux filtres.'}
        </div>
      {:else}
        {#each filteredReleases as r (r.guid)}
          <ReleaseRow
            release={r}
            downloaded={downloaded.has(r.downloadUrl || r.magnetUrl || r.guid)}
            on:download={(e) => handleDownload(e.detail)}
          />
        {/each}
      {/if}
    </div>
  </div>
{/if}
