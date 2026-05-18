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

## [0.1.4]

### Added

- Retrieve PubMed abstract when fulltext is not available via PMC.

## [0.1.3] - 2026-05-13

### Added

- Managers can remove references from a project.

### Fixed

- Entity and class search suggestions respect prefix matches. Prefix matches > contains-only matches, and preferred-name matches > synonym-only matches.
- Prevent titles containing inline formatting from being truncated.

### Changed

- Show citation keys instead of PubMed IDs on the annotation queue.
