---
title: "Analyze Case Counts"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/analyze/analyze-case-counts/
retrieved: 2026-10-01
---

# Analyze Case Counts

You want answers like **"how many cases were filed in this court system last year?"** or **"which areas of law dominate my workspace?"**—without downloading every docket. **Analytics View** returns **aggregated case counts** grouped by a dimension you choose (court, case type, area of law, filing date, and more).

This walkthrough covers **court and case-metadata** dimensions. For attorney and law firm rankings (including opposing counsel), see [Analyze counsel activity](../../common-use-cases/analyze/analyze-counsel-activity.md).

**Reference docs:** [Legal Analytics](../../knowledge-base/legal-analytics.md) (endpoint list, removed v2 dimensions), [Resolve master data](../../common-use-cases/find-and-read-cases/resolve-master-data.md) (filter IDs), [Query Builders](../../knowledge-base/query-builders.md), [Pagination](../../knowledge-base/pagination.md).

Spec: [**Analytics View API**](#).

## Before you start

You need:

- A **workspace token** and **`workspaceId`**
- Any **master-data IDs** you will filter on (`courtSystemId`, `caseClassId`, `areaOfLawId`, …)—resolve them first via [Resolve master data](../../common-use-cases/find-and-read-cases/resolve-master-data.md)

Analytics counts cases **in your workspace**. They are not a billable “full case download”; they aggregate what UniCourt already associates with the workspace.

Base URL: **`https://deep-api.unicourt.com`**.

## How analytics requests work

1. Pick the endpoint whose **group-by dimension** matches the question.
2. Build a **`q`** filter (optional) with master-data IDs, `AND`, `IN()`, and date ranges.
3. Pass **`pageNumber`** and read **`results`** (plus totals / `nextPageAPI`).

| Parameter | Role |
| --- | --- |
| **`q`** | Narrow which cases are counted (filters—not the group-by itself) |
| **`pageNumber`** | Paginate dimension rows |

The **path** chooses what each row represents (court, area of law, …). The **`q`** chooses *which cases* contribute to each count.

## Step 1 — Choose a dimension endpoint

| Question | Endpoint |
| --- | --- |
| Counts by court | `GET .../caseCountAnalyticsByCourt` |
| Counts by court location / system / type | `.../caseCountAnalyticsByCourtLocation`, `...ByCourtSystem`, `...ByCourtType` |
| Counts by case type / type group | `.../caseCountAnalyticsByCaseType`, `...ByCaseTypeGroup` |
| Counts by case class | `.../caseCountAnalyticsByCaseClass` |
| Counts by area of law | `.../caseCountAnalyticsByAreaOfLaw` |
| Counts by filing date | `.../caseCountAnalyticsByCaseFiledDate` |

Removed group-by dimensions

v3 no longer groups primarily by **norm judge**, **norm party**, **jurisdiction geo**, or **party role**. You may still **filter** some endpoints with those fields in `q` where the spec allows. Details: [Legal Analytics — Removed in v3](../../knowledge-base/legal-analytics.md#removed-in-v3-deprecated).

## Step 2 — Resolve filter IDs (if needed)

If you only want federal district filings in 2024, resolve **`courtSystemId`** (or `courtId`, `caseClassId`, …) before calling analytics. Example flow: Master Data `q=name:(…)` → copy ID → paste into analytics `q`.

See [Resolve master data](../../common-use-cases/find-and-read-cases/resolve-master-data.md).

## Step 3 — Run the analytics query

Case counts by court (filter: court system + filed date)

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseCountAnalyticsByCourt?q=courtSystemId%3A%22COSY8rpkvJ4kMi4ZYD%22%20AND%20caseFiledDate%3A%5B2024-01-01T00%3A00%3A00%2B00%3A00TO2024-12-31T00%3A00%3A00%2B00%3A00%5D&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Case counts by area of law (filter: case class)

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseCountAnalyticsByAreaOfLaw?q=caseClassId%3A%22CSCLNjbKTN7Yfo2wdb%22&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Useful `q` patterns (field support varies by endpoint—check the Analytics View spec for each):

| Pattern | Example |
| --- | --- |
| Single ID | `courtId:"CORTV4vCEaKrhystBz"` |
| Combine filters | `courtSystemId:"COSY…" AND caseClassId:"CSCL…"` |
| Up to 10 IDs | `courtId IN ("CORT…","CORT…")` |
| Filing date range | `caseFiledDate:[2024-01-01T00:00:00+00:00TO2024-12-31T00:00:00+00:00]` |

## Step 4 — Read the response

Each row pairs a **dimension object** with a **`caseCount`**. Many rows include a **`caseSearchAPI`** link to open the underlying cases in Case Search.

Excerpt — case counts by court

```json
{  "object": "CaseCountAnalyticsByCourtResponse",  "results": [    {      "object": "CaseCountAnalyticsByCourt",      "caseCount": 617250,      "court": {        "object": "Court",        "courtId": "CORTV4vCEaKrhystBz",        "name": "Los Angeles County Superior Court"      },      "caseSearchAPI": "/workspace/{workspaceId}/caseSearch/CSRCQBFn7WR3ShRMha"    }  ],  "pageNumber": 1,  "totalPages": 1,  "totalCaseCount": 617250,  "totalCourtCount": 1,  "nextPageAPI": null}
```

| Field | Use it to… |
| --- | --- |
| **`caseCount`** | Rank or chart volume for that dimension value |
| **Dimension object** (`court`, `areaOfLaw`, …) | Display name and ID |
| **`caseSearchAPI`** | Drill into cases for that bucket |
| **`totalCaseCount`** | Overall cases matching `q` |
| **`totalCourtCount`** (or peer `total*Count`) | How many dimension rows match |
| **`nextPageAPI`** | Paginate more dimension rows |

## Step 5 — Drill into cases (optional)

Follow **`caseSearchAPI`**, or rebuild a Case Search `q` with the same filters plus the row’s dimension ID. Continue with [Search for cases](../../common-use-cases/find-and-read-cases/search-for-cases.md) / [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md) when you need dockets—not aggregates.

## Case counts vs counsel activity

| Goal | Use |
| --- | --- |
| Volume by **court / type / area of law / filed date** | **Analyze case counts** (this walkthrough) |
| Volume by **attorney or law firm**, or **opposing counsel** | [Analyze counsel activity](../../common-use-cases/analyze/analyze-counsel-activity.md) |
| Individual case list | [Search for cases](../../common-use-cases/find-and-read-cases/search-for-cases.md) |

## v3 vs v2

| v2 | v3 |
| --- | --- |
| `/caseCountAnalyticsByCourt` (etc.) | `/workspace/{workspaceId}/caseCountAnalyticsByCourt` (etc.) |
| Judge / party / jurisdiction-geo / party-role group-by endpoints | Removed as primary dimensions |
| `UniCourt-Enterprise-Legal-Analytics-API-Spec` | `UniCourt-DEEP-Analytics-View-API-Spec` |

Base URL: **`https://deep-api.unicourt.com`**.
