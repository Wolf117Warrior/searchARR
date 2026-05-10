<script lang="ts">
  import DropdownFilter from './DropdownFilter.svelte'
  import type { FilterOption } from './utils'

  export let active: Set<string>
  export let options: (string | FilterOption)[]
  export let label: string

  // Normalise : string[] ou FilterOption[] → { value, label }[]
  $: ddOptions = options.map(o =>
    typeof o === 'string'
      ? { value: o, label: o }
      : { value: o.value, label: o.label }
  )
</script>

<DropdownFilter
  {label}
  options={ddOptions}
  bind:selected={active}
/>
