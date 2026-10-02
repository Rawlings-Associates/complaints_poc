---
title: "Account & Workspace Management"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/getting-started/account-workspace-management/
retrieved: 2026-10-01
---

# Account & Workspace Management

DEEP v3 organizes nearly all API activity inside **workspaces**. This page explains what workspaces are, how they relate to your account and tokens, and how to create and find them. For Client ID / Client Secret and token lifecycle details, see [Authentication](../getting-started/authentication.md). For a full create walkthrough, see [Create a workspace](../common-use-cases/platform/create-a-workspace.md).

## What a workspace is

A workspace is a named container for organizing activity and API calls. You can structure workspaces however fits your organization—one workspace for everything, or separate workspaces by team, business unit, environment, or project.

Virtually all data endpoints are scoped to a workspace. Paths look like `/workspace/{workspaceId}/...`. Every call you make under that path is attributed to that workspace, so activity, usage, and data stay organized at the workspace level. You can still view usage at the [account level or the workspace level](../getting-started/usage-limits-billable-activities.md#workspaces-and-limits).

Account-level operations (creating workspaces, listing them, and most token management) do not use the workspace path prefix. If an endpoint acts on litigation or entity data, expect `/workspace/{workspaceId}/...`.

## Account tokens vs workspace tokens

Authentication still uses a Bearer token in the `Authorization` header. DEEP supports two token types:

| Token type | Scope | When to use it |
| --- | --- | --- |
| **Account token** | Full account; works with account-level and workspace-scoped APIs | Account-level operations. Also usable for day-to-day data work across one or many workspaces when a single credential that can reach any of them is acceptable. |
| **Workspace token** | One specific workspace only | Day-to-day data work when you need to limit access to a single workspace, such as isolating a specific application instance or environment. |

Account tokens work with workspace-scoped endpoints. When you include a `workspaceId` in the URL, usage is automatically counted toward that workspace. You do not need a workspace token just to separate activity across workspaces.

Generate an account token with `POST /generateNewToken`. Generate a workspace token with `POST /generateNewWorkspaceToken`. For credentials, rotation, and invalidation, see [Authentication](../getting-started/authentication.md).

## Create a workspace

You can create a workspace in the API or in DART.

### In the API

Call [**`PUT /workspaceCreate`**](#) with an **account token**.

The only required field is **`workspaceName`**. These fields are all optional—you may omit them entirely:

| Field | Behavior |
| --- | --- |
| `workspaceId` | Optional. Supply your own ID (see rules below), or omit it and UniCourt auto-generates a unique ID in the response. |
| `description` | Optional. |
| `workspaceTemplateId` | Optional. |
| `workspaceTemplateFieldValues` | Optional. |

If you set `workspaceId` yourself, it must:

- Contain only letters (`A–Z`, `a–z`) and numbers (`0–9`)
- Be between 1 and 10 characters
- Contain no spaces, special characters, underscores, or hyphens

Step-by-step request and response examples: [Create a workspace](../common-use-cases/platform/create-a-workspace.md).

### In DART

You can also create workspaces directly in DART. For full UI details, use the Help Center in DART. Short version: go to the **All Workspaces** page and use **Create** in the top right, or use the **New Workspace** button in the sidebar workspace selector for a quick setup.

## List and search workspaces

Once you have an account token:

| Method | Endpoint | What it does |
| --- | --- | --- |
| `GET` | `/workspaces` | List workspaces for the account (paginated) |
| `GET` | `/workspaces/search?q=...` | Search workspaces with keyword expressions (name, ID, description, template fields, and more) |

Use the list or search response to obtain a `workspaceId`, then call data endpoints under `/workspace/{workspaceId}/...`.

## Related

- [Create a workspace](../common-use-cases/platform/create-a-workspace.md) — full `workspaceCreate` walkthrough
- [Authentication](../getting-started/authentication.md) — Client ID / Client Secret, account and workspace tokens
- [Working with UniCourt APIs](../getting-started/working-with-unicourt-apis.md) — first request and workspace path conventions
- [Usage, Limits, and Billable Activity](../getting-started/usage-limits-billable-activities.md) — account-level allotments vs workspace reporting
