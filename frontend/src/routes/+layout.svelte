<script lang="ts">
	import { auth } from '$lib/stores/auth';

	function handleLogout() {
		auth.logout();
	}
</script>

<div class="app-shell">
	<nav>
		<a href="/" class="brand">Job Vacancy Parser</a>
		<div class="nav-links">
			{#if $auth.accessToken}
				<a href="/history">History</a>
				<button on:click={handleLogout}>Log out</button>
			{:else}
				<a href="/login">Log in</a>
				<a href="/signup">Sign up</a>
			{/if}
		</div>
	</nav>

	<main>
		<slot />
	</main>
</div>

<style>
	.app-shell {
		max-width: 720px;
		margin: 0 auto;
		padding: 1.5rem;
		font-family:
			system-ui,
			-apple-system,
			sans-serif;
	}

	nav {
		display: flex;
		justify-content: space-between;
		align-items: center;
		margin-bottom: 2rem;
		padding-bottom: 1rem;
		border-bottom: 1px solid #e5e5e5;
	}

	.brand {
		font-weight: 600;
		text-decoration: none;
		color: #111;
	}

	.nav-links {
		display: flex;
		gap: 1rem;
		align-items: center;
	}

	.nav-links a,
	.nav-links button {
		font: inherit;
		color: #444;
		text-decoration: none;
		background: none;
		border: none;
		cursor: pointer;
	}
</style>
