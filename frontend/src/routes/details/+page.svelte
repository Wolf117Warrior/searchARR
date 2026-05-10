<script lang="ts">
  import { page } from '$app/stores'
  import { onMount, onDestroy } from 'svelte'
  import { getTMDBDetails, searchReleases, downloadTorrent, monitorMedia,
           getRadarrProfiles, getSonarrProfiles, getMonitorStatus,
           type Release, type QualityProfile, type MonitorStatusResult } from '$lib/api'
  import { backdrop, poster, formatYear, extractMeta,
           FILTER_RESOLUTION, FILTER_SOURCE, FILTER_CODEC,
           FILTER_HDR, FILTER_AUDIO, FILTER_CHANNELS, FILTER_LANG,
           type FilterOption } from '$lib/utils'
  import ReleaseRow from '$lib/ReleaseRow.svelte'
  import FilterBar from '$lib/FilterBar.svelte'
  import { detectReleaseType, type ReleaseType } from '$lib/api'

  const RELEASE_TYPES: ReleaseType[] = ['Film', 'Intégrale', 'Saison', 'Épisode']
  let activeTypes = new Set<ReleaseType>()


  // Fermeture dropdown surveillance au clic extérieur
  const closeDropdown = (e: MouseEvent) => {
    if (showDropdown && !(e.target as HTMLElement).closest('[data-monitor-dropdown]')) {
      showDropdown = false
    }
  }

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
  let triggerEl: HTMLButtonElement
  let dropX = 0
  let dropY = 0

  // Statut de surveillance
  let monitorInfo: MonitorStatusResult | null = null
  let loadingMonitorInfo = true

  // Filtres
  let activeRes      = new Set<string>()
  let activeSrc      = new Set<string>()
  let activeLang     = new Set<string>()
  let activeCodec    = new Set<string>()
  let activeHdr      = new Set<string>()
  let activeAudio    = new Set<string>()
  let activeChannels = new Set<string>()
  let activeIndexer  = new Set<string>()

  // Filtres saison / épisode (séries uniquement)
  let filterSeason:  number | null = null
  let filterEpisode: number | null = null

  // Filtre année (tous médias)
  let filterYear: number | null = null

  // Indexeurs dynamiques (calculés depuis les releases)
  $: indexerOptions = [...new Set(releases.map(r => r.indexer).filter(Boolean))]
    .sort()
    .map(i => ({ label: i, value: i, aliases: [i] } as FilterOption))

  // Helper matching : la valeur normalisée de la release est-elle dans les aliases des filtres actifs ?
  const matchesFilter = (active: Set<string>, options: FilterOption[], metaValue: string): boolean => {
    if (active.size === 0) return true
    for (const val of active) {
      const opt = options.find(o => o.value === val)
      if (opt && opt.aliases.includes(metaValue)) return true
    }
    return false
  }

  onDestroy(() => document.removeEventListener('click', closeDropdown, true))

  onMount(async () => {
    document.addEventListener('click', closeDropdown, true)
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
    if (!showDropdown && triggerEl) {
      const rect = triggerEl.getBoundingClientRect()
      dropX = rect.left
      dropY = rect.bottom + 6
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
  if (!matchesFilter(activeRes,      FILTER_RESOLUTION, m.resolution)) return false
  if (!matchesFilter(activeSrc,      FILTER_SOURCE,     m.source))     return false
  if (!matchesFilter(activeCodec,    FILTER_CODEC,      m.codec))      return false
  if (!matchesFilter(activeHdr,      FILTER_HDR,        m.hdr))        return false
  if (!matchesFilter(activeAudio,    FILTER_AUDIO,      m.audio))      return false
  if (!matchesFilter(activeChannels, FILTER_CHANNELS,   m.channels))   return false
  if (!matchesFilter(activeLang,     FILTER_LANG,       m.language))   return false
  if (activeIndexer.size > 0 && !activeIndexer.has(r.indexer))         return false
  if (activeTypes.size   > 0 && !activeTypes.has(detectReleaseType(r.title))) return false
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
                 activeHdr, activeAudio, activeChannels, activeIndexer, activeTypes]
  .some(s => s.size > 0) || filterSeason != null || filterEpisode != null || filterYear != null

const resetFilters = () => {
  activeRes = new Set(); activeSrc = new Set()
  activeLang = new Set(); activeCodec = new Set()
  activeHdr = new Set(); activeAudio = new Set()
  activeChannels = new Set(); activeIndexer = new Set()
  activeTypes = new Set()
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
        <a
          href="https://www.themoviedb.org/{type}/{id}"
          target="_blank"
          rel="noopener noreferrer"
          class="inline-flex items-center gap-1.5 text-xs text-gray-500 hover:text-[#01d277] transition-colors w-fit"
          title="Voir la fiche TMDB"
        >
          <svg class="w-3.5 h-3.5 opacity-70" viewBox="0 0 24 24" fill="currentColor">
            <path d="M11 3a1 1 0 100 2h2.586l-6.293 6.293a1 1 0 101.414 1.414L15 6.414V9a1 1 0 102 0V4a1 1 0 00-1-1h-5z"/>
            <path d="M5 5a2 2 0 00-2 2v8a2 2 0 002 2h8a2 2 0 002-2v-3a1 1 0 10-2 0v3H5V7h3a1 1 0 000-2H5z"/>
          </svg>
          Voir sur TMDB
        </a>
        {#if details.overview}
          <p class="text-sm text-gray-400 leading-relaxed max-w-2xl line-clamp-3">{details.overview}</p>
        {/if}

        <!-- Monitor button + dropdown profil -->
        <div class="mt-1 relative" data-monitor-dropdown style="isolation: isolate; z-index: 100;">

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
                bind:this={triggerEl}
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

            <!-- Dropdown liste profils (fixed pour échapper à tout overflow parent) -->
            {#if showDropdown && profiles.length > 0}
              <div
                style="position:fixed; top:{dropY}px; left:{dropX}px; z-index:9999; min-width:180px;"
                class="bg-[#1a1d27] border border-white/10 rounded-xl shadow-2xl py-1 animate-in"
              >
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
  <div class="flex flex-wrap items-center gap-2 mb-4">

    <FilterBar label="Résolution" options={FILTER_RESOLUTION} bind:active={activeRes} />
    <FilterBar label="Source"     options={FILTER_SOURCE}     bind:active={activeSrc} />
    <FilterBar label="Codec"      options={FILTER_CODEC}      bind:active={activeCodec} />
    <FilterBar label="HDR"        options={FILTER_HDR}        bind:active={activeHdr} />
    <FilterBar label="Audio"      options={FILTER_AUDIO}      bind:active={activeAudio} />
    <FilterBar label="Canaux"     options={FILTER_CHANNELS}   bind:active={activeChannels} />
    <FilterBar label="Langue"     options={FILTER_LANG}       bind:active={activeLang} />
    {#if indexerOptions.length > 1}
      <FilterBar label="Indexeur" options={indexerOptions}    bind:active={activeIndexer} />
    {/if}

    {#if type === 'tv'}
      <FilterBar label="Type"     options={RELEASE_TYPES.map(t => ({ label: t, value: t, aliases: [t] }))} bind:active={activeTypes} />

      <!-- Saison / Épisode -->
      <div class="flex items-center gap-1.5">
        <span class="text-xs text-gray-500">S</span>
        <input type="number" min="1" max="99" placeholder="—" bind:value={filterSeason}
          class="w-12 px-2 py-1.5 rounded-lg bg-white/5 border border-white/10 text-sm text-gray-300
                 focus:outline-none focus:border-indigo-500/60
                 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none" />
        <span class="text-xs text-gray-500">E</span>
        <input type="number" min="1" max="999" placeholder="—" bind:value={filterEpisode}
          class="w-12 px-2 py-1.5 rounded-lg bg-white/5 border border-white/10 text-sm text-gray-300
                 focus:outline-none focus:border-indigo-500/60
                 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none" />
      </div>
    {/if}

    <!-- Année -->
    <input type="number" min="1900" max="2099" placeholder="Année" bind:value={filterYear}
      class="w-20 px-2 py-1.5 rounded-lg bg-white/5 border text-sm transition-all
             {filterYear ? 'border-indigo-500/50 text-indigo-300 bg-indigo-500/10' : 'border-white/10 text-gray-400 placeholder-gray-600'}
             focus:outline-none focus:border-indigo-500/60
             [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none" />

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
