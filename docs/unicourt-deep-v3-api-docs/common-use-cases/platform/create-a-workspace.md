---
title: "Create a Workspace"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/common-use-cases/platform/create-a-workspace/
retrieved: 2026-10-01
---

# Create a Workspace

You need a **`workspaceId`** before you can call almost any DEEP data endpoint. Create a workspace once (or once per team / environment / project), store the ID, then use it in every `/workspace/{workspaceId}/...` path.

**Reference docs:** [Account & Workspace Management](../../getting-started/account-workspace-management.md) (concepts and token scopes), [Authentication](../../getting-started/authentication.md) (account tokens).

Spec: [**`PUT /workspaceCreate`**](#).

## Before you start

| You need | Notes |
| --- | --- |
| **Account token** | `POST /generateNewToken` — workspace create is an account-level operation |
| **Workspace name** | The only required request field |

Base URL: **`https://deep-api.unicourt.com`**.

Spec vs behavior

Some OpenAPI fields for `workspaceCreate` are marked required. In practice, **`workspaceName` is the only required field**. You may omit `workspaceId`, `description`, `workspaceTemplateId`, and `workspaceTemplateFieldValues` entirely—not only leave them empty.

## Step 1 — Create with an auto-generated ID

Omit `workspaceId`. UniCourt generates a unique workspace ID and returns it in the response.

- cURL-Bash
- cURL-Powershell
- cURL-CMD

Create workspace (auto-generated ID)

```shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/workspaceCreate' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <accountToken>' \  -H 'Content-Type: application/json' \  -d '{  "workspaceName": "Claims research — staging"}'
```

Create workspace (auto-generated ID)

```shell
curl.exe -X 'PUT' `  'https://deep-api.unicourt.com/workspaceCreate' `  -H 'accept: application/json' `  -H 'Authorization: Bearer <accountToken>' `  -H 'Content-Type: application/json' `  -d @"{  \"workspaceName\": \"Claims research — staging\"}"@
```

Create workspace (auto-generated ID)

```shell
curl -X "PUT" ^  "https://deep-api.unicourt.com/workspaceCreate" ^  -H "accept: application/json" ^  -H "Authorization: Bearer <accountToken>" ^  -H "Content-Type: application/json" ^  -d "{^  ""workspaceName"": ""Claims research — staging""^}"
```

CreateWorkspaceResponse

```json
{  "object": "CreateWorkspaceResponse",  "workspaceId": "a1b2c3d4",  "message": "Workspace created successfully."}
```

Save `workspaceId` from the response. You will need it for every workspace-scoped call and if you generate a [workspace token](../../getting-started/authentication.md#generate-a-workspace-token).

## Step 2 — Or create with your own workspace ID

Pass `workspaceId` when you want a stable, known value (for example to match an internal project code). Rules:

- Letters (`A–Z`, `a–z`) and numbers (`0–9`) only
- Length 1–10
- No spaces, special characters, underscores, or hyphens

Create workspace (custom ID)

```shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/workspaceCreate' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <accountToken>' \  -H 'Content-Type: application/json' \  -d '{  "workspaceId": "claims01",  "workspaceName": "Claims research — staging",  "description": "Staging workspace for claims integrations"}'
```

`description` is optional, as are `workspaceTemplateId` and `workspaceTemplateFieldValues`. Include them only when you are applying a workspace template and its custom field values.

## Optional — Create in DART instead

You can create workspaces in the DART UI without calling the API. For full details, open the Help Center in DART. Short path: go to **All Workspaces** and click **Create** in the top right, or use **New Workspace** in the sidebar workspace selector for a quick setup.

## Next steps

1. Confirm the workspace with `GET /workspaces` or `GET /workspaces/search?q=...`.
2. Call a data endpoint under `/workspace/{workspaceId}/...` with your account token (or generate a workspace token if you need a narrower credential).
3. See [Working with UniCourt APIs](../../getting-started/working-with-unicourt-apis.md) for a first search-and-read flow.
