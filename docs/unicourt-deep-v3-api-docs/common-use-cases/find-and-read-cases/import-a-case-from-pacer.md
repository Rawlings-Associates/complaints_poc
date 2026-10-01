---
title: "Import a Case from PACER"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/find-and-read-cases/import-a-case-from-pacer/
retrieved: 2026-10-01
---

# Import a Case from PACER

You have a **federal case number** and know which **court** it was filed in, but the case is not in your workspace yet—or you need to pull it directly from PACER rather than relying on what UniCourt already has indexed.

This walkthrough covers that path: register PACER credentials, look up the case on the court site, then run a **Case Update** to pull the full docket into DEEP.

**Common reasons to use this:**

- **New or niche federal matters** not yet in [Case Search](../../common-use-cases/find-and-read-cases/search-for-cases.md)
- **Exact PACER lookup** when you already have the docket number from a filing notice or CM/ECF email
- **Onboarding a matter** into your app when the user pastes a PACER case number and court name

**Try search first when you can.** [Case Search](../../common-use-cases/find-and-read-cases/search-for-cases.md) is usually cheaper and returns normalized data for cases UniCourt already extracts. Use PACER import when search does not find the case or you need a direct court lookup.

**Reference docs:** [PACER API](../../knowledge-base/pacer-api.md) (credentials, PCL search, fees), [Case Update](../../knowledge-base/case-update.md) (full docket pull), [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md).

## Before you start

You need:

