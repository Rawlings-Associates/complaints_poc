---
title: "Case Track"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/case-track/
retrieved: 2026-10-01
---

# Case Track

The Case Track API keeps cases current on a recurring schedule. Each scheduled run refreshes the case from its court source—the same underlying operation as [Case Update](../knowledge-base/case-update.md), but automated rather than one-time.

See [Track a case on a schedule](../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md) for a full walkthrough. Tracked cases are identified by `caseId` (`CASE`)—see [Object ID Prefixes](../knowledge-base/object-id-prefixes.md).

## Case Track vs Case Update

**Track** when you need to schedule recurring updates (hourly, daily, weekly, or monthly). **Update** ([Case Update](../knowledge-base/case-update.md)) when you need a one-off refresh right now.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| PUT | `/workspace/{workspaceId}/caseTrack` | Add or update tracking for a case (`trackCase`) |
| GET | `/workspace/{workspaceId}/caseTrack/{caseId}` | Get tracking configuration and latest run status (`getCaseTrackById`) |
| GET | `/workspace/{workspaceId}/caseTracks` | List tracked cases in a workspace with optional date filters (`getCaseTracks`) |
| GET | `/caseTracks` | List tracked cases across the account (`getCaseTracksRoot`) — **new in v3** |
| DELETE | `/workspace/{workspaceId}/caseTrack/{caseId}` | Stop tracking a case (`removeCaseTrackById`) |

## Track run status flow

Each scheduled refresh is a **track run**. Status for the current and previous runs appears on `currentTrack` and `previousTrack`:

- **IN_PROGRESS** — From the start of the refresh window until it completes or times out.
- **DELAYED** — Temporary court or internal issues; UniCourt retries within the refresh window.
- **COMPLETE** — Case refreshed successfully in this window.
- **FAILURE** — The run timed out or failed with an unrecoverable error.

The **`refreshWindow`** defines both how often tracking runs and the **timeout** for each run. For example, a `2h` window that starts at 9:00 AM must complete before 11:00 AM to count as successful.

## Submitting a case track (HTTP)

