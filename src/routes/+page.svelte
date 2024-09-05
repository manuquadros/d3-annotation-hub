<script lang="ts">
	import '../styles.css';
	import Chunk from './Chunk.svelte';
	import { page } from '$app/stores';

	const pmid = $page.url.searchParams.get('pmid');
	const start = $page.url.searchParams.get('start');
</script>

<div>
	<Chunk {pmid} {start} />
</div>
