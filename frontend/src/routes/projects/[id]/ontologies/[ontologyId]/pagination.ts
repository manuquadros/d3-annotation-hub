/**
 * Rows per page for the ontology-detail Classes and Triples tables. Shared by
 * the server loader (initial page) and the client pager so the first paint and
 * subsequent pages never disagree on how many rows a page holds.
 */
export const PAGE_SIZE = 10;
