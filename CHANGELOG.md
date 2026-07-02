# Changelog

All notable changes to this project will be documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- PDF import.
- PDF viewer.
- Supplementary files import.
- Email notification for users added to a project.
- Fix import of large ontologies.
- Flag references that have already been annotated when adding a document to a project.
- Curation only allows renaming the CURIE of proposed (unconfirmed) entities; renaming a confirmed entity is now rejected.
- Curation CURIE rename is now scoped to the caller's project: a curator can no longer rename a proposed entity belonging to a different project (returns 404).
- Renaming a CURIE to one that already exists now returns a clean 409 instead of an internal server error, in both the curation and admin rename endpoints.
- The curation and admin CURIE editors now show the rejection reason inline (e.g. "already in use") and keep the editor open so it can be corrected, instead of failing silently or displaying a raw error payload.
- In the admin panel, a proposed entity's CURIE is now edited by clicking the CURIE itself (the separate "Edit CURIE" button was removed), matching the curation page.
- Renaming a CURIE to an empty/whitespace value is now rejected (422) instead of overwriting the entity and all its annotations with an empty identifier.
- In the admin panel, a proposed entity's Accept/Reject buttons are disabled while a CURIE rename for that entity is in flight, preventing a concurrent mutation.
- Renaming an entity's CURIE now preserves database referential-integrity enforcement; previously it could leave SQLite foreign-key checks disabled on the connection, letting later writes bypass them.
- Saving an annotation is now recorded under the authenticated user and rejected (403) when the caller is not a member of the target project; previously the save request trusted the client-supplied identity and project, allowing a user to attribute annotations to someone else or write into a project they don't belong to.

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
