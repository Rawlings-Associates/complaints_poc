---
title: "Usage, Limits, and Billable Activity"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/getting-started/usage-limits-billable-activities/
retrieved: 2026-10-01
---

# Usage, Limits, and Billable Activity

## Overview

This article explains how UniCourt counts billable activity on the DEEP API, which allotments apply, and how limits are enforced.

Two systems are separate:

- **Rate limits** control how fast you may call APIs. Exceeding them returns `429` and does not consume billable allotment. For more details, see [Rate Limits](../getting-started/rate-limits.md).
- **Billable activity limits** control how much successful billable work your account may perform. When allotments for an activity are exhausted, further billable work of that type is blocked. This article is about billable activity limits.

## How usage is counted

Every billing activity uses one of three rules:

| How it counts | Meaning | Examples |
| --- | --- | --- |
| **Per successful request** | Each successful billable call consumes 1 unit. For **Entity Update**, a partial profile refresh counts as success (see [Success versus failure](#success-versus-failure)). | Case Search, Case Update, Entity Search, Entity Update, Analytics View |
| **Once per unique ID per billing period** | The first successful use of a given case, entity, or document subject in the period consumes 1 unit; repeats for that same ID do not | Case View, Case Document View, Entity Profile View |
| **Per successful track run** | Each successful scheduled track run consumes 1 unit. For **Entity Tracks**, a partial profile refresh counts as success (see [Success versus failure](#success-versus-failure)). | Case Tracks, Entity Tracks |

Example

All scenarios below assume the **same case** within a **single billing period**:

| Scenario | Case Search Billable Activity Usage | Case View Billable Activity Usage |
| --- | --- | --- |
| 3 case views | — | 1 |
| 1 case view + 1 case export | — | 1 |
| 5 case searches + 5 case views | 5 | 1 |

Case Search counts every call, so 5 searches always cost 5 units. Case View only counts the first time you touch a given case in the period, so viewing it 3 times, or viewing it once and exporting it once, both cost just 1 unit no matter how many more times you touch that same case. If your monthly Case View limit is used up, you can still keep working with cases you've already counted this period; opening a **new** case is what gets blocked.

Related operations share one activity. Case read, import, export, and history all count toward **Case View**, once per case per period. A few supporting reads live under other API groups but still meter as Case View, notably `GET /caseUpdate/{caseId}` and `GET /caseTrack/{caseId}`. Document orders and document downloads count toward **Case Document View**.

Track consumption by activity name in the [Usage endpoints](#usage-and-limit-visibility), not by individual endpoint.

## What counts as billable activity

| Group | Activity | Counts as | What's included |
| --- | --- | --- | --- |
| Docket Research | Case Search | Per successful request | Case Search API operations |
| Docket Research | Case View | Once per case per period | Case read, import, export, history, and related Case View reads (including `GET /caseUpdate/{caseId}` and `GET /caseTrack/{caseId}`) |
| Docket Research | Case Document View | Once per case per period | Document view, document orders, and document downloads (usage units only; court/PACER fees are separate) |
| Docket Research | Case Update | Per successful request | Successful `PUT` that refreshes a case from the court source |
| Docket Tracking | Case Tracks | Per successful track run | Each successful scheduled track run |
| Entity Research | Entity Search | Per successful request | Entity Search API operations |
| Entity Research | Entity Profile View | Once per entity per period | Normalized entity profile reads |
| Entity Research | Entity Update | Per successful request | Entity Update API operations (including partial profile refreshes; see [Success versus failure](#success-versus-failure)) |
| Entity Tracking | Entity Tracks | Per successful track run | Each successful scheduled track run (including partial profile refreshes; see [Success versus failure](#success-versus-failure)) |
| Legal Analytics | Analytics View | Per successful request | Analytics View API operations |
| Platform | Court Master Data | Per successful request | Court master data retrieval |
| Platform | Case Master Data | Per successful request | Case master data retrieval |
| Platform | Authentication & Workspace Management | Per successful request | Auth and workspace management calls |
| Platform | PACER Credentials | Per successful request | PACER credential management calls |
| Platform | Court Service Status | Per successful request | Court service status checks |
| Platform | Usage | Per successful request | Calls to the usage endpoints themselves |
| Other | Other APIs | Per successful request | Any billable API not covered above |

Platform activities are metered per successful request under account-specific limits, but are usually not a practical constraint for normal integrations.

### Success versus failure

Only successful billable work counts. A call that fails to reach the source, or that the source rejects, does not consume a unit.

**Case Update and Case Tracks** use a full-success rule. If the court source cannot be refreshed (for example, the court is offline), the request does not count as Case Update or Case Tracks usage.

**Entity Update and Entity Tracks** use a partial-success rule. An entity profile can span multiple sources (for example, an attorney barred in several states). If UniCourt can refresh any part of the profile and returns a profile object, the request counts as **1 Entity Update** or **1 Entity Track**—even when the response also includes source exceptions for states or sources that failed. Only when every source fails and no profile object is returned does the request not consume a unit.

## Monthly limits, bulk, and overage

For each billing activity, usage is deducted in this order:

1. **Monthly usage limit** — included allowance for the billing period
2. **Bulk limit** — pre-paid or promotional extra usage, if your agreement includes it
3. **Overage** — paid usage beyond the included allowance, if your agreement allows it

When monthly, bulk, and overage (if any) are exhausted, further billable work for that activity is blocked until the next period or until limits are raised. Exhausting an allotment blocks the work; it does not slow the API the way a rate limit does.

Exact allotments, whether bulk or overage apply, and whether unused monthly units roll over are defined in your subscription agreement.

## Court and PACER pass-through fees

Billable activity units and monetary court charges are separate. A successful document order may consume one **Case Document View** unit (once per case per period) **and** incur a court or PACER fee passed through to your account. Case Update can also incur PACER fees in addition to the Case Update unit. See [PACER in UniCourt](../knowledge-base/pacer-api.md) and [Document Orders](../knowledge-base/document-orders.md).

## Usage and limit visibility

Use the Usage endpoints to monitor consumption programmatically. All require authentication:

| Method | Endpoint | Description |
| --- | --- | --- |
| GET | `/monthlyUsage/{month}` | Account usage for the specified month (`YYYY-MM`) |
| GET | `/dailyUsage/{date}` | Account usage for the specified date |
| GET | `/workspace/{workspaceId}/monthlyUsage/{month}` | Same data, filtered to one workspace |
| GET | `/workspace/{workspaceId}/dailyUsage/{date}` | Same data, filtered to one workspace |

Workspace-scoped paths are for **reporting** only. They do not create a separate limit pool, see [Workspaces and limits](#workspaces-and-limits).

For a walkthrough, see [Check usage](../common-use-cases/platform/check-usage.md).

## Workspaces and limits

Allotments are tracked at the **account level**. All workspaces under an account share the same monthly, bulk, and overage pools for each activity unless your agreement states otherwise. A workspace organizes data and activity; it is not a separate limit.

## Migration Notes for v2 Integrators

If you still call billing-cycle usage endpoints or treat document orders as a separate usage concept, map as follows. Walkthrough: [Check usage](../common-use-cases/platform/check-usage.md).

| v2 Field / Endpoint | v3 Field / Endpoint | Notes |
| --- | --- | --- |
| `GET /billingCycles` | *(removed)* | Use `GET /monthlyUsage/{month}` |
| `GET /billingCycleUsage/{billingCycle}` | *(removed)* | Use `GET /monthlyUsage/{month}` with `month` as `YYYY-MM` |
| `GET /dailyUsage/{date}` | `GET /dailyUsage/{date}` | Retained at account scope |
| *(none)* | `GET /workspace/{workspaceId}/monthlyUsage/{month}`, `GET /workspace/{workspaceId}/dailyUsage/{date}` | Workspace-scoped **reporting** only; allotments remain account-level |
| Document orders as a separate usage concept | *(same document APIs; usage now counted under Case Document View)* | Court/PACER fees remain separate pass-through charges |
| `https://enterpriseapi.unicourt.com/…` | `https://deep-api.unicourt.com/…` | Usage endpoints use the DEEP base URL |
