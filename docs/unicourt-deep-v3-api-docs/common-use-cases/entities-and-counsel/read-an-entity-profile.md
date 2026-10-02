---
title: "Read an Entity Profile"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/entities-and-counsel/read-an-entity-profile/
retrieved: 2026-10-01
---

# Read an Entity Profile

You already have a **`normAttorneyId`** or **`normLawFirmId`**—from [matching your internal data](../../common-use-cases/entities-and-counsel/search-for-an-entity.md), from **`Counsel.normAttorney`** / **`Counsel.normLawFirm`** on a case, or from analytics. Now you want the **canonical UniCourt profile**: contact details, bar records, associations, and related API links—not another candidate list.

**Reference docs:** [Normalization](../../knowledge-base/normalization-docs.md) (how norm entities work), [Understanding the Counsel Object](../../knowledge-base/understanding-the-counsel-object.md) (how cases link to norm IDs), [Search for and Match your Entity](../../common-use-cases/entities-and-counsel/search-for-an-entity.md) (how to obtain an ID).

Spec: [**Entity Profile View API**](#).

## Before you start

You need:

- A **`normAttorneyId`** (`QATT…`) or **`normLawFirmId`** (`QLAW…`)
- A **workspace token** and **`workspaceId`**

Base URL: **`https://deep-api.unicourt.com`**.

## Step 1 — Fetch the attorney profile

**GET** [**/workspace/{workspaceId}/normAttorney/{normAttorneyId}**](#):

Get normalized attorney profile

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorney/QATTM0VnRF4w4MBLEQ' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

The **`NormAttorney`** object is the profile shell. Common payload areas:

| Area | What you get |
| --- | --- |
| **Identity** | `normAttorneyId`, `name`, `contact` (addresses, phones, emails, name parts) |
| **Bar** | `barMembershipAndStatusArray`, `barRecordArray` |
| **Background** | `employmentRecordArray`, `lawSchoolArray`, `disciplinaryHistoryArray` (may be `null` when not available) |
| **Freshness** | `lastFetchDate`, `lastFetchDateWithUpdates` |
| **v3 links** | `idEvolutionAPI`, `lastIdEvolutionDate` when the entity ID has evolved |

Excerpt — NormAttorney

```json
{  "object": "NormAttorney",  "normAttorneyId": "QATTM0VnRF4w4MBLEQ",  "name": "Warren Carpenter Osgood",  "contact": {    "object": "NormAttorneyContact",    "currentName": {      "firstName": "Warren",      "middleName": "Carpenter",      "lastName": "Osgood"    }  },  "barMembershipAndStatusArray": [    {      "stateCode": "CA",      "barNumber": "141169",      "admittedDate": "1989-06-06T00:00:00+00:00",      "barMembershipStatus": {        "status": "Inactive"      }    }  ],  "lastFetchDate": "2026-03-06T11:32:29+00:00",  "lastFetchDateWithUpdates": "2024-03-07T03:05:11+00:00"}
```

Full field lists and examples: [Normalization — Norm Attorney Profile](../../knowledge-base/normalization-docs.md#example-looking-at-a-norm-attorney-profile).

## Step 2 — Fetch the law firm profile

**GET** [**/workspace/{workspaceId}/normLawFirm/{normLawFirmId}**](#):

Get normalized law firm profile

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normLawFirm/QLAW811qJ0hBpbm4NH' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Same pattern as attorneys: identity and contact on the root object, plus association and analytics links. In v3, nested **`lawFirmAnalyticsAPI`** bundles from older responses are removed—use standalone Analytics View endpoints with the firm’s **`normLawFirmId`** instead (see [Analyze counsel activity](../../common-use-cases/analyze/analyze-counsel-activity.md)).

## Step 3 — List associations

Profiles often point you to related entities. Use the dedicated association endpoints (paginate with **`pageNumber`**):

| Relationship | Endpoint |
| --- | --- |
| Firms linked to an attorney | `GET /workspace/{workspaceId}/normAttorney/{normAttorneyId}/associatedNormLawFirms` |
| Attorneys linked to a firm | `GET /workspace/{workspaceId}/normLawFirm/{normLawFirmId}/associatedNormAttorneys` |

Law firms associated with an attorney

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorney/QATTM0VnRF4w4MBLEQ/associatedNormLawFirms?pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

These lists support optional **`q`** filters (court, case type, area of law, and similar dimensions). See the Entity Profile View spec for supported connectors.

## Step 4 — Optional: profile history and ID evolution

### Attorney history

**GET /workspace/{workspaceId}/normAttorneyHistory/{normAttorneyId}** returns how the attorney profile changed over time (history buckets by date), useful when you need to audit what UniCourt recorded—not when you only need the current profile.

### ID evolution (new in v3)

Normalized entity IDs can merge or change as UniCourt improves clustering. When **`idEvolutionAPI`** or **`lastIdEvolutionDate`** is present on the profile:

Attorney ID evolution

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorneyIdEvolution/{normAttorneyId}' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Law firms: **`GET /workspace/{workspaceId}/normLawFirmIdEvolution/{normLawFirmId}`**.

If you store norm IDs long-term, check evolution periodically so CRM links stay pointed at the current entity.

## Step 5 — Find cases or keep the profile current

With a confirmed norm ID:

| Goal | Next step |
| --- | --- |
| Cases involving this entity | [Search for cases](../../common-use-cases/find-and-read-cases/search-for-cases.md) — filter `q` with `normAttorneyId` / `normLawFirmId` |
| Aggregated case counts | [Analyze counsel activity](../../common-use-cases/analyze/analyze-counsel-activity.md) |
| Refresh on a schedule | [Track an entity on a schedule](../../common-use-cases/entities-and-counsel/track-an-entity-on-a-schedule.md) |

Case Search by normAttorneyId

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseSearch?q=%28Counsel%3A%28normAttorneyId%3A%22QATTM0VnRF4w4MBLEQ%22%29%29&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

## Match vs profile

| Goal | Use |
| --- | --- |
| Resolve **your** attorney/firm record to a UniCourt ID | [Search for and Match your Entity](../../common-use-cases/entities-and-counsel/search-for-an-entity.md) |
| Load the **full profile** for a known norm ID | **Entity Profile** (this walkthrough) |
| Verify a Match candidate manually | Call this profile API for each candidate, then decide |

## v3 vs v2

| v2 | v3 |
| --- | --- |
| `/normAttorney/{normAttorneyId}` | `/workspace/{workspaceId}/normAttorney/{normAttorneyId}` |
| `/normLawFirm/{normLawFirmId}` | `/workspace/{workspaceId}/normLawFirm/{normLawFirmId}` |
| `/normAttorney/.../associatedNormLawFirms` | Workspace-scoped paths |
| Nested `lawFirmAnalyticsAPI` on firm profile | Removed — use Analytics View with `normLawFirmId` |
| — | `normAttorneyIdEvolution` / `normLawFirmIdEvolution` |

Several NormAttorney array fields (`barRecordArray`, `disciplinaryHistoryArray`, and similar) may be **`null`** in v3 when UniCourt has no data—previously they were often empty arrays.

Base URL: **`https://deep-api.unicourt.com`**.
