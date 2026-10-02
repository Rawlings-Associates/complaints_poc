---
title: "Legal Analytics"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/legal-analytics/
retrieved: 2026-10-01
---

# Legal Analytics

The **Analytics View API** returns aggregated case counts for cases in your workspace. Use it to answer questions like “how many cases were filed in this court last year?” or “which opposing counsel appears most often against this attorney?” without pulling every case individually.

See [Analyze case counts](../common-use-cases/analyze/analyze-case-counts.md) and [Analyze counsel activity](../common-use-cases/analyze/analyze-counsel-activity.md) for full walkthroughs.

Full query syntax and field reference: [Query Builders](../knowledge-base/query-builders.md). API schemas: [**Analytics View API spec**](#).

## How analytics requests work

All analytics endpoints are **GET** requests under **`/workspace/{workspaceId}/…`** on **`deep-api.unicourt.com`**.

| Parameter | Description |
| --- | --- |
| **`q`** | Analytics query expression (filters using master-data IDs, date ranges, `AND`, `IN()`, etc.) |
| **`pageNumber`** | Pagination (see spec for limits) |

Responses return **`results`** (or similarly named arrays on some entity endpoints) with **`caseCount`**, dimension IDs, and pagination fields such as **`totalCaseCount`** and **`nextPageAPI`**.

Resolve entity and master-data IDs via [Entity Search](../getting-started/what-you-can-do-with-deep.md) and [Query Builders](../knowledge-base/query-builders.md) before building `q` expressions. For the prefix on each ID type, see [Object ID Prefixes](../knowledge-base/object-id-prefixes.md).

## Available endpoints in v3

### Case dimension analytics

Group case counts by court or case metadata:

| Endpoint | Groups by |
| --- | --- |
| **GET /workspace/{workspaceId}/caseCountAnalyticsByCourt** | Court |
| **GET /workspace/{workspaceId}/caseCountAnalyticsByCourtLocation** | Court location |
| **GET /workspace/{workspaceId}/caseCountAnalyticsByCourtSystem** | Court system |
| **GET /workspace/{workspaceId}/caseCountAnalyticsByCourtType** | Court type |
| **GET /workspace/{workspaceId}/caseCountAnalyticsByCaseType** | Case type |
| **GET /workspace/{workspaceId}/caseCountAnalyticsByCaseTypeGroup** | Case type group |
| **GET /workspace/{workspaceId}/caseCountAnalyticsByCaseClass** | Case class |
| **GET /workspace/{workspaceId}/caseCountAnalyticsByAreaOfLaw** | Area of law |
| **GET /workspace/{workspaceId}/caseCountAnalyticsByCaseFiledDate** | Filing date |

### Counsel analytics

Group case counts by normalized attorneys or law firms (requires **`normAttorneyId`** / **`normLawFirmId`** in `q` or path context):

| Endpoint | Groups by |
| --- | --- |
| **GET /workspace/{workspaceId}/caseCountAnalyticsByNormAttorney** | Norm attorney |
| **GET /workspace/{workspaceId}/caseCountAnalyticsByNormLawFirm** | Norm law firm |
| **GET /workspace/{workspaceId}/normAttorney/{normAttorneyId}/caseCountAnalyticsByOpposingNormAttorney** | Opposing norm attorneys (for one attorney) |
| **GET /workspace/{workspaceId}/normLawFirm/{normLawFirmId}/caseCountAnalyticsByOpposingNormLawFirm** | Opposing norm law firms (for one law firm) |

Attorney and law firm analytics use UniCourt normalized entities. See [Normalization](../knowledge-base/normalization-docs.md).

## Example request

Case counts by court (filtered)

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseCountAnalyticsByCourt?q=courtSystemId:%22COSY8rpkvJ4kMi4ZYD%22%20AND%20caseFiledDate:[2024-01-01T00:00:00%2B00:00TO2024-12-31T00:00:00%2B00:00]&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Opposing-counsel analytics put the anchor entity in the **path** and use **`q`** for additional filters:

Opposing attorneys for one norm attorney

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorney/QATTSJ709tX66v8KJ2/caseCountAnalyticsByOpposingNormAttorney?q=caseClassId:%22CSCLNjbKTN7Yfo2wdb%22&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

## Removed in v3 (deprecated)

The following v2 **Legal Analytics** capabilities are **not** available in DEEP v3. Do not map these to unrelated endpoints; plan alternative queries or contact UniCourt if you rely on them.

### Analytics dimensions removed

| Removed v2 endpoint | Notes |
| --- | --- |
| **GET /caseCountAnalyticsByNormJudge** | No judge-primary analytics dimension |
| **GET /caseCountAnalyticsByNormParty** | No party-primary analytics dimension |
| **GET /caseCountAnalyticsByJurisdictionGeo** | No jurisdiction-geo-primary dimension |
| **GET /caseCountAnalyticsByPartyRole** | Removed |
| **GET /caseCountAnalyticsByPartyRoleGroup** | Removed |
| **GET /normParty/{normPartyId}/caseCountAnalyticsByOpposingNormParty** | Opposing-party analytics for norm parties removed |

You may still **filter** some retained endpoints using fields like `normJudgeId`, `normPartyId`, or `JurisdictionGeo` inside the **`q`** parameter where the spec allows— but you cannot use a dedicated endpoint that **groups results** by judge, party, jurisdiction geo, or party role as the primary dimension.

### Entity and association APIs removed

Judge and party normalized-entity endpoints and cross-entity association APIs from v2 Legal Analytics are also removed, including:

- **Norm judge** and **norm party** profile and search (`getNormJudgeById`, `getNormPartyById`, `normJudgeSearch`, `normPartySearch`, …)
- **Associated** norm attorneys, judges, law firms, and parties cross-link endpoints (`associatedNormAttorneys`, `associatedNormJudges`, …)

Use **Entity Search** and **Entity Profile View** for attorney and law firm entities retained in v3.

What v3 retains

v3 **does** retain **norm attorney** and **norm law firm** case-count analytics, including **opposing counsel** breakdowns, alongside court and case-metadata dimensions listed above.

## Migration Notes for v2 Integrators

All retained analytics endpoints moved under **`/workspace/{workspaceId}/…`**. Request/response shapes use the same `q` + `pageNumber` pattern; see the Analytics View spec for response object names.

### Retained endpoints — path mapping

| v2 Path | v3 Path |
| --- | --- |
| `/caseCountAnalyticsByCourt` | `/workspace/{workspaceId}/caseCountAnalyticsByCourt` |
| `/caseCountAnalyticsByCourtLocation` | `/workspace/{workspaceId}/caseCountAnalyticsByCourtLocation` |
| `/caseCountAnalyticsByCourtSystem` | `/workspace/{workspaceId}/caseCountAnalyticsByCourtSystem` |
| `/caseCountAnalyticsByCourtType` | `/workspace/{workspaceId}/caseCountAnalyticsByCourtType` |
| `/caseCountAnalyticsByCaseType` | `/workspace/{workspaceId}/caseCountAnalyticsByCaseType` |
| `/caseCountAnalyticsByCaseTypeGroup` | `/workspace/{workspaceId}/caseCountAnalyticsByCaseTypeGroup` |
| `/caseCountAnalyticsByCaseClass` | `/workspace/{workspaceId}/caseCountAnalyticsByCaseClass` |
| `/caseCountAnalyticsByAreaOfLaw` | `/workspace/{workspaceId}/caseCountAnalyticsByAreaOfLaw` |
| `/caseCountAnalyticsByCaseFiledDate` | `/workspace/{workspaceId}/caseCountAnalyticsByCaseFiledDate` |
| `/caseCountAnalyticsByNormAttorney` | `/workspace/{workspaceId}/caseCountAnalyticsByNormAttorney` |
| `/caseCountAnalyticsByNormLawFirm` | `/workspace/{workspaceId}/caseCountAnalyticsByNormLawFirm` |
| `/normAttorney/{id}/caseCountAnalyticsByOpposingNormAttorney` | `/workspace/{workspaceId}/normAttorney/{id}/caseCountAnalyticsByOpposingNormAttorney` |
| `/normLawFirm/{id}/caseCountAnalyticsByOpposingNormLawFirm` | `/workspace/{workspaceId}/normLawFirm/{id}/caseCountAnalyticsByOpposingNormLawFirm` |

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| `UniCourt-Enterprise-Legal-Analytics-API-Spec` | `UniCourt-DEEP-Analytics-View-API-Spec` | Spec bundle renamed |
| Judge / party analytics groups | *(removed)* | See [Removed in v3](#removed-in-v3-deprecated) |
| Account-scoped paths | Workspace-scoped paths | Requires workspace token |
| `https://enterpriseapi.unicourt.com/…` | `https://deep-api.unicourt.com/workspace/{workspaceId}/…` | Base URL change |
