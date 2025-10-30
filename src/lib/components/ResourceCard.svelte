<script lang="ts">
    import Card, { Content } from "@smui/card";
    import { onMount } from "svelte";

    let { fragment } = $props();
    let mountpoint: HTMLSpanElement;

    onMount(() => {
        mountpoint.textContent = "";
        mountpoint.append(fragment);
    });
</script>

<Card>
    <Content><span bind:this={mountpoint}></span></Content>
</Card>
