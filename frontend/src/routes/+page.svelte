<script lang="ts">
  import { onMount } from 'svelte'
  import { searchTMDB, getHomeRows, discoverByGenre, type TMDBResult } from '$lib/api'
  import MediaCard from '$lib/MediaCard.svelte'

  let query      = ''
  let results: TMDBResult[] = []
  let loading    = false
  let error      = ''
  let searched   = false

  // Filtres
  let filterYear:      number | null = null
  let filterMediaType: 'movie' | 'tv' | 'anim-movie' | 'anim-tv' | 'documentary' | null = null

  const MEDIA_TYPES: { value: typeof filterMediaType; label: string }[] = [
    { value: 'movie',       label: 'Film'          },
    { value: 'tv',          label: 'Série'         },
    { value: 'anim-movie',  label: 'Film animé'    },
    { value: 'anim-tv',     label: 'Série animée'  },
    { value: 'documentary', label: 'Documentaire'  },
  ]

  // Traduit les pseudo-types vers ce que l'API searchTMDB comprend
  const apiMediaType = (f: typeof filterMediaType) => {
    if (f === 'anim-movie') return 'animation'
    if (f === 'anim-tv')    return 'animation'
    return f as 'movie' | 'tv' | 'documentary' | null
  }

  const handleSearch = async () => {
    if (!query.trim()) return
    loading  = true
    error    = ''
    searched = true
    try {
      const data = await searchTMDB({
        query,
        year:       filterYear,
        media_type: apiMediaType(filterMediaType),
      })
      results = data.results
    } catch (e: any) {
      error   = e.message
      results = []
    } finally {
      loading = false
    }
  }

  const onFilterChange = () => { if (searched) handleSearch() }

  let _initDone = false
  onMount(() => { _initDone = true })
  $: if (_initDone && (filterYear, filterMediaType, true)) onFilterChange()

  // ------------------------------------------------------------------ Home rows
  // Rows de base (trending + upcoming)
  let _trendingMovies: TMDBResult[] = []
  let _trendingTv:     TMDBResult[] = []
  let _upcomingMovies: TMDBResult[] = []
  let _upcomingTv:     TMDBResult[] = []
  let loadingHome = true

  // Rows discover — chargées à la demande
  let _discoverDocMovie:  TMDBResult[] = []
  let _discoverDocTv:     TMDBResult[] = []
  let loadingDiscover = false
  let _docLoaded = false

  onMount(async () => {
    try {
      const rows = await getHomeRows()
      _trendingMovies = rows.trending_movies
      _trendingTv     = rows.trending_tv
      _upcomingMovies = rows.upcoming_movies
      _upcomingTv     = rows.upcoming_tv
    } catch {}
    finally { loadingHome = false }
  })

  // Chargement différé des rows discover
  // Films animés : tendances + à venir
  let _animMovieTrending: TMDBResult[] = []
  let _animMovieUpcoming: TMDBResult[] = []
  let _animMovieLoaded = false
  // Séries animées : tendances + à venir
  let _animTvTrending: TMDBResult[] = []
  let _animTvUpcoming: TMDBResult[] = []
  let _animTvLoaded = false

  const loadAnimMovieRows = async () => {
    if (_animMovieLoaded) return
    loadingDiscover = true
    try {
      const [trending, upcoming] = await Promise.all([
        discoverByGenre(16, 'movie', 'trending'),
        discoverByGenre(16, 'movie', 'upcoming'),
      ])
      _animMovieTrending = trending.results
      _animMovieUpcoming = upcoming.results
      _animMovieLoaded   = true
    } catch {}
    finally { loadingDiscover = false }
  }

  const loadAnimTvRows = async () => {
    if (_animTvLoaded) return
    loadingDiscover = true
    try {
      const [trending, upcoming] = await Promise.all([
        discoverByGenre(16, 'tv', 'trending'),
        discoverByGenre(16, 'tv', 'upcoming'),
      ])
      _animTvTrending = trending.results
      _animTvUpcoming = upcoming.results
      _animTvLoaded   = true
    } catch {}
    finally { loadingDiscover = false }
  }

  const loadDocRows = async () => {
    if (_docLoaded) return
    loadingDiscover = true
    try {
      const [movies, tv] = await Promise.all([
        discoverByGenre(99, 'movie'),
        discoverByGenre(99, 'tv'),
      ])
      _discoverDocMovie = movies.results
      _discoverDocTv    = tv.results
      _docLoaded = true
    } catch {}
    finally { loadingDiscover = false }
  }

  // Déclenchement automatique au changement de filtre
  $: if (_initDone && filterMediaType === 'anim-movie')   loadAnimMovieRows()
  $: if (_initDone && filterMediaType === 'anim-tv')      loadAnimTvRows()
  $: if (_initDone && filterMediaType === 'documentary')  loadDocRows()

  // Rows affichées selon le filtre actif
  $: homeRows = (() => {
    if (filterMediaType === 'anim-movie') {
      return [
        { label: '🎬 Films animés — Tendances', items: _animMovieTrending },
        { label: '🆕 Films animés — À venir',   items: _animMovieUpcoming },
      ]
    }
    if (filterMediaType === 'anim-tv') {
      return [
        { label: '📺 Séries animées — Tendances', items: _animTvTrending },
        { label: '📆 Séries animées — À venir',   items: _animTvUpcoming },
      ]
    }
    if (filterMediaType === 'documentary') {
      return [
        { label: '🎥 Documentaires — Films',  items: _discoverDocMovie },
        { label: '📺 Documentaires — Séries', items: _discoverDocTv    },
      ]
    }
    if (filterMediaType === 'movie') {
      return [
        { label: '🎥 Films tendance', items: _trendingMovies },
        { label: '🆕 Films à venir',  items: _upcomingMovies },
      ]
    }
    if (filterMediaType === 'tv') {
      return [
        { label: '📺 Séries tendance', items: _trendingTv },
        { label: '📆 Séries à venir',  items: _upcomingTv },
      ]
    }
    // Aucun filtre — tout afficher
    return [
      { label: '🎥 Films tendance',  items: _trendingMovies },
      { label: '📺 Séries tendance', items: _trendingTv     },
      { label: '🆕 Films à venir',   items: _upcomingMovies },
      { label: '📆 Séries à venir',  items: _upcomingTv    },
    ]
  })()

  const handleSelect = (item: TMDBResult) => {
    window.open(`/details?id=${item.id}&type=${item.media_type}&title=${encodeURIComponent(item.title)}`, '_blank', 'noopener,noreferrer')
  }
