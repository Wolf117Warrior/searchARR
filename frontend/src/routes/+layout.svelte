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

      <!-- Nav -->
      <nav class="flex items-center gap-1 ml-4">
        <a href="/search" class="btn-ghost text-xs gap-1.5">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M3 4a1 1 0 011-1h16a1 1 0 011 1v2a1 1 0 01-.293.707L13 13.414V19a1 1 0 01-.553.894l-4 2A1 1 0 017 21v-7.586L3.293 6.707A1 1 0 013 6V4z"/>
          </svg>
          Recherche avancée
        </a>
        <a href="/config" class="btn-ghost text-xs gap-1.5">
          <svg class="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
            <path stroke-linecap="round" stroke-linejoin="round" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z"/>
            <path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
          </svg>
          Configuration
        </a>
      </nav>

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
