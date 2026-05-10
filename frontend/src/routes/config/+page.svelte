<script lang="ts">
  import { onMount } from 'svelte'
  import { getConfig, saveConfig, type AppConfig } from '$lib/api'

  type FormData = Omit<AppConfig, 'configured'>

  const DEFAULTS: FormData = {
    tmdb_api_key:           '',
    prowlarr_url:           'http://localhost:9696',
    prowlarr_api_key:       '',
    radarr_url:             'http://localhost:7878',
    radarr_api_key:         '',
    radarr_root_folder:     '/data/torrents/films',
    radarr_quality_profile: 1,
    sonarr_url:             'http://localhost:8989',
    sonarr_api_key:         '',
    sonarr_root_folder:     '/data/torrents/series',
    sonarr_quality_profile: 1,
    qbit_url:               'http://localhost:8080',
    qbit_user:              'admin',
    qbit_pass:              '',
  }

  let form: FormData = { ...DEFAULTS }
  let loading  = true
  let saving   = false
  let saved    = false
  let error    = ''
  let showPass: Record<string, boolean> = {}

  onMount(async () => {
    try {
      const data = await getConfig()
      form = { ...DEFAULTS, ...data }
    } catch (e: any) {
      error = e.message
    } finally {
      loading = false
    }
  })

  const handleSave = async () => {
    saving = true
    saved  = false
    error  = ''
    try {
      await saveConfig(form)
      saved = true
      setTimeout(() => saved = false, 3000)
    } catch (e: any) {
      error = e.message
    } finally {
      saving = false
    }
  }

  const toggle = (k: string) => showPass[k] = !showPass[k]

  const EyeOff = `<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21"/></svg>`
  const EyeOn  = `<svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/><path stroke-linecap="round" stroke-linejoin="round" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/></svg>`
</script>

<svelte:head><title>Configuration — searchARR</title></svelte:head>

