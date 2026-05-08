<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import { poster, formatYear } from './utils'
  import type { TMDBResult } from './api'

  export let item: TMDBResult
  export let index: number = 0          

  const dispatch = createEventDispatcher<{ select: TMDBResult }>()

  $: img = poster(item.poster_path, 'w342')
  $: year = formatYear(item.release_date)
  $: isMovie = item.media_type === 'movie'
  $: delay = Math.min(index * 40, 400)
</script>

<button
  class="group relative flex flex-col rounded-xl overflow-hidden bg-surface-800
         ring-1 ring-white/5 card-hover card-enter cursor-pointer text-left w-full"
  style="animation-delay: {delay}ms"
  on:click={() => dispatch('select', item)}
  aria-label="{item.title} ({year})"
>
  <!-- Poster -->
  <div class="relative aspect-[2/3] w-full overflow-hidden bg-surface-700">
    {#if img}
      <img
        src={img}
        alt={item.title}
        class="absolute inset-0 w-full h-full object-cover transition-transform duration-500 group-hover:scale-105"
        loading="lazy"
      />
    {:else}
      <div class="absolute inset-0 flex items-center justify-center text-gray-600">
        <svg class="w-12 h-12" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1"
            d="M15 10l4.553-2.069A1 1 0 0121 8.82v6.36a1 1 0 01-1.447.894L15 14M3 8a2 2 0 012-2h10a2 2 0 012 2v8a2 2 0 01-2 2H5a2 2 0 01-2-2V8z" />
        </svg>
      </div>
    {/if}

    <!-- Type badge -->
    <span class="absolute top-2 left-2 badge {isMovie ? 'bg-blue-500/80 text-blue-100' : 'bg-purple-500/80 text-purple-100'}">
      {isMovie ? 'Film' : 'Série'}
    </span>

    <!-- Score -->
    {#if item.vote_average > 0}
      <span class="absolute top-2 right-2 badge bg-black/70 text-yellow-400">
        ★ {item.vote_average.toFixed(1)}
      </span>
    {/if}

    <!-- Gradient overlay -->
    <div class="absolute inset-0 bg-gradient-to-t from-surface-900 via-transparent to-transparent opacity-0 group-hover:opacity-100 transition-opacity duration-300"></div>
  </div>

  <!-- Info -->
  <div class="p-3 flex flex-col gap-1">
    <h3 class="text-sm font-semibold text-white leading-tight line-clamp-2" title={item.title}>
      {item.title}
    </h3>
    {#if year}
      <span class="text-xs text-gray-500">{year}</span>
    {/if}
  </div>
</button>
