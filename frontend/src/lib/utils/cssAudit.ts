/**
 * Static checks over raw CSS text, used by the style tests to hold component
 * `<style>` blocks to the Digidive design system.
 */

/** The CSS Color Level 4 named colours, minus the two system-neutral keywords. */
const NAMED_COLORS = new Set(
    `
    aliceblue antiquewhite aqua aquamarine azure beige bisque black
    blanchedalmond blue blueviolet brown burlywood cadetblue chartreuse
    chocolate coral cornflowerblue cornsilk crimson cyan darkblue darkcyan
    darkgoldenrod darkgray darkgreen darkgrey darkkhaki darkmagenta
    darkolivegreen darkorange darkorchid darkred darksalmon darkseagreen
    darkslateblue darkslategray darkslategrey darkturquoise darkviolet
    deeppink deepskyblue dimgray dimgrey dodgerblue firebrick floralwhite
    forestgreen fuchsia gainsboro ghostwhite gold goldenrod gray green
    greenyellow grey honeydew hotpink indianred indigo ivory khaki lavender
    lavenderblush lawngreen lemonchiffon lightblue lightcoral lightcyan
    lightgoldenrodyellow lightgray lightgreen lightgrey lightpink
    lightsalmon lightseagreen lightskyblue lightslategray lightslategrey
    lightsteelblue lightyellow lime limegreen linen magenta maroon
    mediumaquamarine mediumblue mediumorchid mediumpurple mediumseagreen
    mediumslateblue mediumspringgreen mediumturquoise mediumvioletred
    midnightblue mintcream mistyrose moccasin navajowhite navy oldlace
    olive olivedrab orange orangered orchid palegoldenrod palegreen
    paleturquoise palevioletred papayawhip peachpuff peru pink plum
    powderblue purple rebeccapurple red rosybrown royalblue saddlebrown
    salmon sandybrown seagreen seashell sienna silver skyblue slateblue
    slategray slategrey snow springgreen steelblue tan teal thistle tomato
    turquoise violet wheat white whitesmoke yellow yellowgreen
    `
        .split(/\s+/)
        .filter(Boolean),
);

const COLOR_FUNCTIONS = new Set(
    `
    rgb rgba hsl hsla hwb lab lch oklab oklch color color-mix device-cmyk
    `
        .split(/\s+/)
        .filter(Boolean),
);

const COMMENT = /\/\*[\s\S]*?\*\//g;
const QUOTED = /"[^"]*"|'[^']*'/g;
const HEX = /#[0-9a-fA-F]{3,8}\b/g;

/*
 * A leading `-` or word character is excluded so that the tail of a token name
 * (`--red-500`, `--gray-color-light`) and unit suffixes (`0.5rem`) are not read
 * as bare identifiers.
 */
const IDENTIFIER = /(?<![-\w#])[a-zA-Z][a-zA-Z-]*/g;

/*
 * Translucent washes of pure black or white are ambient shadow tints, not
 * palette entries: the design system has no token for them, so the components
 * are allowed to keep them literal. Any other rgba() is a palette colour.
 */
const NEUTRAL_TINT =
    /\brgba\(\s*(?:0\s*,\s*0\s*,\s*0|255\s*,\s*255\s*,\s*255)\s*,\s*(?:0|0?\.\d+)\s*\)/g;

/** The text between every innermost pair of braces, i.e. declarations only. */
function declarationBodies(css: string): string {
    return [...css.matchAll(/\{([^{}]*)\}/g)]
        .map((block) => block[1])
        .join("\n");
}

/**
 * Every hardcoded colour in the declarations of `css` — hex literals, CSS
 * named colours and colour-function calls — in source order.
 *
 * `var()` references, `transparent`, `currentcolor` and the CSS-wide keywords
 * are not colours in this sense and never appear. Neither do translucent
 * black or white `rgba()` tints, which the components deliberately retain in
 * their `box-shadow` values.
 */
export function findHardcodedColors(css: string): string[] {
    const declarations = declarationBodies(css)
        .replace(COMMENT, " ")
        .replace(QUOTED, " ")
        .replace(NEUTRAL_TINT, " ");

    const found = [...(declarations.match(HEX) ?? [])];

    for (const match of declarations.matchAll(IDENTIFIER)) {
        const name = match[0].toLowerCase();
        const called = declarations[match.index + match[0].length] === "(";

        if (called && COLOR_FUNCTIONS.has(name)) {
            found.push(`${name}(`);
        } else if (!called && NAMED_COLORS.has(name)) {
            found.push(name);
        }
    }

    return found;
}

/**
 * The custom properties `css` declares on `:root`, i.e. the tokens that
 * actually resolve everywhere. A property declared only inside a component
 * rule is not one of them, however global its name looks.
 */
export function declaredRootTokens(css: string): Set<string> {
    const tokens = new Set<string>();

    for (const block of css.matchAll(/:root\s*\{([^{}]*)\}/g)) {
        for (const declaration of block[1].matchAll(/(--[\w-]+)\s*:/g)) {
            tokens.add(declaration[1]);
        }
    }

    return tokens;
}