- A **workspace token** and **`workspaceId`**
- **PACER credentials** stored in DEEP for the account that will be billed
- The **`caseNumber`** as filed at the court (for example `2:10-cv-00001`)
- The **`courtId`** (`CORT…`) for the federal court — resolve via [**Data Standards**](#) or master data APIs (see [Resolve master data](../../common-use-cases/find-and-read-cases/resolve-master-data.md))

PACER import is **synchronous** (one GET). Pulling the **full docket** is a separate **Case Update** step and is **asynchronous**.

## Step 1 — Store PACER credentials

Register the PACER account once per workspace via **PUT /workspace/{workspaceId}/pacerCredential**. Include **`pacerMFASecretKey`** if MFA is enabled on the account.

Add PACER credentials

```Shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/pacerCredential' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "pacerUserId": "<your pacerUserId>",  "password": "<your password>",  "defaultPacerClientCode": "<your pacerClientCode>",  "pacerMFASecretKey": "<your MFA secret key>"}'
```

Full credential rules, client codes, and password rotation: [PACER API — credentials](../../knowledge-base/pacer-api.md#pacer-credentials).

## Step 2 — Import by case number and court

**GET** [**/workspace/{workspaceId}/pacer/importCaseByCourtUsingCaseNumber**](#).

Required query parameters: **`pacerUserId`**, **`caseNumber`**, **`courtId`**. Pass **`pacerClientCode`** when your PACER billing preferences require it.

PACER find-case import

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/pacer/importCaseByCourtUsingCaseNumber?pacerUserId=<your pacerUserId>&pacerClientCode=<your pacerClientCode>&caseNumber=2:10-cv-00001&courtId=CORTjF63b8Z4d2i9UB' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

The response is a **`PACERImportCase`** with **`courtFee`** (what the court charged for the lookup) and **`pacerImportCaseResultsArray`**:

PACER import response (excerpt)

```json
{  "object": "PACERImportCase",  "courtFee": 0.1,  "pacerImportCaseResultsArray": [    {      "object": "PACERImportCaseResults",      "hasOnlyMetaInfo": true,      "uniCourtContent": {        "object": "CaseSearchResult",        "caseId": "CASEgtaa7e66390d69",        "caseNumber": "2:10-cv-00001",        "caseName": "Rob J. Simmons v. California State Parole",        "caseAPI": "/workspace/{workspaceId}/case/CASEgtaa7e66390d69"      }    }  ]}
```

| Field | Meaning |
| --- | --- |
| **`courtFee`** | PACER charge for this find-case call (often `0` for district/bankruptcy; appeal courts may charge a minimum) |
| **`hasOnlyMetaInfo`** | `true` when only basic metadata is available until you run Case Update |
| **`uniCourtContent.caseId`** | The case ID to use for update and read calls |
| **`uniCourtContent.caseAPI`** | Path to the case once data is loaded |

If multiple matches return, pick the correct **`caseId`** from the array before continuing.

## Step 3 — Pull the full docket (Case Update)

Import alone does not give you parties, counsel, and docket entries. Submit a **Case Update** with **`pacerOptions`**:

Update imported PACER case

```Shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/caseUpdate' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>' \  -H 'Content-Type: application/json' \  -d '{  "caseId": "CASEgtaa7e66390d69",  "pacerOptions": {    "pacerUserId": "<your pacerUserId>",    "pacerClientCode": "<your pacerClientCode>"  }}'
```

Poll **GET /workspace/{workspaceId}/caseUpdate/{caseId}** until **`status`** is **`COMPLETE`** or **`FAILURE`**. See [Update a case once](../../common-use-cases/keep-cases-current/update-a-case-once.md) for status values, WebSocket delivery, and PACER-specific options like **`fetchType`** and **`additionalPageArray`**.

## Step 4 — Read the case

When the update completes, fetch the full case via **`caseAPI`** or follow [Read a full case](../../common-use-cases/find-and-read-cases/read-a-full-case.md).

Optional next steps:

- [Track a case on a schedule](../../common-use-cases/keep-cases-current/track-a-case-on-a-schedule.md) — keep the matter current
- [Getting documents from cases](../../common-use-cases/get-case-content/get-a-case-document.md) — download or order filings

## Don't have the case number yet?

When you only know a party name or rough attributes—not the exact case number and court—use **PACER Case Locator (PCL)** search endpoints instead:

PCL civil party search (excerpt)

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/pacerCaseLocator/partySearch/civilCourts?pacerUserId=<your pacerUserId>&pacerClientCode=<your pacerClientCode>&lastName=Smith&firstName=John&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

PCL paths, **`courtGroup`** values, and billing details: [PACER API — Case Locator](../../knowledge-base/pacer-api.md#pacer-case-locator-pcl).

## End-to-end flow

```mermaid
flowchart TD  A[Search Case Search first] --> B{Found?}  B -->|yes| C[Read case — done]  B -->|no| D[PUT pacerCredential if needed]  D --> E[GET pacer/importCaseByCourtUsingCaseNumber]  E --> F[Save caseId from results]  F --> G[PUT caseUpdate with pacerOptions]  G --> H[Poll until COMPLETE]  H --> I[GET case — full docket]
```

## v3 vs v2

| v2 | v3 |
| --- | --- |
| `GET /pacer/importCaseByCourtUsingCaseNumber` | `GET /workspace/{workspaceId}/pacer/importCaseByCourtUsingCaseNumber` |
| `PUT /pacerCredential` | `PUT /workspace/{workspaceId}/pacerCredential` |
| `caseAPI` without workspace prefix | `/workspace/{workspaceId}/case/{caseId}` |
| `pacerOptions.refreshType` on update | Root-level **`fetchType`** |

Base URL: **`https://deep-api.unicourt.com`**.

## Import vs search vs update

| Goal | Use |
| --- | --- |
| Find a case UniCourt may already have | [Search for cases](../../common-use-cases/find-and-read-cases/search-for-cases.md) |
| Look up a known PACER case number + court | **PACER import** (this walkthrough) |
| Pull full docket from PACER | [Update a case once](../../common-use-cases/keep-cases-current/update-a-case-once.md) with **`pacerOptions`** |
| Import state/local court case (not PACER) | [Case Import](../../knowledge-base/case-import.md) — different endpoint |
