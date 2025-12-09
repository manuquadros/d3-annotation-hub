<script>
    /**
     * @typedef {Object} Props
     * @property {import('svelte').Snippet} [children]
     */

    /** @type {Props} */
    import { page } from "$app/stores";
    import { auth } from "$lib/auth.svelte";
    import "../styles.css";
    let { children } = $props();

    let isLoginPage = $derived($page.url.pathname === "/login");
</script>

<header>
    {#if auth.isAuthenticated && !isLoginPage}
        <button class="logout-button" onclick={() => auth.logout()}>
            Logout
        </button>
    {/if}
</header>

<div class="layout">
    {@render children?.()}
</div>
