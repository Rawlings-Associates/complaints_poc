---
title: "Case Update"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/case-update/
retrieved: 2026-10-01
---

# Case Update

The Case Update API refreshes a case from its court source on demand. Processing is asynchronous over HTTP (submit, then poll) or synchronous over WebSocket (submit and receive the result on the same connection).

See [Update a case once](../common-use-cases/keep-cases-current/update-a-case-once.md) for a full walkthrough. Cases are identified by `caseId` (`CASE`)—see [Object ID Prefixes](../knowledge-base/object-id-prefixes.md).

## Case Update vs Case Track

**Update** when you need a one-off refresh of a case from the court source. **Track** ([Case Track](../knowledge-base/case-track.md)) when you need to schedule recurring updates so UniCourt keeps the case current automatically.

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| PUT | `/workspace/{workspaceId}/caseUpdate` | Submit a case update request (`updateCase`) |
| GET | `/workspace/{workspaceId}/caseUpdate/{caseId}` | Get the latest update status for one case (`getCaseUpdateByCaseId`) |
| GET | `/workspace/{workspaceId}/caseUpdates` | List recent update requests with filters (`getCaseUpdates`) |

## Update status flow

- **IN_PROGRESS** — From submission until the `priorityLevel` timeout or resolution.
- **DELAYED** — Temporary court or internal issues; UniCourt retries until timeout.
- **COMPLETE** — Case refreshed. `lastFetchDate` and `lastFetchDateWithUpdates` are populated; `case` may contain the updated case or use `caseAPI`.
- **FAILURE** — Timeout or unrecoverable error.

Timeout before DELAYED

In v2 documentation, **IN_PROGRESS** was described as moving to **DELAYED** after a fixed four-hour window. In v3, the delay threshold depends on **`priorityLevel`**: 5 minutes (`level1`), 30 minutes (`level2`), or 24 hours (`level5`, default).

## Submitting a case update (HTTP)

