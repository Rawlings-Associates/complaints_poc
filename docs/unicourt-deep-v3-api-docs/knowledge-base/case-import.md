---
title: "Case Import"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/case-import/
retrieved: 2026-10-01
---

# Case Import

The Case Import API pulls case data from a court source on demand when the case is not already in UniCourt. Processing is asynchronous: you submit an import request, receive a `caseImportCallbackId`, then poll the callback endpoint or listen on WebSocket for the result.

Use this API for **state and local court sources** supported in the [Case Import Glossary](/res-deep/assets/deep-v3-api-doc/glossaries/caseimport-glossary). To import a **PACER** case by court and case number, use the PACER import endpoint in [PACER API](../knowledge-base/pacer-api.md) instead.

See [Import a case from PACER](../common-use-cases/find-and-read-cases/import-a-case-from-pacer.md) for a PACER import walkthrough. A dedicated walkthrough for court-source case import is not yet published; use the examples below for basic requests. Callback and case IDs use fixed prefixes (`CBCI`, `CASE`)—see [Object ID Prefixes](../knowledge-base/object-id-prefixes.md).

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| PUT | `/workspace/{workspaceId}/caseImport` | Submit a case import request (`importCase`) |
| GET | `/workspace/{workspaceId}/caseImport/callbacks` | List import callbacks with filters (`getCaseImportCallbacks`) |
| GET | `/workspace/{workspaceId}/caseImport/callbacks/{caseImportCallbackId}` | Retrieve one callback by ID (`getCaseImportCallbackById`) |

## Import status flow

- **IN_PROGRESS** — From submission until timeout or resolution.
- **DELAYED** — Temporary court or internal issues; UniCourt retries until the `priorityLevel` timeout.
- **COMPLETE** — Import finished. One or more entries may appear in `importedCaseArray`.
- **FAILURE** — Timeout or unrecoverable error (for example, case unavailable at the court source).

## Placing a case import (HTTP)

