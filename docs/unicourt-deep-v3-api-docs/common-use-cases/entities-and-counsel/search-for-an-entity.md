---
title: "Search for and Match your Entity"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/entities-and-counsel/search-for-an-entity/
retrieved: 2026-10-01
---

# Search for and Match your Entity

You maintain your own records on attorneys and law firms—CRM contacts, opposing counsel lists, panel counsel, or claims data. Those names and bar numbers rarely match court spellings one-for-one. The job is to **link each of your internal records to UniCourt's normalized entity** (`normAttorneyId` or `normLawFirmId`), then use that ID to pull the profile or find associated cases.

This is the typical **experience management** pattern: **match** your data → accept a norm ID → **read the profile** (or search cases). Separately, use **Entity Search** when you are browsing UniCourt’s entity directory with keyword filters—not linking a stored record.

**Recommended path:** use the **Entity Match** APIs (`normAttorneyMatch` / `normLawFirmMatch`). They answer: *"Which normalized entity most likely matches this attorney or firm record?"*—especially when your source data is incomplete or inconsistently formatted.

**Reference docs:** [Entity Match](../../knowledge-base/entity-match.md) (request/response, scoring), [Normalization](../../knowledge-base/normalization-docs.md), [Query Builders](../../knowledge-base/query-builders.md).

## Before you start

You need:

- A **workspace ID** (`workspaceId`) and **workspace-scoped JWT** (see [Authentication](../../getting-started/authentication.md))
- Identifying fields from your internal record (name at minimum; bar state/number, firm, phone, email, or address when available)

Base URL: **`https://deep-api.unicourt.com`**.

## End-to-end flow

```mermaid
flowchart TD  A[Internal attorney or firm record] --> B[GET Entity Match API]  B --> C[Review confidenceScore and scoreConstituents]  C --> D{Confident match?}  D -->|yes| E[Accept candidate]  D -->|no| F[Manual review via Entity Profile]  F --> E  E --> G[Store normAttorneyId or normLawFirmId]  G --> H[Read entity profile]
```

## Step 1 — Call Entity Match with your identifying data

### Attorneys

