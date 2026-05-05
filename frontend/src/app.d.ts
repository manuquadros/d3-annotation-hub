// See https://kit.svelte.dev/docs/types#app
// for information about these interfaces
declare global {
    namespace App {
        // interface Error {}
        // interface Locals {}
        // interface PageData {}
        // interface PageState {}
        // interface Platform {}
    }

    interface Window {
        digidive?: {
            toggleSidebar(el?: Element): void;
        };
    }

    const digidive: NonNullable<Window["digidive"]>;
    const __APP_VERSION__: string;
}

export {};
