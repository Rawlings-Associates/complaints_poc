---
title: "Track a Case on a Schedule"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/keep-cases-current/track-a-case-on-a-schedule/
retrieved: 2026-10-01
---

# Track a Case on a Schedule

Keep a case refreshed automatically on a recurring schedule. Each **track run** pulls updates from the court source—the same underlying refresh as [Case Update](../../knowledge-base/case-update.md), but on a timer you configure.

**Reference docs:** [Case Track](../../knowledge-base/case-track.md) (schedule options, quotas, WebSocket details), [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md), [Update a case once](../../common-use-cases/keep-cases-current/update-a-case-once.md) (one-time refresh instead of scheduled).

## Before you start

You need:

- A **`caseId`** already in your workspace (from [Search for cases](../../common-use-cases/find-and-read-cases/search-for-cases.md), [Import a case from PACER](../../common-use-cases/find-and-read-cases/import-a-case-from-pacer.md), or [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md))
- A **workspace token** and **`workspaceId`**

Track runs count toward your **monthly track quota**. Check **`estimatedTracksPerMonth`** before scaling aggressive schedules.

## Step 1 — Add or update tracking

Submit **PUT** to [**/workspace/{workspaceId}/caseTrack**](#) with **`caseId`** and **`scheduleOptions`**.

Start tracking a case

```Shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseTrack' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "caseId": "CASEak470fff73ba4e",  "scheduleOptions": {    "refreshWindow": "2h",    "onCourtOptimalHours": true  },  "notifyOnDelay": false}'
```

Re-submitting **PUT** for the same **`caseId`** updates the schedule.

### Schedule options (essentials)

All scheduling fields live under **`scheduleOptions`** in v3:

| Field | Purpose |
| --- | --- |
| **`refreshWindow`** | How often runs occur **and** the timeout for each run (`1h`–`12h`, `1d`, `1w`, `2w`, `1m`). |
| **`onCourtOptimalHours`** | `true` — weekdays 8 AM–8 PM in the court time zone (recommended for intraday windows). `false` — runs across the full day. |
| **`daysOfWeekArray`** | Optional restrict days (`MON`–`SUN`). |
| **`startDate`** / **`endDate`** | Optional tracking window (`YYYY-MM-DD`). |

Full window tables and examples: [Case Track — schedule options](../../knowledge-base/case-track.md#schedule-options).

### Response

**PUT** returns a short acknowledgment:

CaseTrackResponse

```json
{  "object": "CaseTrackResponse",  "message": "Added Successfully.",  "estimatedTracksPerMonth": 180}
```

Use **`estimatedTracksPerMonth`** to estimate quota impact. Workspace totals are available from **GET /workspace/{workspaceId}/caseTracks** (`totalEstimatedTracksPerMonth`).

## Step 2 — Monitor track runs

Poll [**GET /workspace/{workspaceId}/caseTrack/{caseId}**](#) for configuration and run status:

Get tracking status

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseTrack/{caseId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Each run appears on **`currentTrack`** (and **`previousTrack`** when applicable):

| `currentTrack.status` | Meaning |
| --- | --- |
| **`IN_PROGRESS`** | Refresh window open; run not finished yet. |
| **`DELAYED`** | Court or internal issue; UniCourt retries within the window. Check **`statusDetails`**. |
| **`COMPLETE`** | Case refreshed successfully this window. |
| **`FAILURE`** | Timed out or unrecoverable error. Check **`exception`**. |

CaseTrack excerpt — successful run

```json
{  "object": "CaseTrack",  "caseId": "CASEak99a698ea5413",  "estimatedTracksPerMonth": 180,  "currentTrack": {    "object": "CaseTrackDetails",    "status": "COMPLETE",    "refreshWindowStart": "2025-08-01T08:00:00+00:00",    "refreshWindowEnd": "2025-08-01T12:00:00+00:00"  },  "lastFetchDate": "2025-08-01T11:58:00+00:00",  "lastFetchDateWithUpdates": "2025-08-01T11:58:00+00:00",  "caseAPI": "/workspace/{workspaceId}/case/CASEak99a698ea5413"}
```

- **`lastFetchDate`** — when UniCourt last checked the court source
- **`lastFetchDateWithUpdates`** — when changes were last detected
- **`nextRefreshWindowStart`** / **`nextRefreshWindowEnd`** — when the next run is scheduled

When **`currentTrack.status`** is **`COMPLETE`**, follow **`caseAPI`** for the updated case (see [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md)).

## Step 3 — Receive run results (optional)

Instead of polling **GET /workspace/{workspaceId}/caseTrack/{caseId}**, subscribe to **`workspaceLiveCallbacks`** on **`deep-callbacks.unicourt.com`**. Track run payloads arrive as **`CaseTrack`** messages. Replay missed runs from **`workspaceHistoricalCallbacks`** with **`callbackType=caseTrack`** (**`CaseTrackPreview`** payloads).

See [Set up callbacks](../../common-use-cases/platform/set-up-callbacks.md) and [Case Track — WebSocket](../../knowledge-base/case-track.md#real-time-delivery-via-websocket).

## Step 4 — List or stop tracking

**List tracks in a workspace:**

List tracked cases

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseTracks?pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Optional filters: **`lastFetchDate`**, **`lastFetchDateWithUpdates`**.

**Stop tracking:**

Remove case track

```Shell
curl -X 'DELETE' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseTrack/{caseId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Account-wide listing (all workspaces): **GET /caseTracks** — see [Case Track](../../knowledge-base/case-track.md#listing-tracked-cases).

## PACER cases

Include **`pacerOptions`** on the **PUT** body (at the request root, not inside `scheduleOptions`). Configure credentials via [PACER API](../../knowledge-base/pacer-api.md).

## Track vs one-time update

| Goal | Use |
| --- | --- |
| Recurring automatic refresh | **Case Track** (this walkthrough) |
| Refresh once, right now | [Update a case once](../../common-use-cases/keep-cases-current/update-a-case-once.md) |
| Only changes since last check | [See what changed on a case](../../common-use-cases/keep-cases-current/sync-case-history.md) |

## v3 reminders

| v2 | v3 |
| --- | --- |
| `schedule.type` + `schedule.days` | `scheduleOptions.refreshWindow` + `scheduleOptions.daysOfWeekArray` |
| `caseTrackParams.caseId` | Top-level `caseId` |
| `PUT /caseTrack` | `PUT /workspace/{workspaceId}/caseTrack` |
