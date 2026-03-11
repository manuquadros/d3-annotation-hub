<script lang="ts">
    import { browser } from "$app/environment";
    import type { PageData } from "./$types";

    import "../styles.css";
    import Annotation from "$lib/components/Annotation.svelte";

    interface Props {
        data: PageData;
    }

    let { data }: Props = $props();

    const initialState = data.documentData;
</script>

<Annotation {initialState} />
