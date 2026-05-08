<script lang="ts">
  import { onMount } from 'svelte'
  import { searchTMDB, getHomeRows, type TMDBResult } from '$lib/api'
  import MediaCard from '$lib/MediaCard.svelte'

  let query      = ''
  let results: TMDBResult[] = []
  let loading    = false
  let error      = ''
  let searched   = false

  // Filtres
  let filterYear:      number | null = null
  let filterMediaType: 'movie' | 'tv' | 'animation' | null = null

  const MEDIA_TYPES: { value: 'movie' | 'tv' | 'animation'; label: string }[] = [
    { value: 'movie',     label: 'Film'      },
    { value: 'tv',        label: 'Série'     },
    { value: 'animation', label: 'Animation' },
  ]

  const handleSearch = async () => {
    if (!query.trim()) return
    loading = true
    error   = ''
    searched = true
    try {
      const data = await searchTMDB({
        query,
        year:       filterYear,
        media_type: filterMediaType,
      })
      results = data.results
    } catch (e: any) {
      error   = e.message
      results = []
    } finally {
      loading = false
    }
  }

  // Re-lance la recherche si des filtres changent et qu'une recherche a déjà eu lieu
  const onFilterChange = () => { if (searched) handleSearch() }

  $: filterYear,      onFilterChange()
  $: filterMediaType, onFilterChange()

  // Données homepage — 4 rows
  let trendingMovies: TMDBResult[] = []
  let trendingTv:     TMDBResult[] = []
  let upcomingMovies: TMDBResult[] = []
  let upcomingTv:     TMDBResult[] = []
  let loadingHome = true

  onMount(async () => {
    try {
      const rows = await getHomeRows()
      trendingMovies = rows.trending_movies
      trendingTv     = rows.trending_tv
      upcomingMovies = rows.upcoming_movies
      upcomingTv     = rows.upcoming_tv
    } catch {}
    finally { loadingHome = false }
  })

  const handleSelect = (item: TMDBResult) => {
    window.open(
      `/details?id=${item.id}&type=${item.media_type}&title=${encodeURIComponent(item.title)}`,
      '_blank',
      'noopener,noreferrer'
    )
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

      <!-- Type média -->
      {#each MEDIA_TYPES as mt}
        <button
          type="button"
          class="filter-chip {filterMediaType === mt.value ? 'filter-chip-active' : 'filter-chip-inactive'}"
          on:click={() => { filterMediaType = filterMediaType === mt.value ? null : mt.value }}
        >{mt.label}</button>
      {/each}

      <!-- Séparateur -->
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

      <!-- Reset -->
      {#if filterMediaType !== null || filterYear !== null}
        <button
          type="button"
          class="text-xs text-gray-500 hover:text-gray-300 transition-colors underline underline-offset-2"
          on:click={() => { filterMediaType = null; filterYear = null }}
        >Effacer</button>
      {/if}
    </div>
  </div>

  <!-- Rangées homepage (visibles uniquement avant toute recherche) -->
  {#if !searched}
    {#if loadingHome}
      <!-- Skeleton 4 rows -->
      {#each Array(4) as _}
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
      {#each [
        { label: '🎥 Films tendance',       items: trendingMovies },
        { label: '📺 Séries tendance',      items: trendingTv     },
        { label: '🆕 Films à venir',         items: upcomingMovies },
        { label: '📆 Séries à venir',        items: upcomingTv     },
      ] as row}
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