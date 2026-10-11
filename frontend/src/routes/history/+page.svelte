<script lang="ts">
	import { onMount } from 'svelte';
	import { goto } from '$app/navigation';
	import { auth } from '$lib/stores/auth';
	import { getHistory, deleteExtraction, ApiError, type ExtractionResponse } from '$lib/api';

	let items: ExtractionResponse[] = [];
	let loading = true;
	let error: string | null = null;

	onMount(async () => {
		if (!$auth.accessToken) {
			goto('/login');
			return;
		}
		try {
			items = await getHistory();
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not load history.';
		} finally {
			loading = false;
		}
	});

	async function handleDelete(id: string | null) {
		if (!id) return;
		try {
			await deleteExtraction(id);
			items = items.filter((item) => item.id !== id);
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Could not delete.';
		}
	}
</script>

<h1>Your history</h1>

{#if loading}
	<p>Loading…</p>
{:else if error}
	<p class="error">{error}</p>
{:else if items.length === 0}
	<p>No saved extractions yet. <a href="/">Upload a job posting</a> to get started.</p>
{:else}
	<ul class="history-list">
		{#each items as item (item.id)}
			<li>
				{#if item.image_url}
					<img src={item.image_url} alt={item.job_title ?? 'Job posting'} />
				{/if}
				<div>
					<h3>{item.job_title ?? 'Untitled'}</h3>
					<p class="company">{item.company ?? ''}</p>
					<p class="date">{item.created_at ? new Date(item.created_at).toLocaleDateString() : ''}</p>
				</div>
				<button on:click={() => handleDelete(item.id)}>Delete</button>
			</li>
		{/each}
	</ul>
{/if}

<style>
	.history-list {
		list-style: none;
		padding: 0;
		display: flex;
		flex-direction: column;
		gap: 1rem;
	}
	.history-list li {
		display: flex;
		align-items: center;
		gap: 1rem;
		border: 1px solid #e5e5e5;
		border-radius: 8px;
		padding: 1rem;
	}
	.history-list img {
		width: 64px;
		height: 64px;
		object-fit: cover;
		border-radius: 6px;
	}
	.history-list h3 {
		margin: 0;
	}
	.company {
		color: #555;
		margin: 0.15rem 0;
	}
	.date {
		color: #999;
		font-size: 0.8rem;
		margin: 0;
	}
	button {
		margin-left: auto;
		background: none;
		border: 1px solid #ccc;
		border-radius: 6px;
		padding: 0.4rem 0.8rem;
		cursor: pointer;
	}
	.error {
		color: #b00020;
	}
</style>
