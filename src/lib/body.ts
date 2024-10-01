import { writable } from "svelte/store";

import { isValidEntitySpan, spanWrappedButton } from "$lib/utils.ts";
import { resources } from "$lib/resources.ts";

const { subscribe, set, update } = writable();

export const body = {
    subscribe,
    set,
    initialize: _processTags,
    replaceResource: _replaceResource,
};

function _processTags(): void {
    update((body) => {
        if (body) {
            const spans = body.querySelectorAll("span");

            spans.forEach((span) => {
                if (isValidEntitySpan(span)) {
                    span = spanWrappedButton(span);
                    resources.storeEntitySpan(span);
                }
            });

            return body;
        }
    });
}

function _replaceResource(source: string, target: string): void {
    update((body) => {
        if (body) {
            const spans = body.querySelectorAll(`span[resource="${source}"]`);

            spans.forEach((span) => span.setAttribute("resource", target));

            return body;
        }
    });
}
