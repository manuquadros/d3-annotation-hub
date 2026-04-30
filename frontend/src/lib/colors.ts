export function getLabelColor(label: string): string {
    if (!label) return "#CCCCCC";
    let hash = 0;
    for (let i = 0; i < label.length; i++) {
        hash = (hash * 31 + label.charCodeAt(i)) >>> 0;
    }
    const hue = hash % 360;
    return `hsl(${hue}, 65%, 45%)`;
}

export function getContrastColor(color: string | undefined): string {
    if (!color) return "#000000";

    const hslMatch = color.match(/hsl\(\s*\d+\s*,\s*[\d.]+%\s*,\s*([\d.]+)%/);
    if (hslMatch) {
        return parseFloat(hslMatch[1]) > 55 ? "#000000" : "#ffffff";
    }

    const hex = color.replace("#", "");
    const r = parseInt(hex.substring(0, 2), 16) / 255;
    const g = parseInt(hex.substring(2, 4), 16) / 255;
    const b = parseInt(hex.substring(4, 6), 16) / 255;
    const toLinear = (c: number) =>
        c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    const luminance =
        0.2126 * toLinear(r) + 0.7152 * toLinear(g) + 0.0722 * toLinear(b);
    return luminance > 0.179 ? "#000000" : "#ffffff";
}
