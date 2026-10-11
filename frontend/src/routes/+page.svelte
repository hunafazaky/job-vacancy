<script lang="ts">
	import { extractJobImage, ApiError, type ExtractionResponse } from '$lib/api';
	import { auth } from '$lib/stores/auth';

	let fileInput: HTMLInputElement;
	let previewUrl: string | null = null;
	let loading = false;
	let error: string | null = null;
	let result: ExtractionResponse | null = null;

	const MAX_SIZE_MB = 5;

	function onFileChange(e: Event) {
		error = null;
		result = null;
		const file = (e.target as HTMLInputElement).files?.[0];
		if (!file) return;

		if (file.size > MAX_SIZE_MB * 1024 * 1024) {
			error = `Image must be under ${MAX_SIZE_MB}MB.`;
			fileInput.value = '';
			return;
		}

		previewUrl = URL.createObjectURL(file);
	}

	async function handleSubmit() {
		const file = fileInput.files?.[0];
		if (!file) {
			error = 'Choose an image first.';
			return;
		}

		loading = true;
		error = null;
		result = null;

		try {
			result = await extractJobImage(file);
		} catch (err) {
			error = err instanceof ApiError ? err.message : 'Something went wrong. Try again.';
		} finally {
			loading = false;
		}
	}
</script>

<h1>Extract a job vacancy from an image</h1>
<p class="subtitle">
	Upload a photo or screenshot of a job posting. We'll pull out the title, company, and
	requirements.
	{#if !$auth.accessToken}
		<a href="/signup">Sign up</a> to save your results.
	{/if}
</p>

<form on:submit|preventDefault={handleSubmit}>
	<input
		bind:this={fileInput}
		type="file"
		accept="image/jpeg,image/png,image/webp"
		on:change={onFileChange}
	/>

	{#if previewUrl}
		<img src={previewUrl} alt="Selected job posting preview" class="preview" />
	{/if}

	<button type="submit" disabled={loading}>
		{loading ? 'Extracting…' : 'Extract job details'}
	</button>
</form>

{#if error}
	<p class="error">{error}</p>
{/if}

{#if result}
	<section class="result">
		<h2>{result.job_title ?? 'Job title not found'}</h2>
		{#if result.company}<p class="company">{result.company}</p>{/if}

		<dl>
			{#if result.location}
				<dt>Location</dt>
				<dd>{result.location}</dd>
			{/if}
			{#if result.employment_type}
				<dt>Type</dt>
				<dd>{result.employment_type}</dd>
			{/if}
			{#if result.salary_range}
				<dt>Salary</dt>
				<dd>{result.salary_range}</dd>
			{/if}
		</dl>

		{#if result.skills_required?.length}
			<h3>Skills required</h3>
			<ul class="skills">
				{#each result.skills_required as skill}
					<li>{skill}</li>
				{/each}
			</ul>
		{/if}

		{#if result.description}
			<h3>Description</h3>
			<p>{result.description}</p>
		{/if}

		<p class="meta">
			{#if result.saved}
				Saved to your history.
			{:else}
				Not saved — <a href="/signup">sign up</a> to keep a history of extractions.
			{/if}
		</p>
	</section>
{/if}

<style>
	.subtitle {
		color: #555;
		margin-bottom: 1.5rem;
	}

	form {
		display: flex;
		flex-direction: column;
		gap: 1rem;
		margin-bottom: 1.5rem;
	}

	.preview {
		max-width: 100%;
		max-height: 300px;
		object-fit: contain;
		border: 1px solid #e5e5e5;
		border-radius: 6px;
	}

	button {
		align-self: flex-start;
		padding: 0.6rem 1.2rem;
		background: #111;
		color: white;
		border: none;
		border-radius: 6px;
		cursor: pointer;
	}

	button:disabled {
		opacity: 0.6;
		cursor: not-allowed;
	}

	.error {
		color: #b00020;
	}

	.result {
		border: 1px solid #e5e5e5;
		border-radius: 8px;
		padding: 1.5rem;
	}

	.company {
		color: #555;
		margin-top: -0.5rem;
	}

	dl {
		display: grid;
		grid-template-columns: auto 1fr;
		gap: 0.25rem 1rem;
		margin: 1rem 0;
	}

	dt {
		font-weight: 600;
		color: #555;
	}

	.skills {
		display: flex;
		flex-wrap: wrap;
		gap: 0.5rem;
		list-style: none;
		padding: 0;
	}

	.skills li {
		background: #f0f0f0;
		border-radius: 999px;
		padding: 0.25rem 0.75rem;
		font-size: 0.9rem;
	}

	.meta {
		margin-top: 1.5rem;
		font-size: 0.9rem;
		color: #777;
	}
</style>
