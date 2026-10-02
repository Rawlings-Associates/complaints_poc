---
title: "UniCourt Data Standards"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/knowledge-base/unicourts-data-standards-and-voyager/
retrieved: 2026-10-01
---

# UniCourt Data Standards

UniCourt aggregates data from hundreds of court sources, each with its own terminology for case types, statuses, courts, and participant roles. **Data Standards** unify those labels into normalized categories with immutable IDs so you can search and compare across jurisdictions.

Browse the taxonomy in [**UniCourt Data Standards UI**](#), or resolve IDs programmatically through **Master Data** APIs under **`/workspace/{workspaceId}/masterData/…`** on **`deep-api.unicourt.com`**.

For how normalized IDs are used in cases and entities, see [Normalization](../knowledge-base/normalization-docs.md). For the prefix on each master-data ID type, see [Object ID Prefixes](../knowledge-base/object-id-prefixes.md).

## Why normalization matters

One portal may label a closed case **CLOSED**; another uses **DISPOSED**. Data Standards map both to a single normalized status (for example, **Closed**) with a stable **`caseStatusId`**:

![](/res-deep/assets/deep-v3-api-doc/assets/images/case-status-object-1-436ce2a9ad24e4508beb16a76673296e.png)

Flat one-level labels are often not enough. A portal “nature of suit” of **Unfair Dismissal** might normalize to:

- **Case Class:** Civil
- **Area of Law:** Labor and Employment
- **Case Type Group:** Labor and Employment
- **Case Type:** Wrongful Termination

![](/res-deep/assets/deep-v3-api-doc/assets/images/case-type-object-1-34775fd992c48ff5155da077c0478970.png)

This tiered structure lets you filter at the breadth you need— for example, all Labor and Employment cases— without listing every underlying case type manually.

## Normalized features in Data Standards

These classifications are available in the Data Standards UI and through Master Data APIs:

| Feature | Structure | v3 notes |
| --- | --- | --- |
| **Case Type** | Four tiers (class → area of law → type group → type) | Unchanged |
| **Case Status** | Two tiers (status group → status) | Unchanged |
| **Court** | Four tiers (system → type → court → location) | **`courtSourceId`** replaces v2 **`courtServiceStatusId`** on court objects |
| **Party Role** | Two tiers (role group → role) | Unchanged |
| **Counsel Role** | Single tier | Replaces v2 **Attorney Type**; used on **`Counsel.counselRole`** |
| **Party representation** | Enum on the **`Party`** object | Replaces v2 **Attorney Representation Type** master data; values include **`COUNSEL_REPRESENTED`**, **`SELF_REPRESENTED`**, **`UNREPRESENTED`**, **`NOT_YET_CLASSIFIED`** |
| **Judge Role** | Single tier | Replaces v2 **Judge Type** |
| **Case Relationship Type** | Single tier | Unchanged |

### Additional master data in v3

DEEP v3 adds Master Data endpoints not present in v2, including:

- **Case disposition** and **case event** (with groups)
- **Motion type** (category, group, type)
- **Outcome** and **procedural activity** (with groups)
- **Court source** and **tentative ruling source** metadata

See the [**Case Master Data API spec**](#) and [**Court Master Data API spec**](#) for the full endpoint list.

## Example: resolve a case status ID

List case statuses (filtered)

```Shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/{workspaceId}/masterData/caseStatus?q=name:(Closed)&pageNumber=1' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <Your JWT accessToken>'
```

Master Data list endpoints accept a **`q`** keyword expression and **`pageNumber`** for pagination, similar to search APIs. Use the **`caseStatusId`**, **`courtId`**, **`partyRoleId`**, or other IDs from the response in [Query Builders](../knowledge-base/query-builders.md) expressions against case search and analytics endpoints.

## Migration Notes for v2 Integrators

| v2 | v3 | Notes |
| --- | --- | --- |
| `/masterData/…` (account-scoped) | `/workspace/{workspaceId}/masterData/…` | Workspace token required |
| `GET /masterData/attorneyType` | `GET /workspace/{workspaceId}/masterData/counselRole` | Renamed concept; maps to **`counselRoleId`** on counsel |
| `GET /masterData/attorneyRepresentationType` | *(removed)* | Use **`Party.representationType`** enum instead |
| `GET /masterData/judgeType` | `GET /workspace/{workspaceId}/masterData/judgeRole` | Renamed to **`judgeRoleId`** |
| `courtServiceStatusId` | `courtSourceId` | On court and case objects |
| `https://enterpriseapi.unicourt.com/masterData/…` | `https://deep-api.unicourt.com/workspace/{workspaceId}/masterData/…` | Base URL change |
| Criminal master data (`causeOfAction`, `charge`, …) | *(removed from v3 Master Data)* | Do not map to unrelated endpoints |

Counsel-related terminology on cases follows the [Counsel object model](../knowledge-base/understanding-the-counsel-object.md): v2 **`attorneyType`** → v3 **`counselRole`**.
