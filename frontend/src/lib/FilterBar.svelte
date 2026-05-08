<script lang="ts">
  export let active: Set<string>
  export let options: string[]
  export let label: string

  const toggle = (val: string) => {
    const next = new Set(active)
    next.has(val) ? next.delete(val) : next.add(val)
    active = next
  }
</script>

<div class="flex items-start gap-3 flex-wrap">
  <span class="text-[10px] font-semibold text-gray-500 uppercase tracking-widest w-20 flex-shrink-0 pt-1.5">
    {label}
  </span>
  <div class="flex flex-wrap gap-1.5">
    {#each options as opt}
      <button
        class="filter-chip {active.has(opt) ? 'filter-chip-active' : 'filter-chip-inactive'}"
        on:click={() => toggle(opt)}
      >
        {opt}
      </button>
    {/each}
  </div>
</div>