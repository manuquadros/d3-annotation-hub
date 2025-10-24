export async function load({ fetch }) {
    const searchParams = new URLSearchParams({
        identifier: "15117974",
    });

    const response = await fetch("/references?identifier=15117974");

    const documentData = await response.json();
    return { documentData };
}
