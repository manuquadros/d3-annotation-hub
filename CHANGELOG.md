# Changelog

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- Entity search now matches per-word prefixes through the FTS index instead of scanning for arbitrary substrings, so it stays fast on large ontologies; searching a mid-word fragment (e.g. "bacterium" to find "Mycobacterium") no longer matches, but any leading or non-leading whole-word prefix still does.
- Large ontology imports are faster: the search index's per-row sync triggers are suppressed during a bulk load and the index is rebuilt once at the end.
- Ontology import streams uploads, so very large ontologies (e.g. NCBITaxon 1.5 GB+) import without exhausting memory; entity/triple progress shows a running count.
- Curation CURIE rename is restricted to proposed (unconfirmed) entities; renaming a confirmed entity is rejected.
- The curation and admin CURIE editors show the rejection reason inline and stay open for correction.
- In the admin panel, a proposed entity's CURIE is edited by clicking the CURIE itself (the "Edit CURIE" button was removed).
- The curation page's CURIE editor now uses the same component as the admin panel, gaining explicit Save/Cancel buttons for consistent behavior.
- Failed create/save/delete actions now show a consistent error message, surfacing the server's reason or a non-JSON gateway/proxy body instead of a generic status or raw JSON.

### Fixed

- Renaming a CURIE to one already in use returns a 409 instead of a server error (curation and admin).
- Renaming a CURIE to an empty/whitespace value is rejected (422).
- In the admin panel, a proposed entity's Accept/Reject buttons are disabled while its CURIE rename is in flight.
- Renaming an entity's CURIE preserves SQLite foreign-key enforcement.
- Renaming a proposed entity's CURIE during curation refreshes the review immediately so the save uses the new identifier.
- Curators can rename a legacy proposed entity with no project scope (NULL `project_id`); the rename adopts it into the current project instead of returning 404.
- A rapid double-Enter in the CURIE editor no longer fires a duplicate rename (which showed a spurious error over the successful save).
- Renaming a proposed entity's CURIE during curation no longer fails with a spurious "already in use" error once the entity has been annotated; the rename now updates every annotation-pointer table atomically.
- Proposing an entity with an existing CURIE returns 409, and an empty/whitespace CURIE is rejected (422).
- Deleting a proposed entity that was already curated no longer errors; its curation rows are removed in the cascade.
- Project managers without global admin rights can open a project's Users, Documents, and Ontologies pages.
- Fixed a memory leak in the annotation view: the highlight cards mounted for each annotation are now torn down when the article re-renders, so editing an entity (rename, synonym change, add/delete) no longer leaves orphaned reactive instances accumulating for the life of the session.
- Autosave (both annotation and curation) now aborts an older in-flight save when a newer one starts, so a slow earlier request can no longer land after a newer one and overwrite it with stale data; a save superseded by rapid editing is no longer shown as a save failure.
- The ontology-detail page now shows a consistent number of rows per page: the first page and every Next/Previous step use the same page size, so classes and triples shown on the initial load are no longer skipped when paging forward.
- Filtering or paging the ontology-detail tables can no longer leave stale rows on screen: when a newer filter or page is requested, a slower earlier request is superseded instead of overwriting the table.
- User email addresses are now unique: the database enforces a UNIQUE constraint on `email`, and user creation refuses a second account for an address that already exists, so duplicate accounts (which made login/identity ambiguous) can no longer be created.
- Editing an already-selected class in the annotation editor's class picker no longer blanks the field and swallows the first keystroke; the typed text is kept and the selection clears only once it stops matching.
- Admin and project-management actions that fail on the server (making/removing a project manager, removing a project member, assigning an ontology, removing a project's ontology) now show the reason instead of silently doing nothing, and their buttons are disabled while the request is in flight to prevent double-submits.

### Security

- Paginated API list endpoints now reject an out-of-range page size (`limit` outside 1–200, or a negative `offset`) with a 422 instead of returning the entire table.
- Saving an annotation is recorded under the authenticated user and rejected (403) for non-members of the target project.
- Proposing an entity or property requires membership in the target project (403 otherwise).
- Curation CURIE rename is scoped to the caller's project (404 for another project's entity).
- Reading a project's OWL/proposed properties, scoping an entity search to a project, and fetching a project reference now require membership in that project (403 otherwise), so a project's privately coined proposed entities/properties are no longer readable by non-members.
- Ontology import is hardened against malicious XML (entity-expansion/XXE and "billion laughs" bombs) while still accepting OBO namespace entities.
- API proxy routes now percent-encode route and query parameters through a shared helper, closing a path/parameter-smuggling hole where a value such as `..%2Fontologies%2F5` could redirect a token-bearing request to a different backend endpoint. The helper also bounds the upstream time-to-first-byte and no longer forwards backend `Set-Cookie` headers to the browser.
- Login no longer leaks whether an email is registered: a failed sign-in now runs the same bcrypt verification whether or not the account exists, so response time can't be used to enumerate accounts.
- Login and change-password are rate-limited per client IP (default 10/minute each, configurable), throttling password brute-force and enumeration attempts.
- Changing a password now enforces a policy: the new password must be at least 8 characters, differ from the current one, and stay within bcrypt's 72-byte limit (so a long password can't be silently truncated).

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
