# Speech2Text Roadmap

## Product Direction
Make Speech2Text personalized and production-ready for both local and remote transcription workflows.

## Phase 1: Full Recode for Project Personalization

### 1.0 Rebrand Project

#### Scope
- Rename project identity across extension and service artifacts.
- Update visible product name, identifiers, and user-facing text.
- Keep migration compatibility for existing users where feasible.

#### Deliverables
- Updated branding in docs, metadata, and UI labels.
- Mapping for legacy names/paths to new naming where required.

#### Done Criteria
- New brand appears consistently in extension, service, and documentation.
- Existing installations can be migrated without breaking core flows.

### 1.1 Extension Refactor to Compilable TypeScript

#### Scope
- Move extension code from plain JavaScript to TypeScript.
- Introduce a reproducible build pipeline that outputs GNOME-compatible JavaScript.
- Define strict module boundaries (UI, recording, D-Bus client, settings, insertion).
- Add static typing for settings schema keys, service responses, and UI state transitions.

#### Deliverables
- `tsconfig.json` and build scripts integrated into project workflow.
- Extension source migrated to `src/**/*.ts`.
- Generated build artifacts for packaging and local install.
- Developer docs for build, watch, and release flow.

#### Done Criteria
- Extension builds with zero TypeScript errors.
- Existing features work after migration (record, transcribe, insert/copy, non-blocking mode).
- No runtime regression in GNOME Shell logs during normal flow.

### 1.2 Service Refactor to `asyncio`

#### Scope
- Convert service flow to asynchronous architecture using `asyncio`.
- Remove blocking operations from recording, transcription, and remote forwarding path.
- Introduce clear async boundaries for D-Bus handlers and remote HTTP calls.
- Add graceful shutdown and task cancellation handling.

#### Deliverables
- Async service core with explicit task orchestration.
- Updated CLI/service startup sequence for event-loop lifecycle.
- Error handling and timeout policies for remote requests.

#### Done Criteria
- Service stays responsive during long transcriptions.
- Parallel user actions do not freeze D-Bus endpoints.
- Logs clearly identify async task failures and recovery behavior.

## Phase 2: Native Extension Manager Settings (Wheel Button)

### Scope
- Add preferences UI under GNOME Extension Manager settings.
- Allow user configuration for:
  - Remote server host URL
  - Remote mode enable/disable
  - API key
- Validate and persist settings via GNOME schema.
- Keep compatibility with existing setup dialog behavior during transition.

### Deliverables
- `prefs` implementation connected to extension schema.
- Input validation and safe API key handling.
- Migration notes for existing users.

### Done Criteria
- User can fully configure remote mode from extension manager settings UI.
- Settings are applied without manual `gsettings` commands.
- Invalid host/API key input is handled with clear validation feedback.

## Phase 3: Server-Side Voice Message Storage (S3/MinIO + PostgreSQL)

### Scope
- Add persistent storage for audio records on server side.
- Support MinIO and other S3-compatible providers through storage abstraction.
- Store metadata and processing records in PostgreSQL.
- Keep secure access model for stored voice messages.

### Deliverables
- Storage adapter interface with S3-compatible implementation.
- PostgreSQL schema and migrations for voice-message records.
- Service config for bucket, credentials, retention, and DB connection.
- API endpoints/service methods for creating and reading records.

### Done Criteria
- Voice messages can be uploaded to S3-compatible storage and retrieved by reference.
- Metadata is consistently stored in PostgreSQL.
- Failed uploads/DB writes are recoverable and logged with traceable IDs.

## Phase 4: Extension Layout Selector (`minimal` vs `full`)

### Scope
- Add layout mode selector in extension settings:
  - `full` (current behavior)
  - `minimal` (small widget, no dim screen, seamless insert)
- Build minimal recording UX optimized for speed and low distraction.
- Ensure insertion flow remains robust in minimal mode.

### Deliverables
- New settings key for layout mode.
- Minimal widget UI and behavior implementation.
- Behavior toggles for modal/dim screen and post-processing UX.

### Done Criteria
- User can switch layout mode in settings without reinstall/restart complexity.
- Minimal mode records and inserts text without dim overlay.
- Full mode remains backward-compatible with current UX.

## Suggested Execution Order
1. Complete Phase 1 (TypeScript + `asyncio`) as technical foundation.
2. Implement Phase 2 settings UI to expose remote controls cleanly.
3. Implement Phase 3 persistent storage backend.
4. Implement Phase 4 minimal layout UX as final product polish.

## Cross-Cutting Requirements
- Add integration tests for remote mode and insertion pipeline.
- Add migration notes for users upgrading from current version.
- Define observability baseline: structured logs, error IDs, latency metrics.
- Keep secrets out of repo; use environment variables for API keys and storage credentials.
