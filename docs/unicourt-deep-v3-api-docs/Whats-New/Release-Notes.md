---
title: "Release Notes"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/Whats-New/Release-Notes/
retrieved: 2026-10-01
---

# Release Notes

New features and major changes to the DEEP API.

## August 3, 2026

`2026-08-03`Latest

### Workspaces, hearings, and API Security

This release makes workspace creation more flexible, expands how hearings are represented on the case object, adds IP Whitelisting under a renamed **API Security** page in DART, and includes several breaking field and endpoint cleanups. Review **Breaking changes** before you upgrade.

### Breaking changes

Hearings

- **Hearing `location` renamed.** Use `hearingLocation` instead of `location`.
- **`hearingDate` is date-only.** It is now a `date` (`YYYY-MM-DD`) rather than a date-time.

Case payload fields

- **Fetch-date fields removed.** `firstFetchDate` and `lastFetchDate` are no longer returned on Docket Entry, Case Document, Hearing, Cause of Action / Source Charges, Related Case, and Tentative Ruling.
- **Related Case `isVisible` removed.** The Related Case object no longer includes `isVisible`.
- **Case Document repository timing.** `firstFetchDate`, `lastFetchDate`, and `lastFetchDateInUniCourtRepository` are replaced by `lastAddedDateToUniCourtRepository`.
- **Docket entry numbers are strings.** `docketEntryNumber` on Docket Entry (and referenced docket numbers) is now a string rather than an integer.

Case Track, Case Update, Document Orders, and Case Import

- **Case Track and Case Update `fetchType`.** Values are now `INCREMENTAL` and `FULL` (replacing `fetchNewDocketEntries` and `fetchAllDocketEntries`). The same enum applies on the Case object's `lastFetchType`.
- **Document order request trimmed.** `fetchType` and `fetchParticipantsIfOlderThanDays` are removed from Case Document Order requests and callbacks.
- **Case Import request trimmed.** `additionalImportOptions`, `caseClassId`, and `filedDate` are removed from Case Import requests and callbacks.

PACER, master data, and endpoints

- **PACER credentials are account-scoped.** Endpoints move from `/workspace/{workspaceId}/pacerCredential...` to `/pacerCredential` and `/pacerCredential/{pacerUserId}`.
- **Motion outcome master data.** `/masterData/outcome` and `/masterData/outcomeGroup` are replaced by `/masterData/motionOutcome` and `/masterData/motionOutcomeGroup` (including the corresponding `{id}` paths). Tags now use `motionOutcomeIdArray` instead of `outcomeIdArray`.
- **Court coverage endpoint removed.** `/workspace/{workspaceId}/courtCoverage/{courtId}` is no longer available.

Workspaces

- **Workspace ID minimum length.** When you supply a `workspaceId` on `/workspaceCreate`, it must be at least 3 characters (`minLength` updated from 1 to 3).

### Enhancements

Workspaces and hearings

- **Workspace create is more flexible.** On `/workspaceCreate`, `workspaceId` and `description` are now optional.
- **Hearings carry more timing detail.** The Hearing object now includes `hearingId`, `hearingTime`, `hearingTimezone`, `hearingTimeResolution` (enum: `NOT_PROVIDED`, `SOURCE_PROVIDED`, `INFERRED`), and `sourceHearingTime`.

Master data and tentative rulings

- **`MotionTypeGroup` includes category fields.** Responses now include required `motionTypeCategory` and `motionTypeCategoryId`.
- **`tentativeRulingDownloadAPI` can be null.** On `TentativeRulingDownload`, `tentativeRulingDownloadAPI` is now nullable (`string` or `null`).

API Security and IP Whitelisting

- **API Credentials renamed to API Security.** In DART, the former **API Credentials** page is now **API Security**. It still holds your client credentials, and it is also where you configure IP Whitelisting.
- **IP Whitelisting.** Restrict which client IPs may call the DEEP API at the account level and, optionally, per workspace. An empty list allows all IPs; once IPs are added for a scope, only those IPs are permitted. Workspace IPs apply in addition to account IPs and must also appear on the account list. Blocked requests return **403 Forbidden**. See [Allowlisting & IP Whitelisting](../getting-started/white-list.md).

