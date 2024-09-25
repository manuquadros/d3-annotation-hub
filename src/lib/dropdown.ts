import { writable } from "svelte/store";

function createDropdown() {
    const state = {
        visible: false,
        x: 0,
        y: 0,
    };

    const { subscribe, update } = writable(state);

    const methods = {
        show() {
            update((state) => ({ ...state, visible: true }));
        },

        hide() {
            update((state) => ({ ...state, visible: false }));
        },

        position(newx: number, newy: number) {
            update((state) => ({ ...state, x: newx, y: newy }));
        },
    };

    return {
        subscribe,
        ...methods,
    };
}

export const optionsDropdown = createDropdown();
export const removeDropdown = createDropdown();
