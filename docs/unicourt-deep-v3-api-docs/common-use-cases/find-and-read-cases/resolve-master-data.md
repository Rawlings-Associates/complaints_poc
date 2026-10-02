---
title: "Resolve Master Data"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/find-and-read-cases/resolve-master-data/
retrieved: 2026-10-01
---

# Resolve Master Data

You want to filter cases for **"Closed"** status, **"Labor and Employment"**, or a specific court—but Case Search and Analytics expect **immutable IDs** (`caseStatusId`, `areaOfLawId`, `courtId`), not free-text labels. Courts spell the same concept differently (`CLOSED` vs `DISPOSED`); UniCourt **Data Standards / Master Data** map those spellings to one ID you can reuse everywhere.

This walkthrough turns plain language into the filter ID, then plugs it into [Search for cases](../../common-use-cases/find-and-read-cases/search-for-cases.md) or analytics.

**Reference docs:** [UniCourt Data Standards](../../knowledge-base/unicourts-data-standards-and-voyager.md) (taxonomy overview), [Query Builders](../../knowledge-base/query-builders.md), [Pagination](../../knowledge-base/pagination.md).

Browse interactively: [**Data Standards UI**](#).

Specs: [**Case Master Data**](#), [**Court Master Data**](#).

## Before you start

You need:

- A **workspace token** and **`workspaceId`**
- The concept you care about in plain language (status name, court name, area of law, party role, and so on)

Base URL: **`https://deep-api.unicourt.com`**.

## How it fits together

```mermaid
flowchart LR  A[Plain label e.g. Closed] --> B[Master Data list with q]  B --> C[Copy immutable ID]  C --> D[Case Search or Analytics q]
```

Master Data is **not** the same as [entity match](../../common-use-cases/entities-and-counsel/search-for-an-entity.md). Master Data resolves **classification IDs** (court, status, case type). Entity Match resolves **people and firms** (`normAttorneyId` / `normLawFirmId`).

## Step 1 — Pick the taxonomy endpoint

Common lookups:

| You want… | List endpoint | ID field to copy |
| --- | --- | --- |
| Case status | `GET .../masterData/caseStatus` | `caseStatusId` |
| Case status group | `GET .../masterData/caseStatusGroup` | `caseStatusGroupId` |
| Case class | `GET .../masterData/caseClass` | `caseClassId` |
| Area of law | `GET .../masterData/areaOfLaw` | `areaOfLawId` |
| Case type / type group | `GET .../masterData/caseType`, `.../caseTypeGroup` | `caseTypeId`, `caseTypeGroupId` |
| Court | `GET .../masterData/court` | `courtId` |
| Court system / type / location | `.../courtSystem`, `.../courtType`, `.../courtLocation` | Matching `*Id` |
| Party role | `GET .../masterData/partyRole` | `partyRoleId` |
| Counsel role (v3) | `GET .../masterData/counselRole` | `counselRoleId` |
| Judge role (v3) | `GET .../masterData/judgeRole` | `judgeRoleId` |
| Court source | `GET .../masterData/courtSource/{courtSourceId}` | `courtSourceId` |

Case type is **four tiers** (class → area of law → type group → type). Status is **two tiers** (group → status). Pick the broadest ID that matches how you want to filter.

Full lists—including dispositions, motions, outcomes, and procedural activities added in v3—are in the Master Data specs and the [Data Standards KB](../../knowledge-base/unicourts-data-standards-and-voyager.md).

## Step 2 — Search Master Data with `q`

List endpoints take a keyword **`q`** and **`pageNumber`** (same boolean/`name:(…)` style as other UniCourt searches). Maximum **15 operators** per query.

Find the Closed case status ID

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/masterData/caseStatus?q=name%3A%28Closed%29&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Find a court by name

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/masterData/court?q=name%3A%28%22Central%20District%20of%20California%22%29&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Find an area of law

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/masterData/areaOfLaw?q=name%3A%28Probate%29&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Copy the ID from the matching row. If several names look similar, open the Data Standards UI or **GET** by ID (Step 3) to confirm the hierarchy.

## Step 3 — Fetch one ID when you need details

Once you know the ID, resolve the full object:

Get case status by ID

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/masterData/caseStatus/{caseStatusId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Get court by ID

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/masterData/court/{courtId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Court objects also expose related paths such as **`.../court/{courtId}/courtLocations`** and **`.../jurisdictionGeo`**.

## Step 4 — Use the ID in Case Search or Analytics

Nest the ID in a Case Search **`q`** expression:

Cases with a resolved case class

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseSearch?q=%28CaseType%3A%28caseClassId%3A%22CSCLNjbKTN7Yfo2wdb%22%29%29&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Cases in a resolved court

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseSearch?q=%28Court%3A%28courtId%3A%22CORTjF63b8Z4d2i9UB%22%29%29&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Exact nested field names depend on the Case Search query schema—validate with **Try It Out** in the [**Case Search API**](#).

For aggregates by court, type, or area of law, pass the same IDs into Analytics View `q` filters—see [Analyze case counts](../../common-use-cases/analyze/analyze-case-counts.md).

## Typical IDs you will resolve

| Prefix pattern | Meaning |
| --- | --- |
| `CORT…` | Court |
| `CTSS…` | Court source (`courtSourceId`) |
| `CSCL…` | Case class |
| `AOFL…` | Area of law |
| `CTYP…` / `CTYG…` | Case type / case type group |
| `CSTS…` / group IDs | Case status / status group |
| `PTYR…` | Party role |
| Counsel / judge role IDs | `counselRoleId`, `judgeRoleId` (v3) |

## v3 vs v2

| v2 | v3 |
| --- | --- |
| `/masterData/…` | `/workspace/{workspaceId}/masterData/…` |
| `attorneyType` | **`counselRole`** |
| `judgeType` | **`judgeRole`** |
| `attorneyRepresentationType` | Removed — use **`Party.representationType`** enum on the case |
| `courtServiceStatusId` | **`courtSourceId`** |
| Criminal taxonomies (`charge`, `causeOfAction`, …) | Removed from Master Data |

## Next steps

- [Search for cases](../../common-use-cases/find-and-read-cases/search-for-cases.md) — run filters with the IDs you resolved
- [Analyze case counts](../../common-use-cases/analyze/analyze-case-counts.md) — aggregate with the same IDs
- [Import a case from PACER](../../common-use-cases/find-and-read-cases/import-a-case-from-pacer.md) — PACER import also needs a resolved **`courtId`**