**GET** [**/workspace/{workspaceId}/normAttorneyMatch**](#).

Pass the strongest identifiers you have. Prioritize, when available:

| Priority | Parameters |
| --- | --- |
| Highest | **`fullName`** (or **`firstName`** + **`lastName`**, optional **`middleName`**) |
| High | **`barredState`** + **`barNumber`** — **`barredState` is required when you send `barNumber`** |
| Helpful | **`lawFirmList`**, **`phoneList`**, **`emailList`**, **`addressList`** |

Match an attorney from your data

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorneyMatch?fullName=MICHAEL%20SCOTT%20HUNT&barredState=CA&barNumber=99804' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Excerpt — NormAttorneyMatchResponse

```json
{  "object": "NormAttorneyMatchResponse",  "name": "MICHAEL SCOTT HUNT",  "possibleNormAttorneyArray": [    {      "object": "PossibleNormAttorneyMatch",      "normAttorneyId": "QATTSJ709tX66v8KJ2",      "normAttorneyName": "MICHAEL SCOTT HUNT",      "bestMatch": true,      "confidenceScore": 1,      "scoreConstituents": {        "nameSimilarityScore": 1,        "barId": "Not_Provided_By_Data_Source",        "address": "Matched",        "email": "Matched",        "phone": "Matched",        "lawFirm": "Matched"      },      "normAttorneyAPI": "/workspace/{workspaceId}/normAttorney/QATTSJ709tX66v8KJ2"    }  ]}
```

### Law firms

**GET** [**/workspace/{workspaceId}/normLawFirmMatch**](#).

**`name`** is required. Optionally pass **`state`**, **`emailList`**, **`phoneList`**, or **`addressList`**. The same selection practices below apply to **`possibleNormLawFirmArray`**.

Match a law firm from your data

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normLawFirmMatch?name=GORDON%20REES&state=CA' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Full parameter and response reference: [Entity Match](../../knowledge-base/entity-match.md).

## Step 2 — Read scores and choose a result

Each candidate includes:

| Field | Use it to… |
| --- | --- |
| `normAttorneyId` / `normLawFirmId` | Store the UniCourt link on your record |
| `confidenceScore` | Decide accept vs review (`similarityScore / n` — quality diluted by how many candidates share the match) |
| `scoreConstituents` | See *why* the score landed where it did (name similarity, bar, firm, contact fields) |
| `bestMatch` | UniCourt’s preferred candidate when multiple rows return—treat as a hint |
| `normAttorneyAPI` / profile path | Open the profile for manual review |

A unique attribute match often scores **1.0**; an identical name with no secondary attributes often scores **0.8**; splits across multiple candidates dilute the score (for example **0.5** or **0.4**). See [Confidence scores](../../knowledge-base/entity-match.md#confidence-scores) for tiers and the full scenario table.

### Manual review

When the scores leave ambiguity:

1. Compare your input fields to each candidate’s name and attributes.
2. Inspect **`scoreConstituents`** for distinguishing factors (middle name, firm, bar, contact details).
3. Open each candidate’s profile via **`normAttorneyAPI`** / law-firm profile path (see [Read an entity profile](../../common-use-cases/entities-and-counsel/read-an-entity-profile.md)).
4. Accept the best match, or flag the record for further research if it remains ambiguous.

## Step 3 — Use the matched norm ID

Store **`normAttorneyId`** or **`normLawFirmId`** on your internal record as the link to UniCourt.

### Read the entity profile

Follow **`normAttorneyAPI`** (or the law-firm profile path) to load bar data, employment history, associated firms/attorneys, and related links:

GET normalized attorney profile

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/normAttorney/QATTSJ709tX66v8KJ2' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Full walkthrough: [Read an entity profile](../../common-use-cases/entities-and-counsel/read-an-entity-profile.md).

### Find associated cases

Pass the norm ID into **Case Search** as a filter in **`q`**:

Cases involving a matched attorney

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseSearch?q=%28Counsel%3A%28normAttorneyId%3A%22QATTSJ709tX66v8KJ2%22%29%29&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

For firms, filter with **`normLawFirmId`** the same way. See [Search for cases](../../common-use-cases/find-and-read-cases/search-for-cases.md) and [Query Builders](../../knowledge-base/query-builders.md).

You can also use the norm ID in [Analyze counsel activity](../../common-use-cases/analyze/analyze-counsel-activity.md) for aggregated case counts.

## When to use Entity Search instead

**Entity Search** (`normAttorneySearch` / `normLawFirmSearch`) is a keyword browser over UniCourt’s entity index—useful when you are exploring names, not linking a stored CRM/claims record.

| Goal | Use |
| --- | --- |
| Link **your** attorney/firm record to UniCourt, then pull the profile | **Entity Match** (this walkthrough) → [Read an entity profile](../../common-use-cases/entities-and-counsel/read-an-entity-profile.md) |
| Browse / keyword-query UniCourt’s entity directory | **Entity Search** — `GET .../normAttorneySearch` or `.../normLawFirmSearch` with `q` |

Search syntax and field lists: [**Entity Search API**](#). v3 covers **attorneys and law firms only** (v2 judge/party search endpoints are removed).

See also [Entity Match vs Entity Search](../../knowledge-base/entity-match.md#entity-match-vs-entity-search).

## v3 vs v2

| v2 | v3 |
| --- | --- |
| `/normAttorneyMatch` | `/workspace/{workspaceId}/normAttorneyMatch` |
| `/normLawFirmMatch` | `/workspace/{workspaceId}/normLawFirmMatch` |
| `/normAttorney/{normAttorneyId}` | `/workspace/{workspaceId}/normAttorney/{normAttorneyId}` |
| `/normAttorneySearch`, `/normLawFirmSearch` | Workspace-scoped equivalents |
| `/normJudgeSearch`, `/normPartySearch` | *(removed)* |

Base URL: **`https://deep-api.unicourt.com`**.

## Next steps

1. [Read an entity profile](../../common-use-cases/entities-and-counsel/read-an-entity-profile.md) — full normalized profile for the matched ID
2. [Search for cases](../../common-use-cases/find-and-read-cases/search-for-cases.md) — cases linked to that entity
3. [Track an entity on a schedule](../../common-use-cases/entities-and-counsel/track-an-entity-on-a-schedule.md) — keep the profile current
