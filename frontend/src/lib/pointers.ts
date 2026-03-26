let _counter = 0;

export function nextPointerKey(): string {
    return `ptr_${++_counter}`;
}

export function initPointerCounter(n: number): void {
    _counter = n;
}
