---
title: "Analyze Counsel Activity"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/analyze/analyze-counsel-activity/
retrieved: 2026-10-01
---

# Analyze Counsel Activity

You want counsel-centric volume questions: **"which attorneys appear most often under this filter?"**, **"how active is this firm?"**, or **"who opposes this attorney across my cases?"**—without iterating every docket. Analytics View can **group case counts by normalized attorney or law firm**, and break down **opposing counsel** for one anchor entity.

Court / case-type aggregates live in [Analyze case counts](../../common-use-cases/analyze/analyze-case-counts.md). This walkthrough is the counsel path.

**Reference docs:** [Legal Analytics](../../knowledge-base/legal-analytics.md), [Search for and Match your Entity](../../common-use-cases/entities-and-counsel/search-for-an-entity.md) (obtain norm IDs), [Normalization](../../knowledge-base/normalization-docs.md), [Resolve master data](../../common-use-cases/find-and-read-cases/resolve-master-data.md) (optional court/type filters).

Spec: [**Analytics View API**](#).

## Before you start

You need:

- A **workspace token** and **`workspaceId`**
- For opposing-counsel queries: a **`normAttorneyId`** or **`normLawFirmId`** (from Match, profile, or case counsel links)
- Optional filter IDs (`courtId`, `caseClassId`, `caseFiledDate`, …) from [Resolve master data](../../common-use-cases/find-and-read-cases/resolve-master-data.md)

Counts cover cases **in your workspace** linked to UniCourt's normalized counsel entities.

Base URL: **`https://deep-api.unicourt.com`**.

## Choose the right counsel endpoint

| Question | Endpoint |
| --- | --- |
| Rank attorneys by case volume (with optional filters) | `GET .../caseCountAnalyticsByNormAttorney` |
| Rank law firms by case volume | `GET .../caseCountAnalyticsByNormLawFirm` |
| Who opposes **this** attorney? | `GET .../normAttorney/{normAttorneyId}/caseCountAnalyticsByOpposingNormAttorney` |
| Which firms oppose **this** firm? | `GET .../normLawFirm/{normLawFirmId}/caseCountAnalyticsByOpposingNormLawFirm` |

Same mechanics as case-count analytics: **path = group-by**, **`q` = filter**, **`pageNumber`** paginates rows. Rows appear in **`results`**.

Attorneys and firms only

v3 retains counsel analytics for **norm attorneys** and **norm law firms**. Judge/party group-by and opposing-party analytics from v2 are removed. See [Legal Analytics — Removed in v3](../../knowledge-base/legal-analytics.md#removed-in-v3-deprecated).

## Step 1 — Get a norm ID when you need one

If you are ranking by attorney/firm under filters alone, you may not need a path ID—`caseCountAnalyticsByNormAttorney` returns attorneys that match `q`.

For **opposing counsel**, put the known entity in the **path**. Resolve names with [Search for and Match your Entity](../../common-use-cases/entities-and-counsel/search-for-an-entity.md) when you only have CRM text.

Match an attorney name → normAttorneyId

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorneyMatch?fullName=MICHAEL%20SCOTT%20HUNT' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

## Step 2 — Rank attorneys or firms by case count

Case counts by norm attorney (filter: court + filed date)

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseCountAnalyticsByNormAttorney?q=courtId%3A%22CORTV4vCEaKrhystBz%22%20AND%20caseFiledDate%3A%5B2024-01-01T00%3A00%3A00%2B00%3A00TO2024-12-31T00%3A00%3A00%2B00%3A00%5D&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Case counts by norm law firm (filter: case class)

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseCountAnalyticsByNormLawFirm?q=caseClassId%3A%22CSCLNjbKTN7Yfo2wdb%22&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

To limit to specific entities, include **`normAttorneyId`** / **`normLawFirmId`** in `q` (or `IN()` for up to 10 IDs)—see the Analytics View spec for each endpoint.

Excerpt — ranks by norm attorney

```json
{  "object": "CaseCountAnalyticsByNormAttorneyResponse",  "results": [    {      "object": "CaseCountAnalyticsByNormAttorney",      "normAttorneyId": "QATTkGfH3h68KV41hY",      "normAttorneyName": "Montoya, Daniel Martin",      "caseCount": 1,      "caseSearchAPI": null    }  ],  "totalCaseCount": 8,  "totalNormAttorneyCount": 7,  "nextPageAPI": null}
```

| Field | Use it to… |
| --- | --- |
| **`caseCount`** | Rank activity |
| **`normAttorneyId`** / **`normAttorneyName`** | Identify the counsel entity (firm endpoints use firm fields) |
| **`caseSearchAPI`** | Drill into cases when present |
| **`totalNormAttorneyCount`** / **`totalNormLawFirmCount`** | How many counsel rows matched |

## Step 3 — Opposing counsel for one entity

Put the anchor attorney or firm in the **path**. Use **`q`** for extra filters (court, case class, dates)—not to change the anchor.

Opposing attorneys for one norm attorney

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorney/QATTSJ709tX66v8KJ2/caseCountAnalyticsByOpposingNormAttorney?q=caseClassId%3A%22CSCLNjbKTN7Yfo2wdb%22&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Opposing firms for one norm law firm

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normLawFirm/QLAWrSqNjDdme55Cb0/caseCountAnalyticsByOpposingNormLawFirm?pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Each row is another normalized counsel entity with a shared **`caseCount`**—useful for experience management and conflict / market views.

## Step 4 — Enrich or drill down

From any row:

- **Profile** — [Read an entity profile](../../common-use-cases/entities-and-counsel/read-an-entity-profile.md) with the row’s norm ID
- **Cases** — follow **`caseSearchAPI`** or build Case Search with `normAttorneyId` / `normLawFirmId` ([Search for cases](../../common-use-cases/find-and-read-cases/search-for-cases.md))
- **Court/type context** — combine counsel analytics with [Analyze case counts](../../common-use-cases/analyze/analyze-case-counts.md) for the same `q` filters

## Counsel activity vs case counts

| Goal | Use |
| --- | --- |
| Volume by **attorney or firm** / **opposing counsel** | **Analyze counsel activity** (this walkthrough) |
| Volume by **court / type / area of law / filed date** | [Analyze case counts](../../common-use-cases/analyze/analyze-case-counts.md) |
| Link CRM counsel names to norm IDs first | [Search for and Match your Entity](../../common-use-cases/entities-and-counsel/search-for-an-entity.md) |

## v3 vs v2

| v2 | v3 |
| --- | --- |
| `/caseCountAnalyticsByNormAttorney` | `/workspace/{workspaceId}/caseCountAnalyticsByNormAttorney` |
| `/normAttorney/{id}/caseCountAnalyticsByOpposingNormAttorney` | Workspace-scoped same path |
| Opposing **party** / judge-primary analytics | Removed |
| Nested `lawFirmAnalyticsAPI` on firm profile | Removed — call Analytics View endpoints directly |

Base URL: **`https://deep-api.unicourt.com`**.
