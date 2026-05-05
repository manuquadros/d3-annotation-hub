<script lang="ts">
    import { page } from "$app/stores";

    interface Props {
        children: import("svelte").Snippet;
    }
    let { children }: Props = $props();

    const nav = [
        { href: "/docs", label: "Introduction" },
        { href: "/docs/annotation", label: "Annotating articles" },
        { href: "/docs/curation", label: "Curating annotations" },
        { href: "/docs/management", label: "Project management" },
    ];

    let lightboxSrc = $state<string | null>(null);

    function handleContentClick(e: MouseEvent) {
        const target = e.target as HTMLElement;
        if (target.tagName === "IMG") {
            lightboxSrc = (target as HTMLImageElement).src;
        }
    }

    function closeLightbox() {
        lightboxSrc = null;
    }

    function handleKeydown(e: KeyboardEvent) {
        if (e.key === "Escape") closeLightbox();
    }
</script>

<svelte:window onkeydown={handleKeydown} />

<div class="docs-layout">
    <aside class="docs-nav">
        <p class="title">User Guide</p>
        <nav>
            {#each nav as item (item.href)}
                <a
                    href={item.href}
                    class:active={$page.url.pathname === item.href}
                >
                    {item.label}
                </a>
            {/each}
        </nav>
    </aside>

    <!-- svelte-ignore a11y_click_events_have_key_events a11y_no_noninteractive_element_interactions -->
    <article class="docs-content" onclick={handleContentClick}>
        {@render children()}
    </article>
</div>

{#if lightboxSrc}
    <button class="lightbox" onclick={closeLightbox} aria-label="Close image">
        <img src={lightboxSrc} alt="" />
    </button>
{/if}

<style>
    .docs-layout {
        display: grid;
        grid-template-columns: 220px 1fr;
        gap: 2rem;
        align-items: start;
        max-width: 960px;
        margin: 0 auto;
        padding: 2rem 1rem;
    }

    .docs-nav {
        position: sticky;
        top: 1rem;
    }

    .docs-nav .title {
        font-size: 0.75rem;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
        color: var(--color-text-muted, #888);
        margin-bottom: 0.5rem;
    }

    .docs-nav nav {
        display: flex;
        flex-direction: column;
        gap: 0.25rem;
    }

    .docs-nav a {
        display: block;
        padding: 0.35rem 0.6rem;
        border-radius: 4px;
        color: inherit;
        text-decoration: none;
        font-size: 0.9rem;
    }

    .docs-nav a:hover {
        background: var(--color-bg-hover, #f0f0f0);
    }

    .docs-nav a.active {
        background: var(--color-bg-active, #e8e8e8);
        font-weight: 600;
    }

    .docs-content {
        min-width: 0;
    }

    .docs-content :global(h1) { font-size: 1.75rem; margin-bottom: 1rem; }
    .docs-content :global(h2) { font-size: 1.3rem; margin-top: 2rem; margin-bottom: 0.75rem; }
    .docs-content :global(h3) { font-size: 1.1rem; margin-top: 1.5rem; margin-bottom: 0.5rem; }
    .docs-content :global(p)  { line-height: 1.7; margin-bottom: 1rem; }
    .docs-content :global(ul), .docs-content :global(ol) { padding-left: 1.5rem; margin-bottom: 1rem; }
    .docs-content :global(li) { margin-bottom: 0.25rem; line-height: 1.6; }
    .docs-content :global(code) { font-size: 0.875em; background: var(--color-bg-code, #f4f4f4); padding: 0.15em 0.35em; border-radius: 3px; }
    .docs-content :global(pre) { background: var(--color-bg-code, #f4f4f4); padding: 1rem; border-radius: 6px; overflow-x: auto; margin-bottom: 1rem; }
    .docs-content :global(pre code) { background: none; padding: 0; }
    .docs-content :global(img) { display: block; width: 80%; margin: 1rem auto; cursor: zoom-in; }

    .lightbox {
        position: fixed;
        inset: 0;
        background: rgba(0, 0, 0, 0.8);
        display: flex;
        align-items: center;
        justify-content: center;
        z-index: 1000;
        cursor: zoom-out;
        border: none;
        padding: 2rem;
    }

    .lightbox img {
        max-width: 100%;
        max-height: 90vh;
        object-fit: contain;
        border-radius: 4px;
    }
</style>