</script>

<svelte:head><title>searchARR</title></svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 py-10">

  <!-- Hero search -->
  <div class="text-center mb-10">
    <h1 class="text-3xl font-bold text-white mb-2">Trouvez votre prochain média</h1>
    <p class="text-gray-500 text-sm mb-8">Recherchez un film ou une série pour voir les releases disponibles</p>

    <form on:submit|preventDefault={handleSearch} class="flex gap-3 max-w-xl mx-auto">
      <div class="relative flex-1">
        <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500"
          fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="7"/><path stroke-linecap="round" d="M20 20l-3-3"/>
        </svg>
        <input
          bind:value={query}
          type="text"
          placeholder="Avatar, Breaking Bad..."
          class="w-full bg-surface-800 border border-white/10 rounded-xl py-3 pl-10 pr-4
                 text-sm text-white placeholder-gray-500
                 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500
                 transition-all"
        />
      </div>
      <button type="submit" class="btn-primary px-6" disabled={loading}>
        {#if loading}
          <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
          </svg>
        {:else}
          Rechercher
        {/if}
      </button>
    </form>

    <!-- Filtres de recherche -->
    <div class="flex items-center justify-center gap-3 mt-4 flex-wrap">

      {#each MEDIA_TYPES as mt}
        <button
          type="button"
          class="filter-chip {filterMediaType === mt.value ? 'filter-chip-active' : 'filter-chip-inactive'}"
          on:click={() => { filterMediaType = filterMediaType === mt.value ? null : mt.value }}
        >{mt.label}</button>
      {/each}

      <span class="text-white/10 text-lg select-none">|</span>

      <!-- Année -->
      <div class="relative flex items-center">
        <span class="absolute left-2.5 text-xs text-gray-500 pointer-events-none select-none">Année</span>
        <input
          type="number"
          min="1900" max="2099"
          placeholder="—"
          bind:value={filterYear}
          on:input={() => { filterYear = filterYear }}
          class="w-32 pl-14 pr-2 py-1.5 bg-white/5 border border-white/10 rounded-lg text-sm text-gray-200
                 focus:outline-none focus:ring-1 focus:ring-indigo-500 focus:border-indigo-500
                 [appearance:textfield] [&::-webkit-outer-spin-button]:appearance-none [&::-webkit-inner-spin-button]:appearance-none"
        />
      </div>

      {#if filterMediaType !== null || filterYear !== null}
        <button
          type="button"
          class="text-xs text-gray-500 hover:text-gray-300 transition-colors underline underline-offset-2"
          on:click={() => { filterMediaType = null; filterYear = null }}
        >Effacer</button>
      {/if}
    </div>
  </div>

  <!-- Rangées homepage -->
  {#if !searched}

    {#if loadingHome || loadingDiscover}
      {#each Array(filterMediaType === 'animation' || filterMediaType === 'documentary' ? 2 : 4) as _}
        <div class="mb-8">
          <div class="w-40 h-4 rounded skeleton mb-3"></div>
          <div class="flex gap-3 overflow-x-hidden">
            {#each Array(8) as __}
              <div class="flex-shrink-0 w-[130px] h-[195px] rounded-xl skeleton"></div>
            {/each}
          </div>
        </div>
      {/each}

    {:else}
      {#each homeRows as row}
        {#if row.items.length > 0}
          <div class="mb-8">
            <h2 class="text-sm font-bold text-white mb-3">{row.label}</h2>
            <div class="flex gap-3 overflow-x-auto pb-2
                        scrollbar-thin scrollbar-thumb-white/10 scrollbar-track-transparent
                        scroll-smooth snap-x snap-mandatory">
              {#each row.items as item, i (item.id)}
                <div class="flex-shrink-0 snap-start w-[130px]">
                  <MediaCard {item} index={i} on:select={(e) => handleSelect(e.detail)} />
                </div>
              {/each}
            </div>
          </div>
        {/if}
      {/each}
    {/if}

  {/if}

  <!-- Error -->
  {#if error}
    <div class="text-center text-red-400 text-sm py-10">{error}</div>
  {/if}

  <!-- Skeleton loader -->
  {#if loading}
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
      {#each Array(12) as _}
        <div class="flex flex-col rounded-xl overflow-hidden ring-1 ring-white/5" style="background:#13151c">
          <div class="aspect-[2/3] w-full skeleton"></div>
          <div class="p-3 flex flex-col gap-2">
            <div class="skeleton skeleton-text"></div>
            <div class="skeleton skeleton-text" style="width:60%"></div>
          </div>
        </div>
      {/each}
    </div>

  <!-- Results grid -->
  {:else if results.length > 0}
    <p class="text-xs text-gray-600 mb-4">{results.length} résultat{results.length > 1 ? 's' : ''}</p>
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 gap-4">
    {#each results as item, i (item.id)}
      <MediaCard {item} index={i} on:select={(e) => handleSelect(e.detail)} />
    {/each}
    </div>

  {:else if searched && !loading && !error}
    <div class="text-center text-gray-600 py-20">
      <svg class="w-12 h-12 mx-auto mb-4 opacity-30" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <circle cx="11" cy="11" r="7"/><path stroke-linecap="round" d="M20 20l-3-3"/>
      </svg>
      <p class="text-sm">Aucun résultat pour « {query} »</p>
    </div>
  {/if}

</div>
