---
title: "Update a Case Once"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/keep-cases-current/update-a-case-once/
retrieved: 2026-10-01
---

# Update a Case Once

Refresh a case from its court source **once**, on demand. Use this when you need current docket data now—not on a recurring schedule.

**Reference docs:** [Case Update](../../knowledge-base/case-update.md) (fields, WebSocket, limits), [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md), [Track a case on a schedule](../../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md) (automated refresh instead).

## Before you start

You need:

- A **`caseId`** in your workspace
- A **workspace token** and **`workspaceId`**

Case updates are **asynchronous over HTTP** (submit, then poll) or **synchronous over WebSocket** (submit and receive on one connection).

## Step 1 — Submit an update

**PUT** to [**/workspace/{workspaceId}/caseUpdate**](#):

Submit case update

```Shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseUpdate' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "caseId": "CASEne32920dcecabe"}'
```

Common optional fields:

| Field | Default | Purpose |
| --- | --- | --- |
| **`priorityLevel`** | `level5` | Timeout before failure: `level1` (5 min), `level2` (30 min), `level5` (24 h). |
| **`notifyOnDelay`** | `false` | Notify when status moves to **`DELAYED`**. |
| **`fetchType`** | `fetchNewDocketEntries` | `fetchAllDocketEntries` re-parses the full docket. |
| **`fetchParticipantsIfOlderThanDays`** | `0` | Limit party/counsel re-fetch on federal cases (`0` = always). |

The immediate response is **`status: IN_PROGRESS`**:

Update acknowledgment

```json
{  "object": "CaseUpdate",  "caseId": "CASEne32920dcecabe",  "status": "IN_PROGRESS",  "priorityLevel": "level5",  "startDate": "2025-08-01T11:58:00+00:00",  "lastFetchDate": "2025-07-28T10:30:00+00:00",  "lastFetchDateWithUpdates": "2025-07-15T09:15:00+00:00",  "caseAPI": "/workspace/{workspaceId}/case/CASEne32920dcecabe",  "case": null}
```

## Step 2 — Poll until complete

Poll [**GET /workspace/{workspaceId}/caseUpdate/{caseId}**](#) until **`status`** is terminal:

Poll update status

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseUpdate/{caseId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

| `status` | Meaning |
| --- | --- |
| **`IN_PROGRESS`** | Update running; keep polling. |
| **`DELAYED`** | Court or internal issue; UniCourt retries until **`priorityLevel`** timeout. See **`statusDetails`**. |
| **`COMPLETE`** | Refresh succeeded. Check **`lastFetchDateWithUpdates`**. |
| **`FAILURE`** | Timed out or failed. See **`exception`**. |

When **`COMPLETE`**, read the refreshed case via **`caseAPI`** or [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md). The inline **`case`** object may be partial; **`caseAPI`** is the canonical full payload.

Completed update (excerpt)

```json
{  "object": "CaseUpdate",  "status": "COMPLETE",  "lastFetchDate": "2025-08-01T12:04:00+00:00",  "lastFetchDateWithUpdates": "2025-08-01T12:04:00+00:00",  "caseAPI": "/workspace/{workspaceId}/case/CASEne32920dcecabe"}
```

## Step 3 — WebSocket alternative (optional)

Submit and receive the result on one connection with **`type=workspaceCaseUpdate`**:

Sync case update over WebSocket

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your JWT accessToken>&type=workspaceCaseUpdate&workspaceId={workspaceId}
```

Send the same JSON body as the HTTP **PUT**. Messages use the same **`CaseUpdate`** shape; the connection closes after the final message (or after two hours max).

For monitoring many updates asynchronously, use **`workspaceLiveCallbacks`** or replay from **`workspaceHistoricalCallbacks`** with **`callbackType=caseUpdate`**. See [Set up callbacks](../../common-use-cases/platform/set-up-callbacks.md).

## Step 4 — List recent updates (optional)

Monitor multiple cases with **GET /workspace/{workspaceId}/caseUpdates**:

List recent updates

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseUpdates?lastNDays=7&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Query parameters: **`caseId`**, **`status`**, **`lastNDays`** (1–30, default `1`), **`pageNumber`**. Returns **`caseUpdatePreviewArray`** — most recent status per case in the look-back window.

## PACER cases

Include **`pacerOptions`** at the request root. Set credentials via [PACER API](../../knowledge-base/pacer-api.md). Example and **`additionalPageArray`** pages: [Case Update — PACER options](../../knowledge-base/case-update.md#pacer-options).

## Update vs track vs history

| Goal | Use |
| --- | --- |
| Refresh **once**, right now | **Case Update** (this walkthrough) |
| **Recurring** automatic refresh | [Track a case on a schedule](../../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md) |
| See **what changed** since a date | [See what changed on a case](../../common-use-cases/keep-cases-current/sync-case-history.md) |

## v3 reminders

| v2 | v3 |
| --- | --- |
| `PUT /caseUpdate` | `PUT /workspace/{workspaceId}/caseUpdate` |
| `requestedDate` | `startDate` + `currentTime` |
| `pacerOptions.refreshType` | Root-level `fetchType` |
| Fixed 4-hour delay threshold | Depends on **`priorityLevel`** |

Daily update limits return HTTP **`403`** / `UN203`. See [Case Update — limits](../../knowledge-base/case-update.md#limits-and-errors).
