<script lang="ts">
	import { onMount } from 'svelte';
	export let pmid: string = '';
	export let start: string = '';
	let promise;

	async function loadChunk() {
		let url: string;
		if (start && pmid) {
			console.log(`loading position ${start} from article ${pmid}`);
			url = `http://localhost:8000/segment/?pmid=${pmid}&start=${start}`;
		} else if (pmid) {
			console.log(`loading article ${pmid}`);
			url = `http://localhost:8000/segment/?pmid=${pmid}`;
		} else {
			console.log('start and pmid are null');
			url = 'http://localhost:8000/segment/';
		}
		let response = await fetch(url);
		return response.json();
	}

	function log(str: string) {
		console.log('Response data:', JSON.stringify(str, null, 2));
	}

	onMount(() => {
		promise = loadChunk();
	});
</script>

{#await promise}
	<p>Loading...</p>
{:then data}
	<div>
		{#if data}
			{@html JSON.parse(data).content}
		{/if}
	</div>
{:catch error}
	<p style="color: red">{error.message}</p>
{/await}