## July 15, 2026

`2026-07-15`Deprecated

### Introducing DEEP v3

DEEP v3 is the next generation of UniCourt's DEEP API platform. It brings a stronger data foundation, a workspace-centric structure, clearer control over how and when you adopt changes, and a broader set of capabilities that are fully supported in GA. Here is what is new.

A stronger data foundation

- **Better entities with improved normalization.** More accurate attorney and law firm records, with far fewer duplicates and fragments, so the entity you match is the entity you meant. When a normalized attorney or law firm ID evolves over time, ID evolution APIs let you follow that change.
- **Attorneys and law firms unified as Counsel.** The old `Attorney` object and its nested law firm array are replaced by a single `Counsel` object, used for both attorneys and law firms and connected to parties and to each other through explicit associations. See [Understanding the Counsel Object](../knowledge-base/understanding-the-counsel-object.md) for the full picture, including what changes if you are migrating from v2.
- **Law firms as a first-class entity.** Query, match, and analyze firms directly, the same way you already work with attorneys.
- **Clearer attorney, law firm, and party models.** Parties link to counsel through party–counsel associations (replacing the older attorney-association shape).
- **Richer master data.** County-oriented courts, counsel roles, motion types and outcomes, case events, case dispositions, procedural activities, and related court-source concepts give you more precise ways to search and filter. Some older master-data families—such as attorney types, causes of action, and charges—are not carried forward in that form.
- **An upgraded case object.** Cases now surface counsel lists (instead of a nested attorneys block), support multiple case types, tentative rulings where available, court-source service status, and clearer cues when full-case pagination is required—along with other quality-of-life improvements.

Workspaces, usage, and authentication

- **Workspaces are now core to the API.** Create and manage workspaces, work within them, and scope nearly all case, search, document, track, update, import, export, PACER, and master-data calls under `/workspace/{workspaceId}/...`.
- **Account and workspace usage APIs.** View daily and monthly usage at the account level and per workspace. Billing-cycle usage endpoints from earlier platform versions are not carried forward; monthly usage is the account-level replacement.
- **Flexible token management.** Account tokens remain available, and workspace-scoped tokens let you limit access to a single workspace. Workspace templates support consistent workspace setup across teams.
- **Full DART integration.** Activity and usage are shared across DEEP and DART, so tracked cases, document orders, and usage line up in either place.

More control over versions and stages

- **Clear API versioning.** Each GA release is identified by its release date. It uses calendar-based versioning, allowing developers and users to instantly know exactly when a new version was released without needing to reference external documentation.
- **Transparent retirement dates that build confidence.** Every GA version moves through three stages: Active, Deprecated, and Retired. The retirement clock for a version starts when its successor is released.
- **GA and Beta stages.** Every endpoint declares its stage, so you always know how stable something is before you build on it.
- **Organized around what you buy.** Endpoints are grouped by activity to mirror packaging, which makes it easier to find exactly what you need.
- **New base URL.** v3 endpoints live at `deep-api.unicourt.com`, with WebSocket callbacks at `deep-callbacks.unicourt.com`.

tip

