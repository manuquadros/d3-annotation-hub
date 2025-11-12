<script lang="ts">
    import Card, { Content } from "@smui/card";
    import { getContext, setContext, onMount } from "svelte";
    import type { Pointer } from "$lib/types.ts";
    import type { SvelteMap } from "svelte/reactivity";

    interface Props {
        fragment: DocumentFragment;
        labelColor: string;
        pointer: { pointer_id: number; label: string };
    }
    const { fragment, labelColor, pointer }: Props = $props();
    const pointers = getContext<SvelteMap<number, Pointer>>("pointers");
    const activeMenuId = getContext<{ value: number | null }>("activeMenuId");

    let mountpoint: HTMLSpanElement;
    let buttonMountpoint: HTMLSpanElement;
    let button: HTMLButtonElement;
    let menuElement: HTMLDivElement;

    // Derive menuVisible from the active menu context
    let menuVisible = $derived(activeMenuId.value === pointer.pointer_id);

    function toggleMenu(event: Event) {
        event.stopPropagation();
        // If this menu is already open, close it. Otherwise, open it (which closes any other menu)
        if (activeMenuId.value === pointer.pointer_id) {
            activeMenuId.value = null;
        } else {
            activeMenuId.value = pointer.pointer_id;
        }
        if (button) {
            button.setAttribute(
                "aria-expanded",
                menuVisible ? "true" : "false",
            );
        }
    }

    function deleteAnnotation() {
        pointers.delete(pointer.pointer_id);
        activeMenuId.value = null;
    }

    function handleClickOutside(event: MouseEvent) {
        if (
            menuVisible &&
            menuElement &&
            !menuElement.contains(event.target as Node) &&
            !button.contains(event.target as Node)
        ) {
            activeMenuId.value = null;
            if (button) {
                button.setAttribute("aria-expanded", "false");
            }
        }
    }

    onMount(() => {
        if (mountpoint && fragment) {
            const highlightText = fragment.textContent || "";
            mountpoint.append(fragment);

            if (buttonMountpoint) {
                button = document.createElement("button");
                button.setAttribute(
                    "aria-label",
                    `Edit annotation '${highlightText}'`,
                );
                button.setAttribute("aria-controls", "h-42");
                button.setAttribute("aria-haspopup", "menu");
                button.setAttribute("aria-expanded", "false");
                button.setAttribute("style", "display: inline");
                button.append("✎");
                button.onclick = toggleMenu;
                buttonMountpoint.append(button);
            }
        }

        document.addEventListener("click", handleClickOutside);

        return () => {
            document.removeEventListener("click", handleClickOutside);
        };
    });
</script>

<Card style="display: inline-block; position: relative;">
    <Content>
        <ruby
            ><span
                bind:this={mountpoint}
                style:border={`2px solid ${labelColor};`}
                style:color="white"
            ></span>
            <rp>(</rp><rt style="color:white;">{pointer.label}</rt><rp>)</rp
            ><span bind:this={buttonMountpoint}></span>
        </ruby>
        {#if menuVisible}
            <div
                bind:this={menuElement}
                style="position: absolute; background: white; border: 1px solid #ccc; padding: 4px; z-index: 1000;"
            >
                <button class={["btn", "btn-block"]} onclick={deleteAnnotation}
                    >Delete annotation</button
                >
            </div>
        {/if}
    </Content>
</Card>
