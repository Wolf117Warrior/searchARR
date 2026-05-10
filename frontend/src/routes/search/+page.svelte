<script lang="ts">
  import { onMount } from 'svelte'
  import { searchTMDB, searchByPerson, getGenres, type TMDBResult, type TMDBGenre, type PersonInfo } from '$lib/api'
  import MediaCard from '$lib/MediaCard.svelte'
  import DropdownFilter from '$lib/DropdownFilter.svelte'

  // ------------------------------------------------------------------ Modes
  // 'title' = recherche classique par titre
  // 'actor' = recherche par acteur/actrice
  let searchMode: 'title' | 'actor' = 'title'

  // ------------------------------------------------------------------ Filtres
  let query      = ''
  let filterYear: number | null = null

  let selType:  Set<string> = new Set()
  let selSort:  Set<string> = new Set()
  let selVote:  Set<string> = new Set()
  let selGenre: Set<string> = new Set()

  $: filterMediaType = selType.size  ? (selType.values().next().value as any) : null
  $: filterSortBy    = selSort.size  ? (selSort.values().next().value as any)  : null
  $: filterVoteMin   = selVote.size  ? parseFloat(selVote.values().next().value) : null
  $: filterGenreId   = selGenre.size ? parseInt(selGenre.values().next().value)  : null

  const TYPE_OPTIONS = [
    { value: 'movie',        label: 'Film'         },
    { value: 'tv',           label: 'Série'        },
    { value: 'animation',    label: 'Animé'        },
    { value: 'documentary',  label: 'Documentaire' },
  ]
  const SORT_OPTIONS = [
    { value: 'popularity',   label: 'Popularité'  },
    { value: 'vote_average', label: 'Note'        },
    { value: 'release_date', label: 'Date sortie' },
  ]
  const VOTE_OPTIONS = [
    { value: '6',   label: '★ 6+' },
    { value: '7',   label: '★ 7+' },
    { value: '7.5', label: '★ 7.5+' },
    { value: '8',   label: '★ 8+' },
  ]
  // En mode acteur : Type limité à Film / Série
  const TYPE_OPTIONS_ACTOR = [
    { value: 'movie', label: 'Film'  },
    { value: 'tv',    label: 'Série' },
  ]

  // ------------------------------------------------------------------ Genres
  let genres: TMDBGenre[] = []
  let loadingGenres = true
  $: GENRE_OPTIONS = genres.map(g => ({ value: String(g.id), label: g.name }))

  onMount(async () => {
    try { const d = await getGenres(); genres = d.genres }
    catch {}
    finally { loadingGenres = false }
  })

  // ------------------------------------------------------------------ Résultats
  let results:  TMDBResult[]  = []
  let loading   = false
  let error     = ''
  let searched  = false
  let total     = 0
  let person:   PersonInfo | null = null   // renseigné en mode acteur

  const handleSearch = async () => {
    if (!query.trim()) return
    loading  = true
    error    = ''
    searched = true
    person   = null
    try {
      if (searchMode === 'actor') {
        // En mode acteur genre_id non supporté (credits TMDB ne filtrent pas par genre côté API)
        const actorMediaType = filterMediaType === 'movie' || filterMediaType === 'tv'
          ? filterMediaType as 'movie' | 'tv'
          : null
        const data = await searchByPerson({
          query,
          media_type: actorMediaType,
          vote_min:   filterVoteMin,
          sort_by:    filterSortBy,
        })
        results = data.results
        total   = data.total
        person  = data.person
      } else {
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
      }
    } catch (e: any) {
      error   = e.message
      results = []
      total   = 0
    } finally {
      loading = false
    }
  }

  $: hasFilters = selType.size > 0 || selSort.size > 0 || selVote.size > 0 ||
                  selGenre.size > 0 || filterYear != null

  const resetFilters = () => {
    selType = new Set(); selSort = new Set()
    selVote = new Set(); selGenre = new Set()
    filterYear = null
    if (searched) handleSearch()
  }

  // Bascule de mode — remet à zéro la recherche en cours
  const switchMode = (mode: 'title' | 'actor') => {
    if (searchMode === mode) return
    searchMode = mode
    results  = []; total = 0; error = ''
    searched = false; person = null
    selType  = new Set()  // recharge les options adaptées
  }

  const handleSelect = (item: TMDBResult) => {
    window.open(
      `/details?id=${item.id}&type=${item.media_type}&title=${encodeURIComponent(item.title)}`,
      '_blank', 'noopener,noreferrer'
    )
  }
</script>

<svelte:head><title>Recherche avancée — searchARR</title></svelte:head>

