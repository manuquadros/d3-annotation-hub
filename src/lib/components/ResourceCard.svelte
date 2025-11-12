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

    function deleteAnnotation() {
        pointers.delete(pointer.pointer_id);
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
                button.append("✕");
                button.onclick = deleteAnnotation;
                buttonMountpoint.append(button);
            }
        }
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
    </Content>
</Card>
