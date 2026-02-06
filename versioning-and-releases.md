# Versioning and Releases

## Goals
- Deterministic deployments
- Rollback capability
- Clear change history per repo

## Versioning
Use SemVer:
- MAJOR: breaking changes (variable rename, behavior change, removed support)
- MINOR: backward-compatible features
- PATCH: backward-compatible fixes

## Git tags
- Tag releases as: `vX.Y.Z`
- Every release tag MUST have:
  - Detailed commit message describing changes
  - Link to release notes (if applicable)
  - Passing CI checks (lint + tests)

## Dependency pinning
Playbooks and AAP projects MUST pin:
- collections via `requirements.yml` version
- roles via:
  - collection inclusion, or
  - git tags/SHAs when consuming standalone role repos

## Backward compatibility rules
Breaking change requires:
- MAJOR bump
- Explicit migration steps in documentation.
- Optional deprecation window
