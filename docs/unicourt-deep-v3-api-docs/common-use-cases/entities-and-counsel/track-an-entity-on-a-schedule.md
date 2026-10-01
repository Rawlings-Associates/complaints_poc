---
title: "Track an Entity on a Schedule"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/entities-and-counsel/track-an-entity-on-a-schedule/
retrieved: 2026-10-01
---

# Track an Entity on a Schedule

Keep a normalized attorney or law firm profile **current automatically**. Each track run refreshes entity data from UniCourt's sources on a schedule you set—useful after you've [matched](../../common-use-cases/entities-and-counsel/search-for-an-entity.md) and [read](../../common-use-cases/entities-and-counsel/read-an-entity-profile.md) an entity and want ongoing bar/contact updates without polling manually.

Entity Track is the counterpart to [Track a case on a schedule](../../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md), with a narrower schedule set (`1W` / `2W` / `1M` only).

**Reference docs:** [**Entity Track API**](#).

## Before you start

You need:

- A **`normAttorneyId`** or **`normLawFirmId`** in your workspace
- A **workspace token** and **`workspaceId`**

Track runs count toward your **entity track quota**. Check **`estimatedTracksPerMonth`** on each **PUT** (and note the HTTP **`403` / `UN203`** limit when you hit the max).

## Step 1 — Start tracking an attorney

**PUT** [**/workspace/{workspaceId}/normAttorneyTrack**](#):

Track a normalized attorney

```Shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorneyTrack' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "normAttorneyId": "QATTyrLx7pedw7KgAi",  "stateCodeArray": ["CA"],  "scheduleOptions": {    "refreshWindow": "1W",    "startDate": "2025-01-02"  },  "notifyOnDelay": false}'
```

| Field | Notes |
| --- | --- |
| **`normAttorneyId`** | Required. Pattern `QATT…` (18 chars). |
| **`stateCodeArray`** | States to refresh. Use `[]` (or omit per schema) for **all** barred states; pass codes like `["CA","NY"]` to limit. |
| **`scheduleOptions.refreshWindow`** | `1W`, `2W`, or `1M` only. |
| **`scheduleOptions.startDate`** / **`endDate`** | Optional `YYYY-MM-DD`. Start must be today or future. |
| **`notifyOnDelay`** | **Not supported.** Omit or set `false`. `true` returns HTTP **`400`**. |

Re-submitting **PUT** for the same ID **updates** the schedule.

NormAttorneyResponse

```json
{  "object": "NormAttorneyResponse",  "message": "Added Successfully.",  "estimatedTracksPerMonth": 4}
```

## Step 2 — Start tracking a law firm

**PUT** [**/workspace/{workspaceId}/normLawFirmTrack**](#):

Track a normalized law firm

```Shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normLawFirmTrack' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "normLawFirmId": "QLAWFATN30Uf235stv",  "scheduleOptions": {    "refreshWindow": "1W",    "startDate": "2025-01-02"  },  "notifyOnDelay": false}'
```

Same **`refreshWindow`** values and **`notifyOnDelay`** rule as attorneys. No **`stateCodeArray`** on law firm track.

## Step 3 — Monitor track runs

Poll the track-by-ID endpoints for schedule config and the latest cycle:

Get attorney track status

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorneyTrack/{normAttorneyId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Get law firm track status

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normLawFirmTrack/{normLawFirmId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

| Status | Meaning |
| --- | --- |
| **`IN_PROGRESS`** | Refresh running inside the current window |
| **`DELAYED`** | Temporary source/internal delay; retries continue until the window ends |
| **`COMPLETE`** | Latest cycle finished successfully |
| **`FAILURE`** | Timed out or unrecoverable error (for example invalid ID) |

Also watch **`lastFetchDate`** and **`lastFetchDateWithUpdates`**. When a run completes, re-read the profile:

- [Read an entity profile](../../common-use-cases/entities-and-counsel/read-an-entity-profile.md)

statusDetails

`statusDetails` may be present on the schema but is typically **`null`** for entity tracks today (no `nextRetry` metadata like some case operations).

## Step 4 — List or stop tracking

**List in a workspace:**

List tracked attorneys

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorneyTracks?pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

List tracked law firms

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normLawFirmTracks?pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Optional filters: **`lastFetchDate`**, **`lastFetchDateWithUpdates`**.

**Account-wide lists** (all workspaces): **GET /normAttorneyTracks** and **GET /normLawFirmTracks** (no workspace path prefix)—new in v3.

**Stop tracking:**

Remove attorney track

```Shell
curl -X 'DELETE' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorneyTrack/{normAttorneyId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Remove law firm track

```Shell
curl -X 'DELETE' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normLawFirmTrack/{normLawFirmId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

## Track vs one-time entity update

| Goal | Use |
| --- | --- |
| Recurring refreshes | **Entity Track** (this walkthrough) |
| Refresh once, right now | **PUT** `/workspace/{workspaceId}/normAttorneyUpdate` or `.../normLawFirmUpdate` (Entity Update API—same status flow, no schedule) |
| Load current profile after a refresh | [Read an entity profile](../../common-use-cases/entities-and-counsel/read-an-entity-profile.md) |

## Entity Track vs Case Track

|  | Entity Track | Case Track |
| --- | --- | --- |
| Refresh from | Bar / entity sources | Court docket sources |
| Windows | `1W`, `2W`, `1M` | Hourly through monthly (`1h`–`12h`, `1d`, `1w`, `2w`, `1m`) |
| `notifyOnDelay: true` | **`400`** — not supported | Supported |
| Extra fields | Attorneys: **`stateCodeArray`** | PACER options, court-optimal hours, days of week |

## v3 vs v2

| v2 | v3 |
| --- | --- |
| `/normAttorneyTrack`, `/normLawFirmTrack` | `/workspace/{workspaceId}/normAttorneyTrack`, `.../normLawFirmTrack` |
| — | Account-level **GET /normAttorneyTracks**, **GET /normLawFirmTracks** |
| Nested analytics links on some track responses | Firm nested `lawFirmAnalyticsAPI` removed; use Analytics View with the norm ID |

Base URL: **`https://deep-api.unicourt.com`**.
