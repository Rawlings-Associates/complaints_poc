---
title: "Export a Case"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/get-case-content/export-a-case/
retrieved: 2026-10-01
---

# Export a Case

You already have a **`caseId`** in your workspace and need a **downloadable package** of the case—docket entries, parties, counsel, document metadata, and related objects—as a **ZIP**, not just API pages you scrape one endpoint at a time.

Use **Case Export** when you want an offline/archive bundle, a handoff file for another system, or a snapshot you can store outside UniCourt. To pull individual PDF/TIFF filings instead, see [Getting documents from cases](../../common-use-cases/get-case-content/get-a-case-document.md).

**Reference docs:** [Case Export](../../knowledge-base/case-export.md) (status, limits, WebSocket), [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md), [Set up callbacks](../../common-use-cases/platform/set-up-callbacks.md).

## Before you start

You need:

- A **`caseId`** already in UniCourt for your workspace (from [search](../../common-use-cases/find-and-read-cases/search-for-cases.md), [PACER import](../../common-use-cases/find-and-read-cases/import-a-case-from-pacer.md), or read/update flows)
- A **workspace token** and **`workspaceId`**

Export packages data UniCourt already holds. It does **not** refresh the case from the court—[update](../../common-use-cases/keep-cases-current/update-a-case-once.md) or [track](../../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md) first if you need current docket data in the ZIP.

PACER

You do **not** need PACER credentials to export a federal case that is already in UniCourt.

Base URL: **`https://deep-api.unicourt.com`**.

## Step 1 — Start the export

**GET** [**/workspace/{workspaceId}/caseExport/{caseId}**](#):

Start case export

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseExport/CASEpkca0efb77dfac' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

One **`caseId`** per request. The immediate response is a **`CaseExportCallback`** with **`status: IN_PROGRESS`**:

Export acknowledgment

```json
{  "object": "CaseExportCallback",  "workspaceId": "proj123",  "caseExportCallbackId": "CBCE3SH766729f6024",  "caseId": "CASEpkca0efb77dfac",  "status": "IN_PROGRESS",  "caseExportCallbackAPI": "/workspace/{workspaceId}/caseExport/callbacks/CBCE3SH766729f6024",  "file": null,  "exception": null}
```

Save **`caseExportCallbackId`** (or **`caseExportCallbackAPI`**) for polling. Large cases can take a few minutes.

## Step 2 — Poll until COMPLETE or FAILURE

Poll export callback

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseExport/callbacks/{caseExportCallbackId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

| `status` | Meaning |
| --- | --- |
| **`IN_PROGRESS`** | Job running; keep polling |
| **`COMPLETE`** | ZIP ready — see [Step 4](#step-4--download-and-unpack-the-zip) |
| **`FAILURE`** | Export failed — inspect **`exception`** |

Case export does **not** use **`DELAYED`** (unlike Case Update / Import).

Completed export (excerpt)

```json
{  "object": "CaseExportCallback",  "caseExportCallbackId": "CBCE3SH766729f6024",  "status": "COMPLETE",  "file": {    "object": "ExportFile",    "name": "case/production/demo/CASEpkca0efb77dfac.zip",    "expiryDate": "2024-07-11T06:03:24+00:00",    "fileUrl": "https://ctf.unicourt.com/demo/CASEpkca0efb77dfac.zip?Expires=..."  },  "exception": null}
```

## Step 3 — WebSocket alternative (optional)

Submit and receive the result on one connection with **`type=workspaceCaseExport`**:

Sync case export over WebSocket

```Shell
wss://deep-callbacks.unicourt.com?accessToken=<Your_JWT_accessToken>&type=workspaceCaseExport&workspaceId={workspaceId}
```

Send after connect

```json
{  "caseId": "CASEpkca0efb77dfac"}
```

Messages use the same **`CaseExportCallback`** shape; the connection closes after the final message (or after two hours max). See [Set up callbacks](../../common-use-cases/platform/set-up-callbacks.md) and [Case Export — WebSocket](../../knowledge-base/case-export.md#real-time-delivery-via-websocket).

For many concurrent exports, prefer HTTP submit + your usual callback strategy, or poll **GET .../caseExport/callbacks**.

## Step 4 — Download and unpack the ZIP

When the callback reaches **`COMPLETE`**, the response includes an **`ExportFile`** under **`file`**:

| `ExportFile` field | Use it to… |
| --- | --- |
| **`fileUrl`** | Download the ZIP over HTTPS (tokenized link) |
| **`expiryDate`** | Know when the URL stops working (typically up to about one week) |
| **`name`** | Identify the archive in logs/storage |

1. **Download** the ZIP from **`file.fileUrl`** before **`expiryDate`**. If the link expires, start a new export.
2. **Unzip** the archive.
3. **Inspect** the extracted contents:

  - The top-level folder is the UniCourt **`caseId`** (for example, `CASEgt432aaf72efbb`).
  - Under that folder, subfolders correspond to major sections of the case metadata (parties, docket entries, counsel, documents, and related objects), each containing JSON files.
  - The folder layout mirrors the schema of the UniCourt case object. See [**getCase**](#) in the Case View API for the full structure.

The package is case **metadata** (JSON), not the PDF/TIFF filing files themselves. For document binaries, see [Getting documents from cases](../../common-use-cases/get-case-content/get-a-case-document.md).

## Step 5 — List recent exports (optional)

List export callbacks

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseExport/callbacks?pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Optional filters: **`date`** (`YYYY-MM-DDTHH:MM:SS+ZZ:zz`), **`status`** (`IN_PROGRESS` | `COMPLETE` | `FAILURE`).

## Export vs documents vs full case read

| Goal | Use |
| --- | --- |
| Offline **ZIP of case data** | **Case Export** (this walkthrough) |
| Individual **document files** (PDF/TIFF) | [Getting documents from cases](../../common-use-cases/get-case-content/get-a-case-document.md) |
| Live **API read** of docket/parties | [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md) |
| Fresh data from the court first | [Update a case once](../../common-use-cases/keep-cases-current/update-a-case-once.md) |

## v3 vs v2

| v2 | v3 |
| --- | --- |
| `GET /caseExport/{caseId}` | `GET /workspace/{workspaceId}/caseExport/{caseId}` |
| `GET /caseExport/callbacks/...` | Workspace-scoped callback paths |
| `type=caseExport` on old callbacks host | `type=workspaceCaseExport` on `deep-callbacks.unicourt.com` + **`workspaceId`** |

Daily export limits return HTTP **`403`** / `UN203` / `LIMIT_REACHED`. See [Case Export — limits](../../knowledge-base/case-export.md#limits-and-errors).
