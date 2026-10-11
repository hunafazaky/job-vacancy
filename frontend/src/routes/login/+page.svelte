<script lang="ts">
	import { goto } from '$app/navigation';
	import { login, ApiError } from '$lib/api';
	import { auth } from '$lib/stores/auth';

	let email = '';
	let password = '';
	let error: string | null = null;
	let loading = false;

	async function handleSubmit() {
		loading = true;
		error = null;
		try {
			const { access_token, refresh_token } = await login(email, password);
			auth.login(access_token, refresh_token);
			goto('/');
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Login failed.';
		} finally {
			loading = false;
		}
	}
</script>

<h1>Log in</h1>

<form on:submit|preventDefault={handleSubmit}>
	<label>
		Email
		<input type="email" bind:value={email} required />
	</label>
	<label>
		Password
		<input type="password" bind:value={password} required />
	</label>
	<button type="submit" disabled={loading}>{loading ? 'Logging in…' : 'Log in'}</button>
</form>

{#if error}<p class="error">{error}</p>{/if}

<p>No account? <a href="/signup">Sign up</a></p>

<style>
	form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		max-width: 320px;
	}
	label {
		display: flex;
		flex-direction: column;
		gap: 0.25rem;
		font-size: 0.9rem;
		color: #444;
	}
	input {
		padding: 0.5rem;
		border: 1px solid #ccc;
		border-radius: 6px;
		font: inherit;
	}
	button {
		padding: 0.6rem 1.2rem;
		background: #111;
		color: white;
		border: none;
		border-radius: 6px;
		cursor: pointer;
	}
	.error {
		color: #b00020;
	}
</style>