Submit a **PUT** to [**/workspace/{workspaceId}/caseUpdate**](#). The flow:

1. Send a request with the target `caseId`.
2. Receive a `CaseUpdate` acknowledgment with `status: IN_PROGRESS`.
3. Poll [**GET /workspace/{workspaceId}/caseUpdate/{caseId}**](#) until `status` is `COMPLETE` or `FAILURE`.

### Request fields

| Field | Required | Description |
| --- | --- | --- |
| `caseId` | Yes | UniCourt case ID to refresh. |
| `priorityLevel` | No | `level1` (5 min), `level2` (30 min), or `level5` (24 h, default). |
| `notifyOnDelay` | No | If `true`, notify when status moves to `DELAYED`. Default `false`. |
| `fetchType` | No | `INCREMENTAL` (default) or `FULL`. |
| `fetchParticipantsIfOlderThanDays` | No | 0–100. Limits how often parties and counsel are re-fetched (federal cases; see spec). `0` always re-fetches. |
| `pacerOptions` | Conditional | Required for PACER cases. See [PACER options](#pacer-options). |

Case update request

```Shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseUpdate' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "caseId": "CASEne32920dcecabe"}'
```

### Response: CaseUpdate

Update acknowledgment (IN_PROGRESS)

```json
{  "object": "CaseUpdate",  "workspaceId": "proj123",  "caseId": "CASEne32920dcecabe",  "priorityLevel": "level5",  "notifyOnDelay": false,  "fetchType": "INCREMENTAL",  "fetchParticipantsIfOlderThanDays": 0,  "pacerOptions": null,  "currentTime": "2025-08-01T12:00:00+00:00",  "startDate": "2025-08-01T11:58:00+00:00",  "status": "IN_PROGRESS",  "statusDetails": null,  "exception": null,  "lastFetchDate": "2025-07-28T10:30:00+00:00",  "lastFetchDateWithUpdates": "2025-07-15T09:15:00+00:00",  "caseAPI": "/workspace/{workspaceId}/case/CASEne32920dcecabe",  "case": null}
```

When complete, poll **GET /workspace/{workspaceId}/caseUpdate/{caseId}** again:

Completed update

```json
{  "object": "CaseUpdate",  "workspaceId": "proj123",  "caseId": "CASEne32920dcecabe",  "priorityLevel": "level5",  "notifyOnDelay": false,  "fetchType": "INCREMENTAL",  "fetchParticipantsIfOlderThanDays": 0,  "pacerOptions": null,  "currentTime": "2025-08-01T12:05:00+00:00",  "startDate": "2025-08-01T11:58:00+00:00",  "status": "COMPLETE",  "statusDetails": null,  "exception": null,  "lastFetchDate": "2025-08-01T12:04:00+00:00",  "lastFetchDateWithUpdates": "2025-08-01T12:04:00+00:00",  "caseAPI": "/workspace/{workspaceId}/case/CASEne32920dcecabe",  "case": {    "object": "Case",    "caseId": "CASEne32920dcecabe",    "caseNumber": "23-CA-002241",    "caseName": "Example v Example"  }}
```

Use **`lastFetchDate`** to see when UniCourt last checked the court source, and **`lastFetchDateWithUpdates`** to see when changes were last found. When the inline `case` object is omitted or truncated, follow **`caseAPI`** for the full v3 case payload.

### When an update is delayed

Delayed update

```json
{  "object": "CaseUpdate",  "workspaceId": "proj123",  "caseId": "CASEne32920dcecabe",  "status": "DELAYED",  "priorityLevel": "level5",  "notifyOnDelay": true,  "statusDetails": {    "object": "StatusDetails",    "issueSource": "COURT",    "issueType": "MAINTENANCE",    "statusAsOn": "2025-06-24T08:15:00+00:00",    "nextRetry": "2025-06-24T08:25:00+00:00",    "details": "Request is delayed as the court source is under maintenance."  },  "exception": null,  "case": null,  "caseAPI": "/workspace/{workspaceId}/case/CASEne32920dcecabe"}
```

### `statusDetails`

| Field | Description |
| --- | --- |
| `issueSource` | `COURT`, `INTERNAL`, or `CLIENT` |
| `issueType` | `MAINTENANCE`, `INTERMITTENT`, or `REPRODUCIBLE` |
| `statusAsOn` | When this status was recorded |
| `nextRetry` | Next retry time (common for `DELAYED`) |
| `details` | Human-readable explanation |

## PACER options

For PACER cases, include `pacerOptions` with at least `pacerUserId`. Configure credentials via [PACER API](../knowledge-base/pacer-api.md).

In v3, **`fetchType`** and **`fetchParticipantsIfOlderThanDays`** belong at the **request root**, not inside `pacerOptions`.

PACER case update request

```json
{  "caseId": "CASEke15dba3978da9",  "fetchType": "INCREMENTAL",  "fetchParticipantsIfOlderThanDays": 30,  "pacerOptions": {    "pacerUserId": "<Your pacerUserId>",    "pacerClientCode": "<Your-pacerClientCode>",    "additionalPageArray": [      {        "page": "associatedCases",        "fetchIfOlderThanDays": 30      },      {        "page": "caseSummary",        "fetchIfOlderThanDays": 15      }    ]  }}
```

Supported `additionalPageArray.page` values: `associatedCases`, `caseSummary`, `listOfCreditors`, `deadlinesAndHearings`.

## Listing recent updates

Use [**GET /workspace/{workspaceId}/caseUpdates**](#) to monitor multiple requests. Query parameters:

- **`caseId`** — Filter to one case.
- **`status`** — `IN_PROGRESS`, `DELAYED`, `COMPLETE`, or `FAILURE`.
- **`lastNDays`** — Look-back window (1–30 days; default `1`). Returns requests submitted in that period; if a case was updated multiple times, only the **most recent** status per case is returned.
- **`pageNumber`** — Pagination.

The response contains `caseUpdatePreviewArray` with `CaseUpdatePreview` objects (status and timestamps without a full inline case).

## Real-time delivery via WebSocket

Submit a case update and receive the result on the same connection using **`type=workspaceCaseUpdate`**:

WebSocket connection

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceCaseUpdate&workspaceId={workspaceId}
```

Send the same JSON body as the HTTP **PUT** request:

WebSocket update request

```json
{  "caseId": "CASEne32920dcecabe"}
```

You receive acknowledgment and completion messages in the same `CaseUpdate` shape as HTTP. The connection closes after the final message (or after a maximum of 2 hours).

v2 WebSocket note

In v2, sync case update used **`type=caseUpdate`** on **`callbacks.unicourt.com`**. v3 uses **`workspaceCaseUpdate`** on **`deep-callbacks.unicourt.com`** with **`workspaceId`**.

For async monitoring of many updates, use **`liveCallbacks`** or **`workspaceLiveCallbacks`** (see [WebSocket Protocol](../knowledge-base/wss.md)). If you miss a callback, use **`historicalCallbacks`** or **`workspaceHistoricalCallbacks`** with `callbackType=caseUpdate`.

## Limits and errors

Daily case-update limits return HTTP `403` with `UN203` / `LIMIT_REACHED`. See [General Error Codes](../knowledge-base/general-error-codes.md) and [Error Management](../knowledge-base/error-codes.md).

## Migration Notes for v2 Integrators

If your integration reads `requestedDate`, nested `pacerOptions.refreshType`, or v2 `case.attorneys` from update responses, these have changed in v3. See the mapping table below.

### `updateCase` — request fields added at root in v3

- `fetchParticipantsIfOlderThanDays`
- `fetchType`
- `notifyOnDelay`
- `priorityLevel`

### `updateCase` — request fields removed from `pacerOptions` in v3

- `pacerOptions.fetchParticipantsIfOlderThanDays` → moved to root `fetchParticipantsIfOlderThanDays`
- `pacerOptions.refreshType` → replaced by root `fetchType` (`INCREMENTAL` / `FULL`)

### `updateCase` / `getCaseUpdateByCaseId` — response fields added in v3

- `workspaceId`
- `currentTime`
- `startDate`
- `fetchType`
- `fetchParticipantsIfOlderThanDays`
- `notifyOnDelay`
- `priorityLevel`
- `lastFetchDate`
- `lastFetchDateWithUpdates`
- `statusDetails`
- `statusDetails.object`
- `statusDetails.issueSource`
- `statusDetails.issueType`
- `statusDetails.statusAsOn`
- `statusDetails.nextRetry`
- `statusDetails.details`

### Response fields removed or replaced in v3

- `requestedDate` → replaced by `startDate` (request time) and `currentTime` (response generation time)
- Embedded `case.attorneys.*` → v3 `Case` uses `counselList` / `counselArray` (see [Understanding the Counsel Object](../knowledge-base/understanding-the-counsel-object.md))
- `case.caseStats.attorneyCount` → `case.caseStats.counselCount` on v3 `Case` objects

When `status` is **COMPLETE**, prefer **`caseAPI`** for the canonical full case if the inline `case` object is null or partial.

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| `PUT /caseUpdate` | `PUT /workspace/{workspaceId}/caseUpdate` | Workspace-scoped on `deep-api.unicourt.com` |
| `GET /caseUpdate/{caseId}` | `GET /workspace/{workspaceId}/caseUpdate/{caseId}` | Workspace-scoped |
| `GET /caseUpdates` | `GET /workspace/{workspaceId}/caseUpdates` | Workspace-scoped; filters use `lastNDays` (not v2 `requestedDate` query on this endpoint) |
| `requestedDate` | `startDate` + `currentTime` | Renamed/split on `CaseUpdate` |
| `pacerOptions.refreshType` | `fetchType` (request root) | Enum values renamed to `INCREMENTAL` / `FULL` |
| `pacerOptions.fetchParticipantsIfOlderThanDays` | `fetchParticipantsIfOlderThanDays` (request root) | Moved out of `pacerOptions` |
| *(none)* | `priorityLevel` | New request/response field |
| *(none)* | `notifyOnDelay` | New request/response field |
| *(none)* | `statusDetails` | New on `CaseUpdate` |
| *(none)* | `lastFetchDate` | New on `CaseUpdate` |
| *(none)* | `lastFetchDateWithUpdates` | New on `CaseUpdate` |
| *(none)* | `workspaceId` | New on `CaseUpdate` |
| `wss://callbacks.unicourt.com?...&type=caseUpdate` | `wss://deep-callbacks.unicourt.com?...&type=workspaceCaseUpdate&workspaceId={workspaceId}` | Host, type, and workspace query param changed |
