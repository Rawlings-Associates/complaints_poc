---
title: "Case Export"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/case-export/
retrieved: 2026-10-01
---

# Case Export

The Case Export API packages a case's full data—docket entries, parties, counsel, documents metadata, and related objects—into a downloadable ZIP file. Processing is asynchronous over HTTP (submit, then poll) or synchronous over WebSocket (submit and receive the result on the same connection).

See [Export a case](../common-use-cases/get-case-content/export-a-case.md) for a full walkthrough. Case and callback IDs use fixed prefixes (`CASE`, `CBCE`)—see [Object ID Prefixes](../knowledge-base/object-id-prefixes.md).

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/workspace/{workspaceId}/caseExport/{caseId}` | Start an export for one case (`exportCase`) |
| GET | `/workspace/{workspaceId}/caseExport/callbacks` | List export callbacks with filters (`getCaseExportCallbacks`) |
| GET | `/workspace/{workspaceId}/caseExport/callbacks/{caseExportCallbackId}` | Retrieve one callback by ID (`getCaseExportCallbackById`) |

## Export status flow

- **IN_PROGRESS** — Export job accepted and running.
- **COMPLETE** — ZIP file ready. `file.fileUrl` contains a tokenized download link.
- **FAILURE** — Export could not be completed (for example, invalid `caseId`, timeout, or internal error). Inspect `exception`.

Case export does not use a **DELAYED** status (unlike Case Update or Case Import).

## Exporting a case (HTTP)

Submit a **GET** to [**/workspace/{workspaceId}/caseExport/{caseId}**](#). The flow:

1. Send a request with the target `caseId` in the path.
2. Receive a `CaseExportCallback` acknowledgment with `status: IN_PROGRESS` and a `caseExportCallbackId`.
3. Poll [**GET /workspace/{workspaceId}/caseExport/callbacks/{caseExportCallbackId}**](#) or use [WebSocket](#real-time-delivery-via-websocket) until `status` is `COMPLETE` or `FAILURE`.

PACER cases

You do not need PACER credentials to export a PACER case. Export works the same way for state, local, and federal cases already in UniCourt.

Case export request

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseExport/CASEpkca0efb77dfac' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

### Response: export acknowledgment

Export acknowledgment (IN_PROGRESS)

```json
{  "object": "CaseExportCallback",  "workspaceId": "proj123",  "caseExportCallbackId": "CBCE3SH766729f6024",  "caseId": "CASEpkca0efb77dfac",  "callbackGeneratedDate": null,  "status": "IN_PROGRESS",  "caseExportCallbackAPI": "/workspace/{workspaceId}/caseExport/callbacks/CBCE3SH766729f6024",  "file": null,  "exception": null}
```

Allow a few minutes for large cases before polling the callback endpoint again.

### Completed export

When `status` is **COMPLETE**, the callback includes an **`ExportFile`** object:

Completed export

```json
{  "object": "CaseExportCallback",  "workspaceId": "proj123",  "caseExportCallbackId": "CBCE3SH766729f6024",  "caseId": "CASEpkca0efb77dfac",  "callbackGeneratedDate": "2024-07-04T06:03:24+00:00",  "status": "COMPLETE",  "caseExportCallbackAPI": "/workspace/{workspaceId}/caseExport/callbacks/CBCE3SH766729f6024",  "file": {    "object": "ExportFile",    "name": "case/production/demo/CASEpkca0efb77dfac.zip",    "expiryDate": "2024-07-11T06:03:24+00:00",    "fileUrl": "https://ctf.unicourt.com/demo/CASEpkca0efb77dfac.zip?Expires=..."  },  "exception": null}
```

Download the ZIP from **`file.fileUrl`** before **`file.expiryDate`**. Links are tokenized and typically valid for up to one week; request a new export if the link expires.

| `ExportFile` field | Description |
| --- | --- |
| `name` | Storage path / filename for the export archive |
| `fileUrl` | Tokenized HTTPS URL to download the ZIP |
| `expiryDate` | When the download URL expires |

One case per request

Only one `caseId` can be exported per API call.

## Listing export callbacks

Use [**GET /workspace/{workspaceId}/caseExport/callbacks**](#) to retrieve callbacks by date or status. Query parameters:

- **`date`** — Callbacks for a given timestamp (`YYYY-MM-DDTHH:MM:SS+ZZ:zz`).
- **`status`** — `IN_PROGRESS`, `COMPLETE`, or `FAILURE` (omit for all).
- **`pageNumber`** — Pagination.

The response is a `CaseExportCallbackListResponse` with a `callbackArray` of `CaseExportCallback` objects.

## Real-time delivery via WebSocket

Submit an export and receive the result on the same connection using **`type=workspaceCaseExport`**:

WebSocket connection

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceCaseExport&workspaceId={workspaceId}
```

Send the case ID as JSON after the connection opens:

WebSocket export request

```json
{  "caseId": "CASEpkca0efb77dfac"}
```

You receive acknowledgment and completion messages in the same `CaseExportCallback` shape as HTTP. The connection closes after the final message (or after a maximum of 2 hours).

Sync vs async streams

**`workspaceCaseExport`** is a synchronous-style channel: one export request per message. To monitor many exports, poll **GET /workspace/{workspaceId}/caseExport/callbacks** or open additional sync connections. Missed export callbacks are not replayed via historical `callbackType=caseExport` in v3 — use the HTTP callback list or the sync channel. See [WebSocket Protocol](../knowledge-base/wss.md).

v2 WebSocket note

In v2, sync case export used **`type=caseExport`** on **`callbacks.unicourt.com`**. v3 uses **`workspaceCaseExport`** on **`deep-callbacks.unicourt.com`** with a **`workspaceId`** query parameter.

## Limits and errors

Daily export limits return HTTP `403` with `UN203` / `LIMIT_REACHED` (for example, 100 exports per day). Failures on an accepted job surface on the callback with `status: FAILURE` and an `exception` object.

See [General Error Codes](../knowledge-base/general-error-codes.md) for the shared code catalog and [Error Management](../knowledge-base/error-codes.md) for handling guidance.

## Migration Notes for v2 Integrators

If your integration uses v2 export paths or omits `workspaceId` on callbacks, update to the workspace-scoped endpoints below.

### `exportCase` / `getCaseExportCallbackById` — response fields added in v3

- `workspaceId`

### `getCaseExportCallbacks`

- Each entry in `callbackArray` includes `workspaceId` (same `CaseExportCallback` shape as other export endpoints).

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| `GET /caseExport/{caseId}` | `GET /workspace/{workspaceId}/caseExport/{caseId}` | Workspace-scoped on `deep-api.unicourt.com` |
| `GET /caseExport/callbacks` | `GET /workspace/{workspaceId}/caseExport/callbacks` | Workspace-scoped |
| `GET /caseExport/callbacks/{caseExportCallbackId}` | `GET /workspace/{workspaceId}/caseExport/callbacks/{caseExportCallbackId}` | Workspace-scoped |
| *(none)* | `workspaceId` | On every `CaseExportCallback` |
| `wss://callbacks.unicourt.com?...&type=caseExport` | `wss://deep-callbacks.unicourt.com?...&type=workspaceCaseExport&workspaceId={workspaceId}` | Host, type, and workspace query param changed |
| `callbackType=caseExport` on historical WSS | *(not a v3 historical filter)* | Replay exports via HTTP **GET /workspace/{workspaceId}/caseExport/callbacks** or sync **`workspaceCaseExport`** |
