<script lang="ts">
  import { onMount } from 'svelte'
  import { searchTMDB, getGenres, type TMDBResult, type TMDBGenre } from '$lib/api'
  import MediaCard from '$lib/MediaCard.svelte'

  // --- Filtres ---
  let query          = ''
  let filterYear:      number | null = null
  let filterMediaType: 'movie' | 'tv' | 'animation' | null = null
  let filterGenreId:   number | null = null
  let filterVoteMin:   number | null = null
  let filterSortBy:    'popularity' | 'vote_average' | 'release_date' | null = null

  const MEDIA_TYPES: { value: 'movie' | 'tv' | 'animation'; label: string }[] = [
    { value: 'movie',     label: 'Film'      },
    { value: 'tv',        label: 'Série'     },
    { value: 'animation', label: 'Animation' },
  ]

  const SORT_OPTIONS: { value: 'popularity' | 'vote_average' | 'release_date'; label: string }[] = [
    { value: 'popularity',    label: 'Popularité'  },
    { value: 'vote_average',  label: 'Note'        },
    { value: 'release_date',  label: 'Date sortie' },
  ]

  const VOTE_PRESETS = [6, 7, 7.5, 8]

  // --- Genres TMDB ---
  let genres: TMDBGenre[] = []
  let loadingGenres = true

  onMount(async () => {
    try {
      const data = await getGenres()
      genres = data.genres
    } catch {}
    finally { loadingGenres = false }
  })

  // --- Résultats ---
  let results: TMDBResult[] = []
  let loading   = false
  let error     = ''
  let searched  = false
  let total     = 0

  const handleSearch = async () => {
    if (!query.trim()) return
    loading  = true
    error    = ''
    searched = true
    try {
      const data = await searchTMDB({
        query,
        year:       filterYear,
        media_type: filterMediaType,
        genre_id:   filterGenreId,
        vote_min:   filterVoteMin,
        sort_by:    filterSortBy,
      })
      results = data.results
      total   = data.total
    } catch (e: any) {
      error   = e.message
      results = []
      total   = 0
    } finally {
      loading = false
    }
  }

  const hasFilters = () =>
    filterYear != null ||
    filterMediaType != null ||
    filterGenreId != null ||
    filterVoteMin != null ||
    filterSortBy != null

  const resetFilters = () => {
    filterYear       = null
    filterMediaType  = null
    filterGenreId    = null
    filterVoteMin    = null
    filterSortBy     = null
    if (searched) handleSearch()
  }

  const handleSelect = (item: TMDBResult) => {
    window.open(
      `/details?id=${item.id}&type=${item.media_type}&title=${encodeURIComponent(item.title)}`,
      '_blank',
      'noopener,noreferrer'
    )
  }
</script>

