# Qev staging v2 isolated candidate

Local-only candidate. This is intentionally not integrated into the site.

V2 stages use the disjoint `qev-stage-v2-<uuid>` namespace and lock name
`qev-stage-v2:<uuid>`. Ownership is acquired before directory creation and held
from staging through selected-bundle disposal. Legacy v1 tabs use other names
and cannot own or delete v2 stages; v2 never enumerates or deletes v1 stages.
Consequently abandoned v1 data is not recoverable safely while old tabs may
still run. Explicit cleanup only accepts a v2 name and requires its v2 lock.

The browser File System Access API and Web Locks API are required. There is no
fallback that weakens isolation. Limits remain 2,000,000,000 bytes per file and
3,000,000,000 bytes total. This candidate does not authenticate manifests.

Run deterministic tests with `node --test test/staging.test.mjs`.

## Current handoff

This is an unintegrated local research draft, not a published browser download. Its deterministic tests use simulated storage, locks, and runtime sessions; real browser multi-tab behavior, full-size downloads, model provenance and release rights remain unverified. Run both suites with `node --test test/staging.test.mjs test/prototype-stage-ui.test.mjs`. Do not publish model assets based on these tests.