<div class="max-w-7xl mx-auto px-4 sm:px-6 py-10">

  <!-- Header -->
  <div class="mb-6">
    <h1 class="text-2xl font-bold text-white mb-1">Recherche avancée</h1>
    <p class="text-sm text-gray-500">Filtrez par genre, note, type et année</p>
  </div>

  <!-- Toggle mode titre / acteur -->
  <div class="flex items-center gap-1 mb-5 p-1 rounded-xl w-fit"
       style="background:rgba(255,255,255,0.04);border:1px solid rgba(255,255,255,0.07)">
    <button
      type="button"
      class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
             {searchMode === 'title'
               ? 'bg-indigo-600 text-white shadow-md'
               : 'text-gray-400 hover:text-gray-200'}"
      on:click={() => switchMode('title')}
    >
      <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <circle cx="11" cy="11" r="7"/><path stroke-linecap="round" stroke-linejoin="round" d="M20 20l-3-3"/>
      </svg>
      Par titre
    </button>
    <button
      type="button"
      class="flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium transition-all
             {searchMode === 'actor'
               ? 'bg-indigo-600 text-white shadow-md'
               : 'text-gray-400 hover:text-gray-200'}"
      on:click={() => switchMode('actor')}
    >
      <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round"
          d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0"/>
      </svg>
      Par acteur
    </button>
  </div>

  <!-- Barre de recherche -->
  <form on:submit|preventDefault={handleSearch} class="flex gap-3 mb-5">
    <div class="relative flex-1">
      {#if searchMode === 'actor'}
        <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500"
          fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0"/>
        </svg>
      {:else}
        <svg class="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-500"
          fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="7"/><path stroke-linecap="round" stroke-linejoin="round" d="M20 20l-3-3"/>
        </svg>
      {/if}
      <input
        bind:value={query}
        type="text"
        placeholder={searchMode === 'actor' ? 'Nom de l\'acteur ou actrice…' : 'Titre du film ou de la série…'}
        class="w-full pl-10 pr-4 py-3 rounded-xl bg-white/5 border border-white/10 text-white
               placeholder-gray-500 text-sm focus:outline-none focus:border-indigo-500/60
               focus:bg-white/8 transition-all"
      />
    </div>
    <button type="submit" class="btn-primary px-6" disabled={loading || !query.trim()}>
      {#if loading}
        <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
        </svg>
      {:else}
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
          <circle cx="11" cy="11" r="7"/><path stroke-linecap="round" stroke-linejoin="round" d="M20 20l-3-3"/>
        </svg>
      {/if}
      Rechercher
    </button>
  </form>

  <!-- Barre de filtres -->
  <div class="flex flex-wrap items-center gap-2 mb-8">

    <DropdownFilter
      label="Type"
      options={searchMode === 'actor' ? TYPE_OPTIONS_ACTOR : TYPE_OPTIONS}
      bind:selected={selType}
      single
      on:change={() => { if (searched) handleSearch() }}
    />

    <DropdownFilter label="Trier par" options={SORT_OPTIONS} bind:selected={selSort} single
      on:change={() => { if (searched) handleSearch() }} />

    <DropdownFilter label="Note" options={VOTE_OPTIONS} bind:selected={selVote} single
      on:change={() => { if (searched) handleSearch() }} />

    <!-- Genre masqué en mode acteur (non filtrable via credits API) -->
    {#if searchMode === 'title'}
      <DropdownFilter label="Genre" options={GENRE_OPTIONS} bind:selected={selGenre} single
        on:change={() => { if (searched) handleSearch() }} />

      <input
        type="number"
        bind:value={filterYear}
        on:change={() => { if (searched) handleSearch() }}
        min="1900" max="2099" placeholder="Année"
        class="w-24 px-3 py-1.5 rounded-lg bg-white/5 border text-sm transition-all
               {filterYear ? 'border-indigo-500/50 text-indigo-300 bg-indigo-500/10' : 'border-white/10 text-gray-400 placeholder-gray-600'}
               focus:outline-none focus:border-indigo-500/60
               [appearance:textfield] [&::-webkit-inner-spin-button]:appearance-none"
      />
    {/if}

    {#if hasFilters}
      <button type="button"
        class="inline-flex items-center gap-1 px-2.5 py-1.5 rounded-lg text-xs text-gray-500
               hover:text-gray-300 transition-colors border border-white/5 hover:border-white/10"
        on:click={resetFilters}>
        <svg class="w-3 h-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
          <path stroke-linecap="round" stroke-linejoin="round" d="M6 18L18 6M6 6l12 12"/>
        </svg>
        Effacer
      </button>
    {/if}
  </div>

  <!-- Bandeau acteur trouvé -->
  {#if person && searched}
    <div class="flex items-center gap-4 mb-6 p-4 rounded-xl"
         style="background:rgba(99,102,241,0.08);border:1px solid rgba(99,102,241,0.2)">
      {#if person.profile_path}
        <img
          src="https://image.tmdb.org/t/p/w92{person.profile_path}"
          alt={person.name}
          class="w-12 h-12 rounded-full object-cover ring-2 ring-indigo-500/30"
          loading="lazy"
        />
      {:else}
        <div class="w-12 h-12 rounded-full bg-white/10 flex items-center justify-center flex-shrink-0">
          <svg class="w-6 h-6 text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.5">
            <path stroke-linecap="round" stroke-linejoin="round"
              d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0"/>
          </svg>
        </div>
      {/if}
      <div>
        <p class="text-sm font-semibold text-white">{person.name}</p>
        <p class="text-xs text-gray-500">
          {person.known_for_department === 'Acting' ? 'Acteur / Actrice' : person.known_for_department}
          · {total} titre{total > 1 ? 's' : ''}
        </p>
      </div>
    </div>
  {/if}

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
      <p class="text-sm">
        {searchMode === 'actor'
          ? 'Acteur introuvable ou aucun média avec affiche disponible'
          : 'Aucun résultat — essayez d\'élargir les filtres'}
      </p>
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
    <div class="flex flex-col items-center justify-center py-24 gap-3 text-gray-600">
      <svg class="w-14 h-14 text-gray-800" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1">
        {#if searchMode === 'actor'}
          <path stroke-linecap="round" stroke-linejoin="round"
            d="M15.75 6a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0zM4.501 20.118a7.5 7.5 0 0114.998 0"/>
        {:else}
          <circle cx="11" cy="11" r="7"/>
          <path stroke-linecap="round" stroke-linejoin="round" d="M20 20l-3-3M8 11h6M11 8v6"/>
        {/if}
      </svg>
      <p class="text-sm">
        {searchMode === 'actor'
          ? 'Entrez un nom d\'acteur pour voir sa filmographie'
          : 'Entrez un titre pour lancer la recherche'}
      </p>
    </div>
  {/if}

</div>
