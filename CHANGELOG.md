# Changelog

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Autosave (annotation and curation) no longer lets a slow older save overwrite a newer one: an in-flight save is aborted when a newer edit triggers the next save, and superseded saves are ignored instead of flashing a spurious "Error – click to retry" during rapid editing.
- Paginated API list endpoints now reject an out-of-range page size (`limit` outside 1–200, or a negative `offset`) with a 422 instead of returning the entire table.
- Entity search now matches per-word prefixes through the FTS index instead of scanning for arbitrary substrings, so it stays fast on large ontologies; searching a mid-word fragment (e.g. "bacterium" to find "Mycobacterium") no longer matches, but any leading or non-leading whole-word prefix still does.
- Large ontology imports are faster: the search index's per-row sync triggers are suppressed during a bulk load and the index is rebuilt once at the end.
- Curation CURIE rename is restricted to proposed (unconfirmed) entities; renaming a confirmed entity is rejected.
- Curation CURIE rename is scoped to the caller's project (404 for another project's entity).
- Renaming a CURIE to one already in use returns a 409 instead of a server error (curation and admin).
- The curation and admin CURIE editors show the rejection reason inline and stay open for correction.
- In the admin panel, a proposed entity's CURIE is edited by clicking the CURIE itself (the "Edit CURIE" button was removed).
- Renaming a CURIE to an empty/whitespace value is rejected (422).
- In the admin panel, a proposed entity's Accept/Reject buttons are disabled while its CURIE rename is in flight.
- Renaming an entity's CURIE preserves SQLite foreign-key enforcement.
- Saving an annotation is recorded under the authenticated user and rejected (403) for non-members of the target project.
- Deleting a proposed entity that was already curated no longer errors; its curation rows are removed in the cascade.
- Proposing an entity or property requires membership in the target project (403 otherwise).
- Proposing an entity with an existing CURIE returns 409, and an empty/whitespace CURIE is rejected (422).
- Project managers without global admin rights can open a project's Users, Documents, and Ontologies pages.
- Renaming a proposed entity's CURIE during curation refreshes the review immediately so the save uses the new identifier.
- Ontology import streams uploads, so very large ontologies (e.g. NCBITaxon 1.5 GB+) import without exhausting memory; entity/triple progress shows a running count.
- Ontology import is hardened against malicious XML (entity-expansion/XXE and "billion laughs" bombs) while still accepting OBO namespace entities.
- Curators can rename a legacy proposed entity with no project scope (NULL `project_id`); the rename adopts it into the current project instead of returning 404.
- Failed create/save/delete actions now show a consistent error message, surfacing the server's reason or a non-JSON gateway/proxy body instead of a generic status or raw JSON.
- A rapid double-Enter in the CURIE editor no longer fires a duplicate rename (which showed a spurious error over the successful save).
- The curation page's CURIE editor now uses the same component as the admin panel, gaining explicit Save/Cancel buttons for consistent behavior.
- Renaming a proposed entity's CURIE during curation no longer fails with a spurious "already in use" error once the entity has been annotated; the rename now updates every annotation-pointer table atomically.
- API proxy routes now percent-encode route and query parameters through a shared helper, closing a path/parameter-smuggling hole where a value such as `..%2Fontologies%2F5` could redirect a token-bearing request to a different backend endpoint. The helper also bounds the upstream time-to-first-byte and no longer forwards backend `Set-Cookie` headers to the browser.

## [0.1.4]

### Added

- Retrieve PubMed abstract when fulltext is not available via PMC.
- Show a progress bar when importing (potentially large) ontologies.
- Extract metadata from the ontology file to populate the import fields.
- Harden ontology metadata extraction against malicious XML entity-expansion in uploaded files.

### Fixed

- Fix internal database error when deleting an ontology that has associated properties or project assignments.
- Project managers who also hold the annotator role can now see the annotation queue in the sidebar.

## [0.1.3] - 2026-05-13

### Added

- Managers can remove references from a project.

### Fixed

- Entity and class search suggestions respect prefix matches. Prefix matches > contains-only matches, and preferred-name matches > synonym-only matches.
- Prevent titles containing inline formatting from being truncated.

### Changed

- Show citation keys instead of PubMed IDs on the annotation queue.
