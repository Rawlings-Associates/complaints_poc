---
title: "Query Builders"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/query-builders/
retrieved: 2026-10-01
---

# Query Builders

## Principles of Keyword Searching and Query Building

### Property Names and Target Values

The UniCourt API allows your software to search for legal data using keyword expressions. The basic unit of a keyword expression is a search criterion, which consists of a property name and a corresponding target value. To search for court cases containing the term "Smith" in the caption text, for example, your software should submit the keyword expression **`caseName:(Smith)`** to the [**/workspace/{workspaceId}/caseSearch**](#) endpoint. In this example, the property name is **`caseName`**, and the target value is Smith. To search for court cases filed in the last 30 days, your software should submit the keyword expression **`filedDate:[now-30d TO now]`** to the [**/workspace/{workspaceId}/caseSearch**](#) endpoint. In this second example, the property name is **`filedDate`**, and the target value is **`[now-30d TO now]`**.

### Boolean operators

Two or more search criteria can be combined by including the Boolean operators `AND` or `OR` within the keyword expression. To search for court cases whose caption text contains the term "Smith" and which were filed in the past 30 days, your software should submit the keyword expression **`caseName:(Smith) AND filedDate:[now-30d TO now]`** to the [**/workspace/{workspaceId}/caseSearch**](#) endpoint.

### Parentheses

A keyword expression may include parenthesis to ensure the expression can be interpreted in only one way. The following keyword expressions, in which the nesting parentheses are highlighted for emphasis, illustrate how parentheses prevent ambiguity:

1. **`(caseName:(Smith) OR caseName:(Jones)) AND filedDate:[now-30d TO now]`**
2. **`caseName:(Smith) OR (caseName:(Jones) AND filedDate:[now-30d TO now])`**

The first keyword expression categorically excludes court cases filed more than 30 days ago. The second keyword expression, however, includes such cases so long as their caption text contains the term "Smith." You should use parentheses to prevent ambiguity in keyword expressions wherever possible.

### Nesting of Property Names

A large number of objects in UniCourt’s data holdings allow for "nesting," such that the value associated with a property name is itself an object. Each Case object, for example, contains counsel entries in `counselList`, each of which has its own property named `name`. The UniCourt API allows keyword expressions to specify target values located within nested objects. To search for court cases involving counsel named "Johnson," for example, your software should send the following keyword expression to the [**/workspace/{workspaceId}/caseSearch**](#) endpoint:

**`Counsel:(name:(Johnson))`**

### Combining Search Criteria

The UniCourt API allows your software to submit any keyword expression that complies with the aforementioned rules on parentheses and nesting.

## Endpoints for Keyword Searching and Query Builders

The UniCourt API allows your software to query for objects using keyword searching. The UniCourt API accepts keyword searches from your software at the following endpoints:

| Endpoints | Specification with Query Builder |
| --- | --- |
| `/workspace/{workspaceId}/caseSearch` | [https://app.unicourt.com/developers/enterpriseapi/api/UniCourt-DEEP-Case-Search-API-Spec#/Case%20Search/searchCases](#) |
| `/workspace/{workspaceId}/normAttorneySearch` | [https://app.unicourt.com/developers/enterpriseapi/api/UniCourt-DEEP-Entity-Search-API-Spec#/Attorney%20Search/searchNormalizedAttorneys](#) |
| `/workspace/{workspaceId}/normLawFirmSearch` | [https://app.unicourt.com/developers/enterpriseapi/api/UniCourt-DEEP-Entity-Search-API-Spec#/Law%20Firm%20Search/searchNormalizedLawFirms](#) |

What constitutes a valid keyword query varies according to the endpoint. Specific rules for constructing keyword queries are set forth in the respective specification for each endpoint. The specification of each endpoint also includes a query builder tool for building keyword queries, which may be accessed through the **“Try It Out”** button.

## Migration Notes for v2 Integrators

If your keyword expressions still nest under `Attorney` or call account-scoped search paths, update as below. For counsel field and association changes, see [Understanding the Counsel Object](../knowledge-base/understanding-the-counsel-object.md).

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| `GET /caseSearch` | `GET /workspace/{workspaceId}/caseSearch` | Workspace-scoped on `deep-api.unicourt.com` |
| `Attorney:(name:(…))` in case search `q` | `Counsel:(name:(…))` | Case counsel is modeled as **Counsel**, not **Attorney**; filter with `counselType` when you need attorneys only |
| `Attorney:(normAttorneyId:…)` / law-firm nesting on cases | `Counsel:(normAttorneyId:…)`, `Counsel:(normLawFirmId:…)` | Normalized links live on counsel; see [Counsel object](../knowledge-base/understanding-the-counsel-object.md#searching-for-counsel) |
| `UniCourt-Enterprise-Court-Data-API-Spec` query builders | `UniCourt-DEEP-Case-Search-API-Spec` (and DEEP entity search specs) | Spec bundles renamed; use each endpoint’s **Try It Out** query builder for valid nested fields |
| Account-scoped `/normAttorneySearch`, `/normLawFirmSearch` | `/workspace/{workspaceId}/normAttorneySearch`, `/workspace/{workspaceId}/normLawFirmSearch` | Workspace-scoped; supported fields remain in the Entity Search specs |