<div class="max-w-2xl mx-auto px-4 sm:px-6 py-10">

  <!-- Header -->
  <div class="mb-8 flex items-center justify-between">
    <div>
      <h1 class="text-2xl font-bold text-white mb-1">Configuration</h1>
      <p class="text-sm text-gray-500">Connexion aux services — persisté dans <code class="text-indigo-400 text-xs">/data/config.json</code></p>
    </div>
    {#if saved}
      <span class="flex items-center gap-1.5 text-xs text-green-400 font-medium animate-pulse">
        <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2"><path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/></svg>
        Sauvegardé
      </span>
    {/if}
  </div>

  {#if loading}
    <div class="space-y-4">
      {#each Array(6) as _}<div class="skeleton h-14 rounded-xl"></div>{/each}
    </div>

  {:else}
    <form on:submit|preventDefault={handleSave} class="space-y-6">

      <!-- TMDB -->
      <section class="cfg-section">
        <h2 class="cfg-title">TMDB</h2>
        <div class="cfg-field">
          <label for="tmdb_api_key">API Key</label>
          <div class="secret-wrap">
            <input id="tmdb_api_key"
              type={showPass['tmdb_api_key'] ? 'text' : 'password'}
              bind:value={form.tmdb_api_key}
              placeholder="Clé API TMDB v3"
              autocomplete="off" />
            <button type="button" class="eye" on:click={() => toggle('tmdb_api_key')} tabindex="-1" aria-label="toggle">
              {@html showPass['tmdb_api_key'] ? EyeOff : EyeOn}
            </button>
          </div>
        </div>
      </section>

      <!-- Prowlarr -->
      <section class="cfg-section">
        <h2 class="cfg-title">Prowlarr</h2>
        <div class="cfg-grid">
          <div class="cfg-field col-span-2">
            <label for="prowlarr_url">URL</label>
            <input id="prowlarr_url" type="url" bind:value={form.prowlarr_url} placeholder="http://prowlarr:9696" />
          </div>
          <div class="cfg-field col-span-2">
            <label for="prowlarr_api_key">API Key</label>
            <div class="secret-wrap">
              <input id="prowlarr_api_key"
                type={showPass['prowlarr_api_key'] ? 'text' : 'password'}
                bind:value={form.prowlarr_api_key}
                placeholder="Clé API Prowlarr"
                autocomplete="off" />
              <button type="button" class="eye" on:click={() => toggle('prowlarr_api_key')} tabindex="-1" aria-label="toggle">
                {@html showPass['prowlarr_api_key'] ? EyeOff : EyeOn}
              </button>
            </div>
          </div>
        </div>
      </section>

      <!-- Radarr -->
      <section class="cfg-section">
        <h2 class="cfg-title">Radarr</h2>
        <div class="cfg-grid">
          <div class="cfg-field col-span-2">
            <label for="radarr_url">URL</label>
            <input id="radarr_url" type="url" bind:value={form.radarr_url} placeholder="http://radarr:7878" />
          </div>
          <div class="cfg-field col-span-2">
            <label for="radarr_api_key">API Key</label>
            <div class="secret-wrap">
              <input id="radarr_api_key"
                type={showPass['radarr_api_key'] ? 'text' : 'password'}
                bind:value={form.radarr_api_key}
                placeholder="Clé API Radarr"
                autocomplete="off" />
              <button type="button" class="eye" on:click={() => toggle('radarr_api_key')} tabindex="-1" aria-label="toggle">
                {@html showPass['radarr_api_key'] ? EyeOff : EyeOn}
              </button>
            </div>
          </div>
          <div class="cfg-field">
            <label for="radarr_root">Dossier root</label>
            <input id="radarr_root" type="text" bind:value={form.radarr_root_folder} placeholder="/data/torrents/films" />
          </div>
          <div class="cfg-field">
            <label for="radarr_quality">Profil qualité (ID)</label>
            <input id="radarr_quality" type="number" bind:value={form.radarr_quality_profile} min="1" />
          </div>
        </div>
      </section>

      <!-- Sonarr -->
      <section class="cfg-section">
        <h2 class="cfg-title">Sonarr</h2>
        <div class="cfg-grid">
          <div class="cfg-field col-span-2">
            <label for="sonarr_url">URL</label>
            <input id="sonarr_url" type="url" bind:value={form.sonarr_url} placeholder="http://sonarr:8989" />
          </div>
          <div class="cfg-field col-span-2">
            <label for="sonarr_api_key">API Key</label>
            <div class="secret-wrap">
              <input id="sonarr_api_key"
                type={showPass['sonarr_api_key'] ? 'text' : 'password'}
                bind:value={form.sonarr_api_key}
                placeholder="Clé API Sonarr"
                autocomplete="off" />
              <button type="button" class="eye" on:click={() => toggle('sonarr_api_key')} tabindex="-1" aria-label="toggle">
                {@html showPass['sonarr_api_key'] ? EyeOff : EyeOn}
              </button>
            </div>
          </div>
          <div class="cfg-field">
            <label for="sonarr_root">Dossier root</label>
            <input id="sonarr_root" type="text" bind:value={form.sonarr_root_folder} placeholder="/data/torrents/series" />
          </div>
          <div class="cfg-field">
            <label for="sonarr_quality">Profil qualité (ID)</label>
            <input id="sonarr_quality" type="number" bind:value={form.sonarr_quality_profile} min="1" />
          </div>
        </div>
      </section>

      <!-- qBittorrent -->
      <section class="cfg-section">
        <h2 class="cfg-title">qBittorrent</h2>
        <div class="cfg-grid">
          <div class="cfg-field col-span-2">
            <label for="qbit_url">URL</label>
            <input id="qbit_url" type="url" bind:value={form.qbit_url} placeholder="http://qbittorrent:8080" />
          </div>
          <div class="cfg-field">
            <label for="qbit_user">Utilisateur</label>
            <input id="qbit_user" type="text" bind:value={form.qbit_user} placeholder="admin" autocomplete="off" />
          </div>
          <div class="cfg-field">
            <label for="qbit_pass">Mot de passe</label>
            <div class="secret-wrap">
              <input id="qbit_pass"
                type={showPass['qbit_pass'] ? 'text' : 'password'}
                bind:value={form.qbit_pass}
                placeholder="••••••••"
                autocomplete="off" />
              <button type="button" class="eye" on:click={() => toggle('qbit_pass')} tabindex="-1" aria-label="toggle">
                {@html showPass['qbit_pass'] ? EyeOff : EyeOn}
              </button>
            </div>
          </div>
        </div>
      </section>

      {#if error}
        <div class="rounded-xl bg-red-500/10 border border-red-500/20 px-4 py-3 text-sm text-red-400">{error}</div>
      {/if}

      <div class="flex justify-end pt-2">
        <button type="submit" class="btn-primary px-8" disabled={saving}>
          {#if saving}
            <svg class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
              <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"/>
              <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8v8H4z"/>
            </svg>
            Sauvegarde...
          {:else}
            <svg class="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
              <path stroke-linecap="round" stroke-linejoin="round" d="M5 13l4 4L19 7"/>
            </svg>
            Sauvegarder
          {/if}
        </button>
      </div>

    </form>
  {/if}

</div>

<style>
  .cfg-section {
    background: rgba(255,255,255,0.03);
    border: 1px solid rgba(255,255,255,0.08);
    border-radius: 1rem;
    padding: 1.25rem;
    display: flex;
    flex-direction: column;
    gap: 1rem;
  }
  .cfg-title    { @apply text-sm font-semibold text-white/80 mb-1; }
  .cfg-grid     { @apply grid grid-cols-2 gap-4; }
  .cfg-field    { @apply flex flex-col gap-1.5; }
  .cfg-field label { @apply text-[10px] font-semibold uppercase tracking-widest text-gray-500; }
  .cfg-field input {
    @apply w-full px-3 py-2.5 rounded-lg bg-white/5 border border-white/10 text-white text-sm
           placeholder-gray-600 focus:outline-none focus:border-indigo-500/60 transition-all;
  }
  .secret-wrap  { @apply relative; }
  .secret-wrap input { @apply pr-10; }
  .eye {
    @apply absolute right-2.5 top-1/2 -translate-y-1/2 text-gray-500
           hover:text-gray-300 transition-colors cursor-pointer bg-transparent border-0 p-0;
  }
</style>