<svelte:head><title>Recherche avancée — searchARR</title></svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 py-10">

  <!-- Header page -->
  <div class="mb-8">
    <h1 class="text-2xl font-bold text-white mb-1">Recherche avancée</h1>
    <p class="text-sm text-gray-500">Filtrez par genre, note, type et année</p>
  </div>

  <!-- Barre de recherche -->
  <form on:submit|preventDefault={handleSearch} class="flex gap-3 mb-6">
    <div class="relative flex-1">
      <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="7"/><path stroke-linecap="round" stroke-linejoin="round" d="M20 20l-3-3"/>
      </svg>
      <input
        bind:value={query}
        type="text"
        placeholder="Titre du film ou de la série…"
        class="w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white placeholder-gray-500 text-sm focus:outline-none focus:border-indigo-500/60 focus:bg-white/8 transition-all"
      />
    </div>
    <button type="submit" class="btn-primary px-6" disabled={loading || !query.trim()}>
      {#if loading}
        <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/></svg>
      {:else}
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="7"/><path stroke-linecap="round" stroke-linejoin="round" d="M20 20l-3-3"/></svg>
      {/if}
      Rechercher
    </button>
  </form>

  <!-- Panneau filtres -->
  <div class="bg-white/3 border border-white/8 rounded-2xl p-5 mb-8 space-y-5">

    <!-- Ligne 1 : Type + Tri -->
    <div class="flex flex-wrap gap-4 items-center">
      <!-- Type -->
      <div class="flex flex-col gap-1.5">
        <span class="text-[10px] font-semibold uppercase tracking-widest text-gray-500">Type</span>
        <div class="flex gap-2">
          {#each MEDIA_TYPES as mt}
            <button
              type="button"
              class="filter-chip {filterMediaType === mt.value ? 'filter-chip-active' : 'filter-chip-inactive'}"
              on:click={() => {
                filterMediaType = filterMediaType === mt.value ? null : mt.value
                if (searched) handleSearch()
              }}
            >{mt.label}</button>
          {/each}
        </div>
      </div>

      <div class="w-px h-8 bg-white/8 hidden sm:block"></div>

      <!-- Tri -->
      <div class="flex flex-col gap-1.5">
        <span class="text-[10px] font-semibold uppercase tracking-widest text-gray-500">Trier par</span>
        <div class="flex gap-2">
          {#each SORT_OPTIONS as opt}
            <button
              type="button"
              class="filter-chip {filterSortBy === opt.value ? 'filter-chip-active' : 'filter-chip-inactive'}"
              on:click={() => {
                filterSortBy = filterSortBy === opt.value ? null : opt.value
                if (searched) handleSearch()
              }}
            >{opt.label}</button>
          {/each}
        </div>
      </div>
    </div>

    <!-- Ligne 2 : Note min + Année -->
    <div class="flex flex-wrap gap-4 items-center">
      <!-- Note min -->
      <div class="flex flex-col gap-1.5">
        <span class="text-[10px] font-semibold uppercase tracking-widest text-gray-500">Note minimum</span>
        <div class="flex gap-2 items-center">
          {#each VOTE_PRESETS as v}
            <button
              type="button"
              class="filter-chip {filterVoteMin === v ? 'filter-chip-active' : 'filter-chip-inactive'}"
              on:click={() => {
                filterVoteMin = filterVoteMin === v ? null : v
                if (searched) handleSearch()
              }}
            >★ {v}</button>
          {/each}
        </div>
      </div>

      <div class="w-px h-8 bg-white/8 hidden sm:block"></div>

      <!-- Année -->
      <div class="flex flex-col gap-1.5">
        <span class="text-[10px] font-semibold uppercase tracking-widest text-gray-500">Année</span>
        <input
          type="number"
          bind:value={filterYear}
          on:change={() => { if (searched) handleSearch() }}
          min="1900" max="2099" placeholder="ex: 2024"
          class="w-28 px-3 py-1.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm placeholder-gray-600 focus:outline-none focus:border-indigo-500/60 [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none"
        />
      </div>
    </div>

    <!-- Ligne 3 : Genres -->
    <div class="flex flex-col gap-1.5">
      <span class="text-[10px] font-semibold uppercase tracking-widest text-gray-500">Genre</span>
      {#if loadingGenres}
        <div class="flex gap-2">
          {#each Array(8) as _}
            <div class="skeleton h-7 w-16 rounded-lg"></div>
          {/each}
        </div>
      {:else}
        <div class="flex flex-wrap gap-2">
          {#each genres as g}
            <button
              type="button"
              class="filter-chip {filterGenreId === g.id ? 'filter-chip-active' : 'filter-chip-inactive'}"
              on:click={() => {
                filterGenreId = filterGenreId === g.id ? null : g.id
                if (searched) handleSearch()
              }}
            >{g.name}</button>
          {/each}
        </div>
      {/if}
    </div>

    <!-- Reset -->
    {#if hasFilters()}
      <div class="flex justify-end pt-1">
        <button type="button" class="btn-ghost text-xs" on:click={resetFilters}>
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/></svg>
          Effacer les filtres
        </button>
      </div>
    {/if}
  </div>

  <!-- Résultats -->
  {#if error}
    <div class="text-center text-red-400 py-12">{error}</div>

  {:else if loading}
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {#each Array(10) as _}
        <div class="skeleton aspect-[2/3] rounded-xl"></div>
      {/each}
    </div>

  {:else if searched && results.length === 0}
    <div class="flex flex-col items-center justify-center py-24 gap-4 text-gray-500">
      <svg class="w-12 h-12 text-gray-700" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.2">
        <circle cx="11" cy="11" r="7"/><path stroke-linecap="round" stroke-linejoin="round" d="M20 20l-3-3"/>
      </svg>
      <p class="text-sm">Aucun résultat — essayez d'élargir les filtres</p>
    </div>

  {:else if searched}
    <div class="flex items-center justify-between mb-4">
      <span class="text-xs text-gray-500">{total} résultat{total > 1 ? 's' : ''}</span>
    </div>
    <div class="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 gap-4">
      {#each results as item, i}
        <div class="card-enter" style="animation-delay: {i * 40}ms">
          <MediaCard {item} on:select={(e) => handleSelect(e.detail)} />
        </div>
      {/each}
    </div>

  {:else}
    <!-- État initial -->
    <div class="flex flex-col items-center justify-center py-24 gap-3 text-gray-600">
      <svg class="w-14 h-14 text-gray-800" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
        <circle cx="11" cy="11" r="7"/>
        <path stroke-linecap="round" stroke-linejoin="round" d="M20 20l-3-3M8 11h6M11 8v6"/>
      </svg>
      <p class="text-sm">Entrez un titre pour lancer la recherche</p>
    </div>
  {/if}

</div>
