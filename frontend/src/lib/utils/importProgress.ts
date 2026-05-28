export interface ImportStep {
    step: string;
    label: string;
    status: "pending" | "active" | "done" | "error";
    counts: { loaded: number; total: number };
    isBinary: boolean;
}

export function computeOverallPct(steps: ImportStep[]): number {
    if (steps.length === 0) return 0;
    let points = 0;
    for (const s of steps) {
        if (s.status === "done") {
            points += 1;
        } else if (s.status === "active") {
            points += s.counts.total > 0 ? s.counts.loaded / s.counts.total : 1;
        }
    }
    return Math.round((points / steps.length) * 100);
}