Submit a **PUT** to [**/workspace/{workspaceId}/caseImport**](#). The flow:

1. Send a request with `caseNumber` and court context (`courtSourceId`, `courtId`, or both — see [Request fields](#request-fields)).
2. Receive a `CaseImportCallback` acknowledgment with `status: IN_PROGRESS` and a `caseImportCallbackId`.
3. Poll [**GET /workspace/{workspaceId}/caseImport/callbacks/{caseImportCallbackId}**](#) or use [WebSocket](#real-time-delivery-via-websocket) until `status` is `COMPLETE` or `FAILURE`.

### Request fields

| Field | Required | Description |
| --- | --- | --- |
| `caseNumber` | Yes | Case number as filed at the court (format varies by source; see glossary). |
| `courtSourceId` | Conditional | Court source ID (`CTSS…`). Use alone or with `courtId` depending on source requirements. |
| `courtId` | Conditional | Specific court ID (`CORT…`) when the source requires it. |
| `caseClassId` | No | Case class when required by the source. |
| `filedDate` | No | Filing date when required to disambiguate the case. |
| `additionalImportOptions` | No | Source-specific options (see glossary for courts that require a `key`). |
| `priorityLevel` | No | `level1` (5 min), `level2` (30 min), or `level5` (24 h, default). |
| `notifyOnDelay` | No | If `true`, receive notification when status moves to `DELAYED`. Default `false`. |

You can identify the court context in three common ways:

1. `caseNumber` + `courtSourceId`
2. `caseNumber` + `courtId`
3. `caseNumber` + `courtSourceId` + `courtId`

Case import request

```Shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseImport' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "caseNumber": "728148/2024",  "courtSourceId": "CTSS4e01a69e1643e2"}'
```

### Response: the import callback

The immediate response is a `CaseImportCallback` object:

Import acknowledgment (IN_PROGRESS)

```json
{  "object": "CaseImportCallback",  "workspaceId": "proj123",  "caseImportCallbackId": "CBCIvfed3698d6df05",  "caseNumber": "728148/2024",  "courtId": null,  "courtSourceId": "CTSS4e01a69e1643e2",  "caseClassId": null,  "filedDate": null,  "additionalImportOptions": null,  "priorityLevel": "level5",  "notifyOnDelay": false,  "currentTime": "2024-11-29T12:34:56+00:00",  "startDate": "2024-11-29T12:30:00+00:00",  "status": "IN_PROGRESS",  "statusDetails": null,  "exception": null,  "callbackGeneratedDate": null,  "importedCaseArray": []}
```

When the import completes, poll the callback endpoint again (or wait for WebSocket delivery):

Completed import (single case, inline Case object)

```json
{  "object": "CaseImportCallback",  "workspaceId": "proj123",  "caseImportCallbackId": "CBCIvfed3698d6df05",  "caseNumber": "728148/2024",  "courtId": "CORT5dsQDAuw9ctWLp",  "courtSourceId": "CTSS4e01a69e1643e2",  "caseClassId": "CSCLNjbKTN7Yfo2wdb",  "filedDate": "2019-08-01T00:00:00+00:00",  "additionalImportOptions": null,  "priorityLevel": "level5",  "notifyOnDelay": false,  "currentTime": "2024-11-29T12:40:00+00:00",  "startDate": "2024-11-29T12:30:00+00:00",  "status": "COMPLETE",  "statusDetails": null,  "exception": null,  "callbackGeneratedDate": "2024-11-29T12:39:00+00:00",  "importedCaseArray": [    {      "object": "CaseImportedDetails",      "caseId": "CASEgg0d4433e4a773",      "caseAPI": "/workspace/{workspaceId}/case/CASEgg0d4433e4a773",      "case": {        "object": "Case",        "caseId": "CASEgg0d4433e4a773",        "caseNumber": "728148/2024",        "caseName": "Example v Example"      }    }  ]}
```

Multiple matches

If an import resolves to **more than one** case, the callback does **not** include full `case` objects in `importedCaseArray`. Each entry returns `caseId` and `caseAPI` only. Follow `caseAPI` to fetch the full case with **GET /workspace/{workspaceId}/case/{caseId}**.

### When an import is delayed

Delayed import

```json
{  "object": "CaseImportCallback",  "workspaceId": "proj123",  "caseImportCallbackId": "CBCI63f481489xjSE0",  "caseNumber": "728148/2024",  "courtSourceId": "CTSS4e01a69e1643e2",  "status": "DELAYED",  "priorityLevel": "level5",  "notifyOnDelay": true,  "statusDetails": {    "object": "StatusDetails",    "issueSource": "COURT",    "issueType": "MAINTENANCE",    "statusAsOn": "2025-06-24T08:15:00+00:00",    "nextRetry": "2025-06-24T08:25:00+00:00",    "details": "Request is delayed as the court source is under maintenance."  },  "exception": null,  "importedCaseArray": []}
```

### `statusDetails`

Populated for **DELAYED** or **FAILURE**; usually `null` for **IN_PROGRESS** or **COMPLETE**.

| Field | Description |
| --- | --- |
| `issueSource` | `COURT`, `INTERNAL`, or `CLIENT` |
| `issueType` | `MAINTENANCE`, `INTERMITTENT`, or `REPRODUCIBLE` |
| `statusAsOn` | When this status was recorded |
| `nextRetry` | Next retry time (common for `DELAYED`; often `null` on `FAILURE`) |
| `details` | Human-readable explanation |

## Listing recent imports

Use [**GET /workspace/{workspaceId}/caseImport/callbacks**](#) to review multiple callbacks. Query parameters:

- **`callbackGeneratedDate`** — Filter by callback generation time (within the last 30 days).
- **`startDate`** — Filter by when the import was requested (within the last 30 days).
- **`status`** — `IN_PROGRESS`, `DELAYED`, `COMPLETE`, or `FAILURE` (omit for all).
- **`pageNumber`** — Pagination.

## Real-Time Delivery via WebSocket

Instead of polling, submit import requests and receive callbacks over WebSocket using **`type=workspaceCaseImport`**:

WebSocket connection

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceCaseImport&workspaceId={workspaceId}
```

Send the same JSON body as the HTTP **PUT** request:

WebSocket import request

```json
{  "caseNumber": "728148/2024",  "courtSourceId": "CTSS4e01a69e1643e2"}
```

You receive acknowledgment and completion messages in the same `CaseImportCallback` shape as HTTP. The connection closes after the final callback (or after a maximum of 2 hours).

Sync vs async streams

**`workspaceCaseImport`** is a synchronous-style channel: one import request per message, connection closes when done. To monitor many imports across operations, use **`liveCallbacks`** or **`workspaceLiveCallbacks`** (see [WebSocket Protocol](../knowledge-base/wss.md)).

v2 WebSocket note

In v2, sync case import used **`type=caseImport`** on **`callbacks.unicourt.com`**. v3 uses **`workspaceCaseImport`** on **`deep-callbacks.unicourt.com`** with a **`workspaceId`** query parameter.

## Limits and errors

Daily import limits return HTTP `403` with code `UN203` / `LIMIT_REACHED` before the request is accepted. Per-source limits may surface on the callback with `status: FAILURE` and an `exception` object.

See [General Error Codes](../knowledge-base/general-error-codes.md) for the shared code catalog and [Error Management](../knowledge-base/error-codes.md) for handling guidance.

Supported court sources

For court source IDs and jurisdiction-specific case number formats, see the [Case Import Glossary](/res-deep/assets/deep-v3-api-doc/glossaries/caseimport-glossary).

## Migration Notes for v2 Integrators

If your integration currently reads v2 case import paths, `courtServiceStatusId`, or nullable `importedCaseArray` shapes, these have changed in v3. See the mapping table below.

### Response fields added in v3 (`importCase`, `getCaseImportCallbackById`)

- `workspaceId`
- `importedCaseArray[].object`
- `importedCaseArray[].caseId`
- `importedCaseArray[].caseAPI`
- `importedCaseArray[].case`

### Type changes

- `importedCaseArray`: in v2 could be `array` or `null`; in v3 it is always an **array** (may be empty while `IN_PROGRESS`).

### Request / callback field renames

- `courtServiceStatusId` → `courtSourceId` (same `CTSS…` identifier prefix; name aligned with court **source** master data in v3)

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| `PUT /caseImport` | `PUT /workspace/{workspaceId}/caseImport` | Workspace-scoped on `deep-api.unicourt.com` |
| `GET /caseImport/callbacks` | `GET /workspace/{workspaceId}/caseImport/callbacks` | Workspace-scoped |
| `GET /caseImport/callbacks/{caseImportCallbackId}` | `GET /workspace/{workspaceId}/caseImport/callbacks/{caseImportCallbackId}` | Workspace-scoped |
| `courtServiceStatusId` | `courtSourceId` | Renamed; glossary tables use court source IDs |
| `importedCaseArray` (nullable array) | `importedCaseArray` (array) | Always present; empty until matches are known |
| *(none)* | `importedCaseArray[].caseAPI` | Link to fetch case when full `case` object is omitted |
| *(none)* | `importedCaseArray[].case` | Inline `Case` when a single match is imported |
| *(none)* | `workspaceId` | On every `CaseImportCallback` |
| `wss://callbacks.unicourt.com?...&type=caseImport` | `wss://deep-callbacks.unicourt.com?...&type=workspaceCaseImport&workspaceId={workspaceId}` | Host, type, and workspace query param changed |