For how versioning, stages, and support windows work, see [API Versioning](../getting-started/api-versioning.md) and [Working with UniCourt's APIs](../getting-started/working-with-unicourt-apis.md).

Keeping cases current: Case Track and Case Update

- **Case Track as a core capability.** Keep a case current on a schedule you choose—without manual polling or repeated one-off update calls. Schedules support richer windows (including intradaily refresh and court-optimal hours), so you can align refresh cadence with how your workflows consume updates. Track responses also surface clearer run status, delay details, and estimated monthly track volume.
- **Case Update for one-shot refresh.** Request an immediate update when you need a case refreshed outside a track schedule. Updates support processing priority, delay notifications, and structured status details (including when the next retry will occur). Acknowledgment and status payloads are leaner: they no longer embed a full nested case object.

Case Import and Case Export

- **Case Import.** Bring cases into your workspace from supported court sources so you can use them with the rest of the DEEP API. Imports support priority and delay notifications, and successful imports return richer case references for what was brought in.
- **Case Export.** Export case content in a workspace-scoped flow, consistent with the rest of the v3 path model.

Documents

- **Document order failover.** UniCourt uses every available method, including a manual process with people in the loop, to retrieve a document when automation falls short. If a person could pull it from the court site, so can UniCourt.
- **Document orders with more control.** Assign processing priority, request a reorder when you need a fresh copy from the court, and receive clearer delay and status details—including when the next retry will occur. Document metadata also uses a repository / availability model in place of the older in-library flags.
- **Document text search.** Search the OCR'd text across hundreds of millions of downloaded documents to find precise keyword hits inside specific filings.

Matching, history, and tentative rulings

- **Case Match (formerly Case Locator).** Fuzzy-match your internal records to the right UniCourt case, even when those records are incomplete, inconsistent, or missing key identifiers.
- **Normalized Entity Match.** The same fuzzy matching for attorneys and law firms, including mapping several of your internal records for the same entity to a single UniCourt entity.
- **Case History.** A change log across docket entries, hearings, counsel, parties, judges, related cases, documents, counsel associations, and tentative rulings—so you can see what is new on a case and how it has evolved. History shapes that depended on the old attorney model or case decision documents are replaced by counsel- and tentative-ruling-oriented history where applicable.
- **Tentative rulings.** Tentative ruling retrieve, download, and history endpoints replace the earlier case decision document APIs for this class of content.

Entity track and update

- **Attorney and law firm track and update.** Keep normalized attorney and law firm profiles current with track-on-a-schedule and one-shot update flows, scoped to your workspace—alongside case track and update.

Court service status

- **Court service status.** See the current availability of services like case updates and document orders, and be notified when the courts you care about go offline or come back—including live status streams and workspace-scoped status subscriptions over WebSockets.

Delay notifications, priority, and callbacks

- **Faster, more detailed delay and failure notifications.** Case updates, case tracking, document orders, and case imports now tell you sooner and in more detail what is happening, including when the next retry will occur, so you can react in your own system.
- **Priority levels.** Assign processing priority to case updates, case imports, and document orders, so your time-sensitive requests are fulfilled first.
- **WebSocket host and channel model.** Connect to `wss://deep-callbacks.unicourt.com`. Workspace-scoped sync streams use workspace-prefixed types (for example, `workspaceCaseUpdate`) and require a `workspaceId` query parameter. New and expanded channels cover case import, norm attorney update, live and historical callback streams, and court service status. The older REST helper for listing callbacks by date is not carried forward.
- For callback patterns and connection details, see [WebSockets](../knowledge-base/wss.md) and [Handling requests and callbacks](../knowledge-base/handling-requests-callbacks.md).

Legal Analytics

- **Attorney and law firm analytics remain.** Case-count analytics for normalized attorneys and law firms (including opposing-counsel views) continue under the workspace path model.
- **Judge and party analytics removed.** Normalized judge and party search, profiles, association endpoints, and related case-count analytics are not carried forward in v3. Build analytics workflows around counsel (attorneys and law firms) and the remaining case-count dimensions.

PACER

- **Workspace-scoped PACER flows.** PACER credentials, case locator search, and PACER case import follow the same workspace path pattern as the rest of DEEP.

### Where to go next

- [Welcome to DEEP v3](../Whats-New/welcome.md), for a lighter overview of the launch highlights
- [Working with UniCourt's APIs](../getting-started/working-with-unicourt-apis.md), for the foundations: workspaces, authentication, and the conventions you will use everywhere
- [What you can do with DEEP](../getting-started/what-you-can-do-with-deep.md), for learning about which parts of our APIs match what you're trying to build
- [API Versioning](../getting-started/api-versioning.md), for how versions and release stages work
- [Understanding the Counsel Object](../knowledge-base/understanding-the-counsel-object.md), for how attorneys and law firms work together in v3, and what changes if you're migrating from v2
- [Usage limits and billable activities](../getting-started/usage-limits-billable-activities.md), for account and workspace usage
