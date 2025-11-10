<script lang="ts">
    import Card, { Content } from "@smui/card";
    import { onMount } from "svelte";

    interface Props {
        fragment: DocumentFragment;
        labelColor: string;
        label: string;
    }
    const { fragment, labelColor, label }: Props = $props();
    let mountpoint: HTMLSpanElement;
    let buttonMountpoint: HTMLSpanElement;

    onMount(() => {
        if (mountpoint && fragment) {
            const highlightText = fragment.textContent || "";
            mountpoint.append(fragment);

            if (buttonMountpoint) {
                const button = document.createElement("button");
                button.setAttribute(
                    "aria-label",
                    `Edit highlight '${highlightText}'`,
                );
                button.setAttribute("aria-controls", "h-42");
                button.setAttribute("aria-haspopup", "menu");
                button.setAttribute("aria-expanded", "false");
                button.setAttribute("style", "display: inline");
                button.append("✎");
                buttonMountpoint.append(button);
            }
        }
    });
</script>

<Card style="display: inline-block;">
    <Content>
        <ruby
            ><span
                bind:this={mountpoint}
                style:border={`2px solid ${labelColor};`}
                style:color="white"
            ></span>
            <rp>(</rp><rt style="color:white;">{label}</rt><rp>)</rp><span
                bind:this={buttonMountpoint}
            ></span>
        </ruby>
    </Content>
</Card>
