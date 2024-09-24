<script lang="ts">
  import {
    bacteriaLabel,
    enzymeLabel,
    strainLabel,
    resources,
  } from "$lib/resources.ts";
  import { derived, get } from "svelte/store";
  import { dragStart, dragOver, handleDrop } from "$lib/handlers.ts";

  function plural(singular: string): string {
    if (singular === "Bacteria") {
      return singular;
    } else {
      return singular + "s";
    }
  }

  const classLabels = [enzymeLabel, strainLabel, bacteriaLabel];

  const classes = derived(resources, ($resources) => {
    const map = new Map();
    classLabels.forEach((label) =>
      map.set(
        label,
        Array.from($resources.values()).filter((res) => res.label === label),
      ),
    );

    return map;
  });

  console.log($classes);
</script>

<h2>Entities</h2>

{#if $classes.size > 0}
  {#each $classes as [label, resources]}
    <h3>{plural(label.split(":")[1])}</h3>
    {#each resources as resource}
      {#if resource.count}
        <button
          type="button"
          class="entity entitySummary"
          resource={resource.id}
          typeof={label}
          draggable="true"
          on:dragstart={dragStart}
          on:dragover={dragOver}
          on:drop={handleDrop}
        >
          {resource.name}
        </button>
      {/if}
    {/each}
  {/each}
{/if}

<!-- {#if showDropdown} -->
<!--     <div -->
<!--         class="dropdown" -->
<!--         style="position: absolute; left: {dropdownPosition.x}px; top: {dropdownPosition.y}px;" -->
<!--     > -->
<!--         {#each getOptions() as relation} -->
<!--             <button on:click={handleRelationChoice(relation)}>{relation}</button -->
<!--             > -->
<!--         {/each} -->
<!--     </div> -->
<!-- {/if} -->
