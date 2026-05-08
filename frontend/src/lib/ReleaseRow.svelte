<script lang="ts">
  import { createEventDispatcher } from 'svelte'
  import { formatBytes, extractMeta } from './utils'
  import type { Release } from './api'

  export let release: Release
  export let downloaded = false

  const dispatch = createEventDispatcher<{ download: string }>()

  $: meta = extractMeta(release.title)
  $: targetUrl = release.downloadUrl || release.magnetUrl || release.guid

  const resolutionColor: Record<string, string> = {
    '2160P': 'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    '4K':    'bg-yellow-500/20 text-yellow-300 border-yellow-500/30',
    '1080P': 'bg-blue-500/20 text-blue-300 border-blue-500/30',
    '720P':  'bg-green-500/20 text-green-300 border-green-500/30',
    'SD':    'bg-gray-500/20 text-gray-400 border-gray-500/30',
  }
  $: resClass = resolutionColor[meta.resolution] ?? resolutionColor['SD']
</script>

<div class="flex items-center gap-3 px-4 py-3 rounded-xl bg-surface-800 ring-1 ring-white/5
            hover:ring-white/10 hover:bg-surface-700 transition-all duration-150 group">

  <!-- Seeders indicator -->
<div class="flex-shrink-0 w-1.5 h-10 rounded-full {release.seeders > 10 ? 'bg-green-500' : release.seeders > 0 ? 'bg-yellow-500' : 'bg-red-500'}"></div>
  <!-- Title + badges -->
  <div class="flex-1 min-w-0">
    <p class="text-sm text-gray-200 truncate" title={release.title}>{release.title}</p>
    <div class="flex flex-wrap gap-1.5 mt-1.5">
      <span class="badge border {resClass}">{meta.resolution}</span>
      {#if meta.source}<span class="badge bg-white/5 text-gray-400 border border-white/10">{meta.source}</span>{/if}
      {#if meta.codec}<span class="badge bg-white/5 text-gray-400 border border-white/10">{meta.codec}</span>{/if}
      {#if meta.hdr}<span class="badge bg-orange-500/20 text-orange-300 border border-orange-500/30">{meta.hdr}</span>{/if}
      {#if meta.language}<span class="badge bg-indigo-500/20 text-indigo-300 border border-indigo-500/30">{meta.language}</span>{/if}
      {#if meta.audio}<span class="badge bg-white/5 text-gray-500 border border-white/10">{meta.audio}</span>{/if}
    </div>
  </div>

  <!-- Meta numbers -->
  <div class="flex-shrink-0 flex flex-col items-end gap-1 text-xs text-gray-500">
    <span class="text-gray-400">{formatBytes(release.size)}</span>
<span class="text-[10px] font-medium text-blue-400 group-hover:text-blue-300 transition-colors">
  {release.indexer || '?'}</span>  
</div>

  <!-- Seeders / Leechers -->
  <div class="flex-shrink-0 flex flex-col items-center gap-0.5 w-10 text-xs font-mono">
    <span class="text-green-400 font-semibold">{release.seeders ?? 0}</span>
    <span class="text-red-400">{release.leechers ?? 0}</span>
  </div>

  <!-- Download button -->
  <button
    class="flex-shrink-0 p-2.5 rounded-xl transition-all duration-200
           {downloaded
             ? 'bg-green-500/20 text-green-400 ring-1 ring-green-500/30'
             : 'bg-white/5 text-gray-400 hover:bg-indigo-600 hover:text-white ring-1 ring-white/10'}"
    on:click={() => !downloaded && dispatch('download', targetUrl)}
    title={downloaded ? 'Déjà envoyé' : 'Envoyer à qBittorrent'}
    disabled={downloaded}
  >
    {#if downloaded}
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
        <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7" />
      </svg>
    {:else}
      <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
        <path stroke-linecap="round" stroke-linejoin="round" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
      </svg>
    {/if}
  </button>
</div>
