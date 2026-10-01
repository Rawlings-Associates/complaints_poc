---
title: "Case Search"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/case-search/
retrieved: 2026-10-01
---

# Case Search

The Case Search API finds cases with keyword expressions against UniCourt’s case index. Use it when you need a **list of cases that meet certain criteria**, or when you already **confidently know key identifying information** about a single case (for example an exact case number) and want exact field matches with sorting and pagination.

Unlike [Case Match](../knowledge-base/case-match.md), which fuzzy-matches imperfect inputs to ranked candidates, Case Search expects clean filters in a `q` expression and returns paginated result sets.

See [Search for cases](../common-use-cases/find-and-read-cases/search-for-cases.md) for a walkthrough. For expression syntax, see [Query Builders](../knowledge-base/query-builders.md). For page size and caps, see [Pagination](../knowledge-base/pagination.md). Result IDs such as `caseId` (`CASE`) and `caseSearchId` (`CSRH`) use fixed prefixes—see [Object ID Prefixes](../knowledge-base/object-id-prefixes.md).

## Endpoints

| Method | Path | Description |
| --- | --- | --- |
| GET | `/workspace/{workspaceId}/caseSearch` | Search cases with a keyword expression (`searchCases`) |
| GET | `/workspace/{workspaceId}/caseSearch/{caseSearchId}` | Re-fetch results for a previous search (`getCaseSearchById`) |

## Submitting a case search

