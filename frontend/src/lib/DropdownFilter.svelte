<script lang="ts">
  import { onDestroy } from 'svelte'

  export let label: string
  export let options: { value: string; label: string }[]
  export let selected: Set<string> = new Set()
  export let single = false          // true = sélection unique
  export let placeholder = ''       // texte si rien de sélectionné

  let open = false
  let btnEl: HTMLButtonElement
  let dropX = 0
  let dropY = 0

  $: activeCount = selected.size
  $: btnLabel = (() => {
    if (activeCount === 0) return placeholder || label
    if (single) return options.find(o => selected.has(o.value))?.label ?? label
    return `${label} (${activeCount})`
  })()

  const toggle = (val: string) => {
    const next = new Set(selected)
    if (single) {
      if (next.has(val)) { next.clear() } else { next.clear(); next.add(val) }
    } else {
      next.has(val) ? next.delete(val) : next.add(val)
    }
    selected = next
  }

  const openMenu = () => {
    if (!open && btnEl) {
      const r = btnEl.getBoundingClientRect()
      dropX = r.left
      dropY = r.bottom + 4
    }
    open = !open
  }

  const handleOutside = (e: MouseEvent) => {
    if (open && !(e.target as HTMLElement).closest('[data-dd-filter]')) open = false
  }

  // Recalcule position au scroll/resize pour éviter le décalage
  const reposition = () => {
    if (open && btnEl) {
      const r = btnEl.getBoundingClientRect()
      dropX = r.left
      dropY = r.bottom + 4
    }
  }

  import { onMount } from 'svelte'
  onMount(() => {
    document.addEventListener('click', handleOutside, true)
    window.addEventListener('scroll', reposition, true)
    window.addEventListener('resize', reposition)
  })
  onDestroy(() => {
    document.removeEventListener('click', handleOutside, true)
    window.removeEventListener('scroll', reposition, true)
    window.removeEventListener('resize', reposition)
  })
</script>

<div data-dd-filter class="relative inline-block">
  <button
    bind:this={btnEl}
    type="button"
    on:click|stopPropagation={openMenu}
    class="inline-flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-all
           border {activeCount > 0
             ? 'bg-indigo-500/20 border-indigo-500/50 text-indigo-300'
             : 'bg-white/5 border-white/10 text-gray-400 hover:border-white/20 hover:text-gray-200'}"
  >
    <span class="max-w-[120px] truncate">{btnLabel}</span>
    <svg class="w-3 h-3 flex-shrink-0 transition-transform {open ? 'rotate-180' : ''}"
      fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2.5">
      <path stroke-linecap="round" stroke-linejoin="round" d="M19 9l-7 7-7-7"/>
    </svg>
  </button>
</div>

<!-- Dropdown portal (fixed) -->
{#if open && options.length > 0}
  <div
    style="position:fixed; top:{dropY}px; left:{dropX}px; z-index:9999; min-width:160px; max-height:280px;"
    class="bg-[#1a1d27] border border-white/10 rounded-xl shadow-2xl py-1 overflow-y-auto"
  >
    {#each options as opt}
      <button
        type="button"
        class="w-full text-left px-3 py-2 text-sm flex items-center gap-2 transition-colors
               {selected.has(opt.value) ? 'text-indigo-300 bg-indigo-500/15' : 'text-gray-300 hover:bg-white/5'}"
        on:click|stopPropagation={() => toggle(opt.value)}
      >
        <span class="w-3.5 flex-shrink-0 text-center text-xs">
          {selected.has(opt.value) ? '✓' : ''}
        </span>
        {opt.label}
      </button>
    {/each}
  </div>
{/if}
