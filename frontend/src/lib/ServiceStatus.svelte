<script lang="ts">
  import { onMount, onDestroy } from 'svelte'

  interface Service { name: string; online: boolean; ms: number | null }

  let services: Service[] = []
  let loading = true
  let showTooltip = false
  let interval: ReturnType<typeof setInterval>

  const ICONS: Record<string, string> = {
    Radarr:   'R',
    Sonarr:   'S',
    Prowlarr: 'P',
    qBit:     'Q',
  }

  const fetchStatus = async () => {
    try {
      const r = await fetch('/api/services/status')
      if (r.ok) {
        const data = await r.json()
        services = data.services
      }
    } catch {}
    finally { loading = false }
  }

  onMount(() => {
    fetchStatus()
    // Rafraîchissement toutes les 60s
    interval = setInterval(fetchStatus, 60_000)
  })

  onDestroy(() => clearInterval(interval))

  $: allOnline  = services.length > 0 && services.every(s => s.online)
  $: anyOffline = services.some(s => !s.online)
  $: dotColor   = loading
    ? 'bg-gray-600'
    : anyOffline
      ? 'bg-red-500'
      : allOnline
        ? 'bg-emerald-500'
        : 'bg-gray-600'
</script>

<!-- Dot indicateur global -->
<div class="relative flex items-center">
  <button
    class="flex items-center gap-1.5 px-2 py-1 rounded-lg hover:bg-white/5 transition-colors"
    aria-label="Statut des services"
    on:click={() => showTooltip = !showTooltip}
    on:blur={() => setTimeout(() => showTooltip = false, 150)}
  >
    <!-- Dot avec pulse si tout est OK -->
    <span class="relative flex h-2 w-2">
      {#if !loading && allOnline}
        <span class="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-50"></span>
      {/if}
      <span class="relative inline-flex h-2 w-2 rounded-full {dotColor}"></span>
    </span>
    <span class="text-xs text-gray-500 hidden sm:block">
      {#if loading}
        …
      {:else if anyOffline}
        {services.filter(s => !s.online).length} hors ligne
      {:else}
        OK
      {/if}
    </span>
  </button>

  <!-- Tooltip dropdown -->
  {#if showTooltip && services.length > 0}
    <div class="absolute right-0 top-full mt-2 z-50
                bg-[#13151c] border border-white/10 rounded-xl shadow-2xl
                py-2 min-w-[200px]">
      <div class="px-3 pb-1.5 mb-1 border-b border-white/5">
        <span class="text-[10px] font-semibold text-gray-500 uppercase tracking-widest">Stack</span><span class="text-[10px] font-semibold text-indigo-400 uppercase tracking-widest">ARR</span>
      </div>
      {#each services as svc}
        <div class="flex items-center justify-between px-3 py-1.5">
          <div class="flex items-center gap-2">
            <!-- Dot par service -->
            <span class="h-1.5 w-1.5 rounded-full flex-shrink-0
                         {svc.online ? 'bg-emerald-400' : 'bg-red-400'}"></span>
            <span class="text-xs font-medium {svc.online ? 'text-gray-200' : 'text-gray-500'}">
              {svc.name}
            </span>
          </div>
          <div class="flex items-center gap-1.5">
            {#if svc.online && svc.ms !== null}
              <span class="text-[10px] tabular-nums
                           {svc.ms < 100 ? 'text-emerald-500' : svc.ms < 300 ? 'text-yellow-500' : 'text-red-400'}">
                {svc.ms}ms
              </span>
            {:else if !svc.online}
              <span class="text-[10px] text-red-400">offline</span>
            {/if}
          </div>
        </div>
      {/each}

      <!-- Refresh manuel -->
      <div class="px-3 pt-1.5 mt-1 border-t border-white/5">
        <button
          class="text-[10px] text-gray-600 hover:text-gray-400 transition-colors"
          on:click={() => { loading = true; fetchStatus() }}
        >
          ↻ Rafraîchir
        </button>
      </div>
    </div>
  {/if}
</div>
