---
title: "Read a Full Case"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/find-and-read-cases/read-a-full-case/
retrieved: 2026-10-01
---

# Read a Full Case

Pull a case's metadata, participants, docket, and document list from **Case View** APIs. Start with a **`caseId`** from [Search for cases](../../common-use-cases/find-and-read-cases/search-for-cases.md) (or from import/update flows).

**Reference docs:** [Pagination](../../knowledge-base/pagination.md) (sub-resource lists), [Understanding the Counsel Object](../../knowledge-base/understanding-the-counsel-object.md), [Document Orders](../../knowledge-base/document-orders.md) (download vs order paths).

Spec: [**Case View API**](#).

## Before you start

Use a **workspace token** and your **`workspaceId`**. Base URL: **`https://deep-api.unicourt.com`**.

## Step 1 — Fetch the case record

Get case by caseId

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/case/{caseId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

The **`Case`** object is the case shell: caption, filing date, court, status, and counts. It also embeds **previews** of parties, counsel, docket entries, and documents when the case is small enough.

Excerpt — Case object

```json
{  "object": "Case",  "caseId": "CASEar7a26f15e76cf",  "caseNumber": "18STPB11082",  "caseName": "HUANG, AMY - DECEDENT",  "filedDate": "2018-12-05T00:00:00+00:00",  "courtSourceId": "CTSSV4vCEaKrhysQPq",  "caseTypeArray": [    {      "object": "CaseType",      "caseClass": "Probate",      "areaOfLaw": "Probate"    }  ],  "caseStats": {    "object": "CaseStats",    "partyCount": 27,    "counselCount": 41,    "docketEntryCount": 2351,    "allCaseDocumentCount": 1013  },  "parties": {    "object": "Parties",    "pageNumber": 1,    "totalCount": 27,    "totalPages": 2,    "nextPageAPI": "/workspace/{workspaceId}/case/CASEar7a26f15e76cf/parties?pageNumber=2"  }}
```

Use **`caseStats`** to see how large each sub-resource is before you fetch it. If the embedded **`parties`**, **`counselList`**, **`docketEntries`**, or **`caseDocuments`** block shows **`totalPages` > 1**, or if **`isPaginationRequiredForFullCase`** is `true`, call the dedicated list endpoints in the steps below instead of relying on the embedded preview alone.

Sealed cases

A sealed case may return **`451`** instead of case data. Add the case to tracking or contact UniCourt Support if you need access when the court unseals it (see [Error Management](../../knowledge-base/error-codes.md)).

## Step 2 — List participants

Case View exposes parties, counsel, and judges on separate paginated endpoints. All require **`pageNumber`**.

| Resource | Endpoint |
| --- | --- |
| Parties | `GET /workspace/{workspaceId}/case/{caseId}/parties` |
| Counsel | `GET /workspace/{workspaceId}/case/{caseId}/counsel` |
| Judges | `GET /workspace/{workspaceId}/case/{caseId}/judges` |

List counsel for a case

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/case/{caseId}/counsel?pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Counsel responses use the v3 **Counsel** model (`counselId`, `counselType`, `counselRole`, `normAttorney`, `normLawFirm`) — not the v2 **`Attorney`** object. See [Understanding the Counsel Object](../../knowledge-base/understanding-the-counsel-object.md).

Optional query parameter on counsel: **`isVisible`** (`true` / `false`) to filter active vs historical representation.

To drill into one participant, use the by-ID endpoints (for example **`GET /workspace/{workspaceId}/counsel/{counselId}`** or **`GET /workspace/{workspaceId}/party/{partyId}`**).

## Step 3 — List docket entries

Docket entries (page 1)

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/case/{caseId}/docketEntries?pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Follow **`nextPageAPI`** until you have all pages (100 entries per page — see [Pagination](../../knowledge-base/pagination.md)).

Related list endpoints when you need document linkage:

| Endpoint | Use when… |
| --- | --- |
| `GET .../docketEntries/primaryDocuments` | Primary documents attached to docket entries |
| `GET .../docketEntries/secondaryDocuments` | Secondary attachments |

## Step 4 — List case documents

Case documents (page 1)

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/case/{caseId}/documents?pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Each item includes a **`caseDocumentId`**. Before downloading or ordering, fetch full metadata:

Document metadata

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseDocument/{caseDocumentId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Check **`repository`** (`UNICOURT` vs `COURT_SOURCE`) and **`availabilityStatusAtCourtSource`**, then follow [Getting documents from cases](../../common-use-cases/get-case-content/get-a-case-document.md) to acquire the file.

For a **ZIP of the whole case** (structured data package, not individual PDFs), see [Export a case](../../common-use-cases/get-case-content/export-a-case.md).

## Step 5 — Optional related data

| Endpoint | Contents |
| --- | --- |
| `GET .../case/{caseId}/hearings` | Scheduled hearings |
| `GET .../case/{caseId}/relatedCases` | Linked cases |
| `GET .../case/{caseId}/tentativeRulings` | Tentative rulings (where available) |

Each supports **`pageNumber`** where the response is a list.

## Keep the case current

Reading a case returns data UniCourt already holds. To refresh from the court:

- One-time refresh → [Update a case once](../../common-use-cases/keep-cases-current/update-a-case-once.md)
- What changed since last check → [See what changed on a case](../../common-use-cases/keep-cases-current/sync-case-history.md)
- Ongoing schedule → [Track a case on a schedule](../../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md)

## v3 vs v2 reminders

| v2 | v3 |
| --- | --- |
| `GET /case/{caseId}` | `GET /workspace/{workspaceId}/case/{caseId}` |
| `GET /case/{caseId}/attorneys` | `GET /workspace/{workspaceId}/case/{caseId}/counsel` |
| `caseType` (single object) | `caseTypeArray` |
| `caseStats.attorneyCount` | `caseStats.counselCount` |
| `courtServiceStatusId` | `courtSourceId` |