Submit a **PUT** to [**/workspace/{workspaceId}/caseTrack**](#). The flow:

1. Send a request with `caseId` and `scheduleOptions`.
2. Receive a `CaseTrackResponse` with `estimatedTracksPerMonth`.
3. Poll [**GET /workspace/{workspaceId}/caseTrack/{caseId}**](#) for configuration, `currentTrack` status, and optional inline `case` data.

Re-submitting **PUT** for the same `caseId` updates the schedule (same endpoint).

### Request fields

| Field | Required | Description |
| --- | --- | --- |
| `caseId` | Yes | UniCourt case ID to track. |
| `scheduleOptions` | Yes | Scheduling configuration (see [Schedule options](#schedule-options)). |
| `notifyOnDelay` | No | If `true`, notify when a track run moves to `DELAYED`. Default `false`. |
| `fetchType` | No | `INCREMENTAL` (default) or `FULL`. |
| `fetchParticipantsIfOlderThanDays` | No | 0–100. Limits how often parties and counsel are re-fetched (federal cases; see spec). `0` always re-fetches. |
| `pacerOptions` | Conditional | Required for PACER cases. See [PACER options](#pacer-options). |

Case track request

```Shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseTrack' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "caseId": "CASEak470fff73ba4e",  "scheduleOptions": {    "refreshWindow": "2h",    "onCourtOptimalHours": true  },  "notifyOnDelay": false}'
```

### Response: CaseTrackResponse

**PUT** returns a short acknowledgment—not the full `CaseTrack` object:

Track added or updated

```json
{  "object": "CaseTrackResponse",  "message": "Added Successfully.",  "estimatedTracksPerMonth": 180}
```

Use **`estimatedTracksPerMonth`** to gauge quota impact before scaling schedules.

### Getting tracking status for one case

Poll **GET /workspace/{workspaceId}/caseTrack/{caseId}** for the full `CaseTrack` object:

CaseTrack (excerpt)

```json
{  "object": "CaseTrack",  "workspaceId": "proj123",  "caseId": "CASEak99a698ea5413",  "scheduleOptions": {    "object": "CaseTrackScheduleOptions",    "refreshWindow": "4h",    "onCourtOptimalHours": true,    "daysOfWeekArray": null,    "startDate": "2023-01-02",    "endDate": "2024-01-02"  },  "notifyOnDelay": false,  "fetchType": "INCREMENTAL",  "fetchParticipantsIfOlderThanDays": 0,  "estimatedTracksPerMonth": 180,  "currentTime": "2025-08-01T12:00:00+00:00",  "currentTrack": {    "object": "CaseTrackDetails",    "status": "COMPLETE",    "refreshWindowStart": "2025-08-01T08:00:00+00:00",    "refreshWindowEnd": "2025-08-01T12:00:00+00:00",    "statusDetails": null,    "exception": null,    "pacerOptions": null  },  "previousTrack": null,  "nextRefreshWindowStart": "2025-08-01T12:00:00+00:00",  "nextRefreshWindowEnd": "2025-08-01T16:00:00+00:00",  "lastFetchDate": "2025-08-01T11:58:00+00:00",  "lastFetchDateWithUpdates": "2025-08-01T11:58:00+00:00",  "caseAPI": "/workspace/{workspaceId}/case/CASEak99a698ea5413",  "case": null}
```

Use **`lastFetchDate`** for when UniCourt last checked the court source, and **`lastFetchDateWithUpdates`** for when changes were last found. When the inline `case` object is omitted, follow **`caseAPI`** for the full v3 case payload.

### `currentTrack.statusDetails`

| Field | Description |
| --- | --- |
| `issueSource` | `COURT`, `INTERNAL`, or `CLIENT` |
| `issueType` | `MAINTENANCE`, `INTERMITTENT`, or `REPRODUCIBLE` |
| `statusAsOn` | When this status was recorded |
| `nextRetry` | Next retry time (common for `DELAYED`) |
| `details` | Human-readable explanation |

## Schedule options

All scheduling fields belong under **`scheduleOptions`** in v3 (not at the request root).

| Field | Description |
| --- | --- |
| **`refreshWindow`** | Tracking frequency and per-run timeout. Allowed values: `1h`, `2h`, `3h`, `4h`, `6h`, `8h`, `12h`, `1d`, `1w`, `2w`, `1m` (case-insensitive). |
| **`onCourtOptimalHours`** | `true`: Monday–Friday, 8:00 AM–8:00 PM in the court's time zone, plus a 12:10 AM run the next day. Allowed windows: `1h`–`12h`. `false`: runs across the full day according to `refreshWindow`; allowed windows include `1d`, `1w`, `2w`, `1m`. |
| **`daysOfWeekArray`** | Optional. Only when `refreshWindow` is `1h`–`12h` or `1d`. Values: `MON`, `TUE`, `WED`, `THU`, `FRI`, `SAT`, `SUN`. Defaults: Mon–Fri when `onCourtOptimalHours` is `true`; Mon–Sun when `false`. |
| **`startDate`** | Optional `YYYY-MM-DD`. First tracking window start in the court's time zone. Defaults to immediate. |
| **`endDate`** | Optional `YYYY-MM-DD`. When tracking stops. Omit for indefinite tracking. |

## Refresh windows for court optimal hours

When `onCourtOptimalHours` is `true`, tracking aligns with court hours (Monday–Friday, 8:00 AM–8:00 PM). An additional window at 12:10 AM the following day (timeout until 8:00 AM) captures late-night filings.

| Refresh Window | Tracking Hours | Estimated Tracks/Day | Available days |
| --- | --- | --- | --- |
| 1h | 8–20, then next day 00:10 | 14 | M–F |
| 2h | 8–20 every 2h, then next day 00:10 | 8 | M–F |
| 3h | 8–20 every 3h, then next day 00:10 | 6 | M–F |
| 4h | 8–20 every 4h, then next day 00:10 | 5 | M–F |
| 6h | 8–20 every 6h, then next day 00:10 | 4 | M–F |
| 8h | 8–16, then next day 00:10 | 3 | M–F |
| 12h | 8, then next day 00:10 | 2 | M–F |

## Refresh windows without court optimal hours

When `onCourtOptimalHours` is `false`, intraday windows (`1h`–`12h`) start at 12:00 AM and recur every X hours. Daily and longer windows (`1d`–`1m`) start at 8:00 PM.

| Refresh Window | Tracking Hours | Estimated Tracks/Day | Available days |
| --- | --- | --- | --- |
| 1h | 0–23 hourly | 24 | M–T–W–T–F–S–S |
| 2h | 0–22 every 2h | 12 | M–T–W–T–F–S–S |
| 3h | 0–21 every 3h | 8 | M–T–W–T–F–S–S |
| 4h | 0–20 every 4h | 6 | M–T–W–T–F–S–S |
| 6h | 0–18 every 6h | 4 | M–T–W–T–F–S–S |
| 8h | 0–16 every 8h | 3 | M–T–W–T–F–S–S |
| 12h | 0–12 every 12h | 2 | M–T–W–T–F–S–S |
| 1d | 20:00 | 1 | M–T–W–T–F–S–S |
| 1w | 20:00 weekly | N/A | N/A |
| 2w | 20:00 biweekly | N/A | N/A |
| 1m | 20:00 monthly | N/A | N/A |

## PACER options

For PACER cases, include `pacerOptions` with at least `pacerUserId`. Configure credentials via [PACER API](../knowledge-base/pacer-api.md).

In v3, **`fetchType`** and **`fetchParticipantsIfOlderThanDays`** belong at the **request root**, not inside `pacerOptions`.

PACER case track request

```json
{  "caseId": "CASEgu33e26e59141b",  "scheduleOptions": {    "onCourtOptimalHours": true,    "refreshWindow": "4h",    "startDate": "2025-01-02"  },  "notifyOnDelay": true,  "fetchType": "INCREMENTAL",  "fetchParticipantsIfOlderThanDays": 30,  "pacerOptions": {    "pacerUserId": "<Your pacerUserId>",    "pacerClientCode": "<Your-pacerClientCode>",    "additionalPageArray": [      {        "page": "associatedCases",        "fetchIfOlderThanDays": 30      }    ]  }}
```

## Listing tracked cases

Use [**GET /workspace/{workspaceId}/caseTracks**](#) to list tracks in a workspace. Optional query parameters:

- **`lastFetchDate`** — Filter by when cases were last fetched (`YYYY-MM-DDTHH:MM:SS+ZZ:zz`).
- **`lastFetchDateWithUpdates`** — Filter by when changes were last found.
- **`pageNumber`** — Pagination.

The response includes `caseTrackPreviewArray` (`CaseTrackPreview` objects) and **`totalEstimatedTracksPerMonth`** (sum of all tracks in the workspace).

Use [**GET /caseTracks**](#) for the same list at account scope (no `workspaceId` in the path).

## Real-time delivery via WebSocket

v3 does **not** expose a dedicated synchronous WebSocket channel for submitting tracks (unlike `workspaceCaseUpdate` or `workspaceCaseImport`). Instead:

- **Per-run results** arrive on **`liveCallbacks`** or **`workspaceLiveCallbacks`** as **`CaseTrack`** messages.
- **Missed callbacks** can be replayed from **`historicalCallbacks`** or **`workspaceHistoricalCallbacks`** with **`callbackType=caseTrack`** (**`CaseTrackPreview`** payloads).

Live callbacks (workspace-scoped)

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceLiveCallbacks&workspaceId={workspaceId}
```

Historical replay with a filter:

Historical case track callbacks

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceHistoricalCallbacks&workspaceId={workspaceId}&callbackType=caseTrack
```

See [WebSocket Protocol](../knowledge-base/wss.md) for connection lifecycle, filters, and error handling.

v2 WebSocket note

In v2, sync case track used **`type=caseTrack`** on **`callbacks.unicourt.com`**. v3 delivers track-run callbacks on **`liveCallbacks`** / **`workspaceLiveCallbacks`**; there is no **`workspaceCaseTrack`** type.

## Best practices

- For intraday windows, prefer `onCourtOptimalHours: true` to avoid off-hours runs. At `1h`, optimal hours reduce runs from 24 to 14 per day.
- Daily, weekly, and longer windows run once per their frequency regardless of optimal hours.
- Use `fetchParticipantsIfOlderThanDays` on frequently tracked federal cases to control participant refresh costs.

## Track quota usage

When you add or update a track, **`estimatedTracksPerMonth`** on the **PUT** response shows projected usage for a 30-day period. The same field appears on each `CaseTrack` or `CaseTrackPreview` from **GET** endpoints or WebSocket callbacks.

**GET /workspace/{workspaceId}/caseTracks** also returns **`totalEstimatedTracksPerMonth`**, summing all tracks in the workspace. Each successful track run counts toward your monthly quota whether the schedule is hourly or monthly.

## Limits and errors

Your account can track a maximum number of cases at once (default: 20). Contact support to raise the limit. Exceeding it returns HTTP `403`:

Case tracking limit reached

```json
{  "object": "Exception",  "code": "UN203",  "message": "LIMIT_REACHED",  "details": "You already have 20 Cases for tracking. Please contact support to increase this limit."}
```

See [General Error Codes](../knowledge-base/general-error-codes.md) and [Error Management](../knowledge-base/error-codes.md) for related codes.

## Migration Notes for v2 Integrators

If your integration nests scheduling under `schedule` or `caseTrackParams`, or reads v2 `case.attorneys` from track responses, these have changed in v3. See the mapping table below.

### `trackCase` — request fields added in v3

- `caseId` (moved to request root)
- `fetchParticipantsIfOlderThanDays` (moved to request root)
- `fetchType` (moved to request root; replaces `caseTrackParams.pacerOptions.refreshType`)
- `notifyOnDelay`
- `pacerOptions` (moved to request root)
- `pacerOptions.additionalPageArray`
- `pacerOptions.pacerClientCode`
- `pacerOptions.pacerUserId`
- `scheduleOptions`
- `scheduleOptions.daysOfWeekArray`
- `scheduleOptions.endDate`
- `scheduleOptions.onCourtOptimalHours`
- `scheduleOptions.refreshWindow`
- `scheduleOptions.startDate`

### `trackCase` — request fields removed in v3

- `caseTrackParams`
- `caseTrackParams.caseId`
- `caseTrackParams.pacerOptions`
- `caseTrackParams.pacerOptions.additionalPageArray`
- `caseTrackParams.pacerOptions.fetchParticipantsIfOlderThanDays`
- `caseTrackParams.pacerOptions.pacerClientCode`
- `caseTrackParams.pacerOptions.pacerUserId`
- `caseTrackParams.pacerOptions.refreshType`
- `schedule`
- `schedule.days`
- `schedule.type`

### `trackCase` — response fields added in v3

- `estimatedTracksPerMonth` (on `CaseTrackResponse`; v3 **PUT** no longer returns a full inline `CaseTrack`)

### `getCaseTrackById` — response fields added in v3

- `workspaceId`
- `currentTime`
- `estimatedTracksPerMonth`
- `fetchParticipantsIfOlderThanDays`
- `fetchType`
- `notifyOnDelay`
- `nextRefreshWindowEnd`
- `nextRefreshWindowStart`
- `scheduleOptions` (with nested scheduling fields)
- `currentTrack`
- `currentTrack.object`
- `currentTrack.pacerOptions`
- `currentTrack.pacerOptions.additionalPageArray`
- `currentTrack.pacerOptions.object`
- `currentTrack.pacerOptions.pacerClientCode`
- `currentTrack.pacerOptions.pacerUserId`
- `currentTrack.refreshWindowEnd`
- `currentTrack.refreshWindowStart`
- `currentTrack.status`
- `currentTrack.statusDetails`
- `currentTrack.statusDetails.object`
- `currentTrack.statusDetails.issueSource`
- `currentTrack.statusDetails.issueType`
- `currentTrack.statusDetails.statusAsOn`
- `currentTrack.statusDetails.nextRetry`
- `currentTrack.statusDetails.details`
- `currentTrack.exception`
- `currentTrack.exception.object`
- `currentTrack.exception.code`
- `currentTrack.exception.message`
- `currentTrack.exception.details`
- `previousTrack` (same nested shape as `currentTrack`)

### `getCaseTracks` — response fields added in v3

- `totalEstimatedTracksPerMonth`

### Response fields removed or replaced in v3

- Embedded `case.attorneys.*` → v3 `Case` uses `counselList` / `counselArray` (see [Understanding the Counsel Object](../knowledge-base/understanding-the-counsel-object.md))
- `case.caseStats.attorneyCount` → `case.caseStats.counselCount`
- Flat request scheduling fields (`refreshWindow`, `onCourtOptimalHours`, etc. at root) → nested under `scheduleOptions`
- `schedule.type` / `schedule.days` → replaced by `scheduleOptions.refreshWindow` and `scheduleOptions.daysOfWeekArray`
- `lastFetchDate` / `lastFetchDateWithUpdates` type: nullable in v2, required strings in v3

When `currentTrack.status` is **COMPLETE**, prefer **`caseAPI`** for the canonical full case if the inline `case` object is null or partial.

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| `PUT /caseTrack` | `PUT /workspace/{workspaceId}/caseTrack` | Workspace-scoped on `deep-api.unicourt.com` |
| `GET /caseTrack/{caseId}` | `GET /workspace/{workspaceId}/caseTrack/{caseId}` | Workspace-scoped |
| `GET /caseTracks` | `GET /workspace/{workspaceId}/caseTracks` | Workspace-scoped list |
| — | `GET /caseTracks` | Account-level list (`getCaseTracksRoot`); new in v3 |
| `DELETE /caseTrack/{caseId}` | `DELETE /workspace/{workspaceId}/caseTrack/{caseId}` | Workspace-scoped |
| `caseTrackParams.caseId` | `caseId` | Top-level on request |
| `caseTrackParams.pacerOptions.refreshType` | `fetchType` | Top-level; enum values are `INCREMENTAL` / `FULL` |
| `caseTrackParams.pacerOptions.fetchParticipantsIfOlderThanDays` | `fetchParticipantsIfOlderThanDays` | Top-level |
| `schedule.type` + `schedule.days` | `scheduleOptions.refreshWindow` + `scheduleOptions.daysOfWeekArray` | Scheduling model restructured |
| `refreshWindow` (request root) | `scheduleOptions.refreshWindow` | Nested under `scheduleOptions` |
| `wss://callbacks.unicourt.com?...&type=caseTrack` | `liveCallbacks` / `workspaceLiveCallbacks` + `callbackType=caseTrack` on historical | No `workspaceCaseTrack` in v3 |
