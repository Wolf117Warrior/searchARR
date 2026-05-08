<script lang="ts">
  import '../app.css'
  import ServiceStatus from '$lib/ServiceStatus.svelte'
</script>

<div class="min-h-screen bg-[#0d0f14] text-white">
  <header class="sticky top-0 z-50 bg-[#0d0f14]/90 backdrop-blur-md border-b border-white/5">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 h-14 flex items-center gap-3">
      <!-- Logo -->
      <!-- Logo -->
      <a href="/" class="flex items-center gap-2.5 text-white font-bold text-lg tracking-tight hover:opacity-80 transition-opacity">
        <svg class="w-7 h-7 text-indigo-400" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="1.8">
          <circle cx="11" cy="11" r="7" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M20 20l-3-3" />
          <path stroke-linecap="round" stroke-linejoin="round" d="M11 8v6M8 11h6" />
        </svg>
        <span>search<span class="text-indigo-400">ARR</span></span>
      </a>

      <!-- Spacer -->
      <div class="flex-1"></div>

      <!-- Label StackARR + statut services -->
      <div class="flex items-center gap-2">
        <span class="text-xs font-semibold text-gray-500">Stack<span class="text-indigo-400">ARR</span></span>
        <ServiceStatus />
      </div>
    </div>
  </header>

  <main>
    <slot />
  </main>
</div>