Submit a **GET** to [**/workspace/{workspaceId}/caseSearch**](#). The flow:

1. Build a keyword expression for **`q`** (field names, values, and Boolean operators).
2. Call with **`pageNumber`** (required; start at `1`) and optional **`sort`** / **`order`**.
3. Read `caseSearchResultArray` for preview results on this page; follow **`caseId`** / **`caseAPI`** for the full case.
4. Paginate with **`nextPageAPI`** or increment **`pageNumber`** until results are exhausted.
5. Optionally re-run later with **`caseSearchId`** from the response.

### Request parameters

| Parameter | Required | Description |
| --- | --- | --- |
| `q` | Yes | Keyword expression. See [Query Builders](../knowledge-base/query-builders.md) and the Case Search spec for supported fields. |
| `pageNumber` | Yes | Page to retrieve (starts at `1`). |
| `sort` | No | Field to sort by (for example `filedDate`). |
| `order` | No | `asc` or `desc`. |

Case search request

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseSearch?q=%28caseName%3A%28Harley-Davidson%29%29%20AND%20filedDate%3A%7B2021-01-01T00%3A00%3A00%20TO%20%2A%7D%20AND%20%28Party%3A%28%28name%3A%28Morris%29%29%20AND%20%28PartyRole%3A%28name%3A%28Plaintiff%29%29%29%29%29%20AND%20%28Counsel%3A%28name%3A%28Connors%29%29%29%20AND%20%28Court%3A%28type%3A%22State%22%29%29&pageNumber=1&sort=filedDate&order=desc' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Example `q` expressions:

| Goal | Example `q` |
| --- | --- |
| Cases whose caption contains "Harley-Davidson" | `caseName:(Harley-Davidson)` |
| Cases filed on or after 2021-01-01 | `filedDate:{2021-01-01T00:00:00 TO *}` |
| Caption + date combined | `caseName:(Harley-Davidson) AND filedDate:{2021-01-01T00:00:00 TO *}` |
| Plaintiff named Morris | `(Party:((name:(Morris)) AND (PartyRole:(name:(Plaintiff)))))` |
| Counsel named Connors | `(Counsel:(name:(Connors)))` |
| State courts (`type` is `State` or `Federal`) | `(Court:(type:"State"))` |
| Caption, date, party, counsel, and court combined | `(caseName:(Harley-Davidson)) AND filedDate:{2021-01-01T00:00:00 TO *} AND (Party:((name:(Morris)) AND (PartyRole:(name:(Plaintiff))))) AND (Counsel:(name:(Connors))) AND (Court:(type:"State"))` |
| Exact case number | `(caseNumber:"CA 25-00256")` |
| Counsel by normalized ID | `Counsel:(normAttorneyId:"QATTM0VnRF4w4MBLEQ")` |

Validate nested field names with **Try It Out** in the [**Case Search API spec**](#). Resolve court and type IDs with [Resolve master data](../common-use-cases/find-and-read-cases/resolve-master-data.md) before nesting them in `q`.

Counsel vs Attorney in search

On the case object, attorneys and law firms are modeled as **Counsel** — see [Understanding the Counsel Object](../knowledge-base/understanding-the-counsel-object.md). Prefer `Counsel:(…)` filters in `q`. Confirm the exact nested property names in the Case Search spec’s query builder.

### Response: CaseSearchResponse

Case search response (excerpt)

```json
{  "object": "CaseSearchResponse",  "caseSearchResultArray": [    {      "object": "CaseSearchResult",      "caseId": "CASEggd5bf749967db",      "caseName": "Harold E. Morris et al v. Harley-Davidson Motor Company Group, LLC",      "caseNumber": "CA 25-00256",      "filedDate": "2025-02-13T00:00:00+00:00",      "caseAPI": "/workspace/{workspaceId}/case/CASEggd5bf749967db",      "matchedObjectArray": [        {          "object": "MatchedObject",          "matchedObjectId": "CNSLggc233ac8ea445",          "matchedObjectName": "Counsel",          "matchedObjectAttribute": "name",          "highlightSnippet": "<b>CONNORS</b> LLP",          "matchedObjectAPI": "/workspace/{workspaceId}/counsel/CNSLggc233ac8ea445"        },        {          "object": "MatchedObject",          "matchedObjectId": "PRTYgg4121f3bc6aa8",          "matchedObjectName": "Party",          "matchedObjectAttribute": "name",          "highlightSnippet": "<b>Morris</b> , Respondent",          "matchedObjectAPI": "/workspace/{workspaceId}/party/PRTYgg4121f3bc6aa8"        },        {          "object": "MatchedObject",          "matchedObjectId": "PTYRiP8nMgPxBsPc5i",          "matchedObjectName": "Party.PartyRole",          "matchedObjectAttribute": "name",          "highlightSnippet": "<b>Plaintiff</b>",          "matchedObjectAPI": "/workspace/{workspaceId}/masterData/partyRole/PTYRiP8nMgPxBsPc5i"        }      ]    }  ],  "caseSearchId": "CSRHRywKSxXDwPkJod",  "q": "%28caseName%3A%28Harley-Davidson%29%29%20AND%20filedDate%3A%7B2021-01-01T00%3A00%3A00%20TO%20%2A%7D%20AND%20%28Party%3A%28%28name%3A%28Morris%29%29%20AND%20%28PartyRole%3A%28name%3A%28Plaintiff%29%29%29%29%29%20AND%20%28Counsel%3A%28name%3A%28Connors%29%29%29%20AND%20%28Court%3A%28type%3A%22State%22%29%29",  "pageNumber": 1,  "totalCount": 4,  "totalPages": 1,  "nextPageAPI": null,  "previousPageAPI": null}
```

| Field | Description |
| --- | --- |
| `caseSearchResultArray` | Preview results on this page (not the full case). |
| `caseSearchId` | ID for re-fetching this search without resending `q`. |
| `q` | The expression used for this search. |
| `pageNumber` / `totalCount` / `totalPages` | Pagination metadata. |
| `nextPageAPI` / `previousPageAPI` | Relative paths for adjacent pages (`null` when none). |

Each `CaseSearchResult` includes identifiers, preview metadata, **`caseAPI`**, and **`matchedObjectArray`** (which fields matched, with highlight snippets).

An empty **`caseSearchResultArray`** with **`200 OK`** means the query was valid but matched no cases.

## Pagination

Case Search returns **10 results per page** and supports up to **1,000 pages** per query—at most **10,000 cases** for a single `q`. If **`totalCount`** is higher, narrow your expression or batch by date (or another filter) and run multiple searches.

Every request must include **`pageNumber`**. Prefer following **`nextPageAPI`** over constructing page URLs yourself. See [Pagination](../knowledge-base/pagination.md) for edge cases.

## Re-fetching a previous search

To retrieve results for an earlier query without resending `q`, use **`caseSearchId`**:

Fetch by caseSearchId

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseSearch/{caseSearchId}?pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

CASE SEARCH EXPIRATION

A caseSearchId expires six months after its last use.

## Case Search vs Case Match

| Use… | When… |
| --- | --- |
| **Case Search** | You need a list of cases that meet certain criteria, or you already confidently know key identifying information about a single case and want exact keyword filters with sorting and pagination. |
| **Case Match** | You are trying to find a case from imperfect data—fuzzy-match your inputs against UniCourt’s holdings to resolve to the standardized, cleaned version of the case. |

## Migration Notes for v2 Integrators

If your keyword expressions still nest under `Attorney` or call account-scoped search paths, update as below. For counsel field and association changes on the case object, see [Understanding the Counsel Object](../knowledge-base/understanding-the-counsel-object.md).

| v2 | v3 | Notes |
| --- | --- | --- |
| `GET /caseSearch` | `GET /workspace/{workspaceId}/caseSearch` | Workspace-scoped on `deep-api.unicourt.com` |
| `GET /caseSearch/{caseSearchId}` | `GET /workspace/{workspaceId}/caseSearch/{caseSearchId}` | Workspace-scoped |
| `Attorney:(name:(…))` in `q` | `Counsel:(name:(…))` | Case counsel is modeled as **Counsel**; filter with `counselType` when you need attorneys only |
| `Attorney:(normAttorneyId:…)` / law-firm nesting on cases | `Counsel:(normAttorneyId:…)`, `Counsel:(normLawFirmId:…)` | Normalized links live on counsel |
| `https://enterpriseapi.unicourt.com/…` | `https://deep-api.unicourt.com/workspace/{workspaceId}/…` | Base URL and workspace prefix |
| `UniCourt-Enterprise-Court-Data-API-Spec` query builders | `UniCourt-DEEP-Case-Search-API-Spec` | Use each endpoint’s **Try It Out** query builder for valid nested fields |
