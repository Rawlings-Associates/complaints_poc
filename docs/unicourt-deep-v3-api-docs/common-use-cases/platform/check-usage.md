---
title: "Check Usage"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/platform/check-usage/
retrieved: 2026-10-01
---

# Check Usage

You need to know **how much billable activity your account has consumed**—this month, today, or for one workspace—before you scale imports, tracks, or document orders. Usage APIs report **allocated**, **consumed**, and **overage** totals by activity type so you can monitor programmatically instead of estimating from your own call logs.

**Reference docs:** [Usage, Limits, and Billable Activity](../../getting-started/usage-limits-billable-activities.md) (what counts as billable), [Rate Limits](../../getting-started/rate-limits.md) (speed vs account limits—different systems), [Authentication](../../getting-started/authentication.md).

Spec: [**Usage API**](#).

## Before you start

| Endpoint scope | Token |
| --- | --- |
| Account **`/monthlyUsage/{month}`**, **`/dailyUsage/{date}`** | **Account token** (`POST /generateNewToken`) |
| Workspace **`/workspace/{workspaceId}/monthlyUsage/{month}`**, **`.../dailyUsage/{date}`** | **Workspace token** for that workspace |

Billable limits are **account-level**. Workspace usage endpoints **filter reporting** to one workspace—they are not a separate limit pool. See [Workspaces and limits](../../getting-started/usage-limits-billable-activities.md#workspaces-and-limits).

Base URL: **`https://deep-api.unicourt.com`**.

## Account vs workspace vs rate limits

| Concept | What it controls | How you check it |
| --- | --- | --- |
| **Billable activity (account limit)** | How much successful billable work you may do in a period | Usage APIs (this walkthrough) |
| **Workspace usage report** | Same data, filtered to one workspace | Workspace-scoped Usage paths |
| **Rate limits** | How fast you may call APIs (`429` / `UN429`) | [Rate Limits](../../getting-started/rate-limits.md) — not returned by Usage APIs |

## Step 1 — Check monthly account usage

**GET** [**/monthlyUsage/{month}**](#) with **`month`** as **`YYYY-MM`**:

Account monthly usage

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/monthlyUsage/2025-02' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your account JWT accessToken>'
```

Excerpt — AccountBillingCycleUsage

```json
{  "object": "AccountBillingCycleUsage",  "month": "2025-02",  "accountAllocated": {    "Case Search": 500,    "Case View": 1000,    "Case Document View": 180,    "Case Update": 300,    "Entity Update": 250  },  "accountConsumed": {    "Case Search": 370,    "Case View": 820,    "Case Document View": 134,    "Case Update": 235,    "Entity Update": 180  },  "overage": {    "Case Search": 0,    "Case View": 0,    "Case Document View": 0,    "Case Update": 0,    "Entity Update": 0  }}
```

| Field | Meaning |
| --- | --- |
| **`accountAllocated`** | Limits for the period by activity label |
| **`accountConsumed`** | Successful billable units used so far |
| **`overage`** | Units beyond allocation (when applicable) |

Activity labels in the response match the billable activities in your agreement (Case Search, Case View, Case Document View, Case Update, Entity Update, and so on). Related operations share those meters — for example, case imports and exports count toward **Case View**, and document orders count toward **Case Document View**. For the full list and what triggers a charge, see [What counts as billable activity](../../getting-started/usage-limits-billable-activities.md#what-counts-as-billable-activity).

Invalid **`month`** values return **`404`**.

## Step 2 — Check daily account usage

**GET /dailyUsage/{date}** with **`date`** as **`YYYY-MM-DD`**:

Account daily usage

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/dailyUsage/2025-02-21' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your account JWT accessToken>'
```

The response is **`AccountDailyUsage`**: **`usageStartTime`** / **`usageEndTime`** plus the same **`accountAllocated`** / **`accountConsumed`** / **`overage`** maps for that day.

Use daily views to investigate spikes; use monthly for quota headroom.

## Step 3 — Scope usage to one workspace (optional)

When you need to report consumption for a single workspace (still against the shared account limit):

Workspace monthly usage

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/monthlyUsage/2025-02' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your workspace JWT accessToken>'
```

Workspace daily usage

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/dailyUsage/2025-02-21' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your workspace JWT accessToken>'
```

Same date formats as the account endpoints.

## Endpoints at a glance

| Method | Path | Scope |
| --- | --- | --- |
| GET | `/monthlyUsage/{month}` | Account |
| GET | `/dailyUsage/{date}` | Account |
| GET | `/workspace/{workspaceId}/monthlyUsage/{month}` | Workspace report |
| GET | `/workspace/{workspaceId}/dailyUsage/{date}` | Workspace report |

## Practical tips

- Monitor **`accountConsumed`** against **`accountAllocated`** before large [Case Track](../../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md) or [Case Document View](../../common-use-cases/get-case-content/get-a-case-document.md) (document order) batches.
- Prefer product **previews** (where available) to estimate cost—previews are not billable. Details in the Usage KB.
- A **`429`** means you hit a **rate limit**, not that Usage shows you out of billable activity.
- Hitting a billable limit typically surfaces as **`403` / `UN203` / `LIMIT_REACHED`** on the operation that consumes the unit (import, update, track, and so on)—Usage APIs tell you *why* headroom is gone.

## v3 vs v2

| v2 | v3 |
| --- | --- |
| `/billingCycles`, `/billingCycleUsage/{billingCycle}` | **Removed** — use `/monthlyUsage/{month}` |
| `/dailyUsage/{date}` | Retained (account); plus workspace-scoped daily/monthly |
| — | `/workspace/{workspaceId}/monthlyUsage/{month}`, `.../dailyUsage/{date}` |

Base URL: **`https://deep-api.unicourt.com`**.
