---
title: "Authentication"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/getting-started/authentication/
retrieved: 2026-10-01
---

# Authentication

Every DEEP request is authenticated with a bearer token. This page covers where your credentials come from, the two token scopes and when to use each, how to generate and send a token, and how to list, rotate, and invalidate tokens over their lifetime.

For a quick orientation to authentication in the context of a first call, see [Working with UniCourt APIs](../getting-started/working-with-unicourt-apis.md). This page is the full reference.

## Credentials: Client ID and Client Secret

Each API subscriber is issued a **Client ID** and a **Client Secret**. The Client ID is like a username and the Client Secret is like the password that goes with it. Both are alphanumeric strings, and both appear in [**your user profile**](#). You should protect your Client Secret against unauthorized disclosure. Any individual or organization that knows your Client Secret can access the UniCourt API on your behalf and incur charges in connection with that access. You can issue a fresh secret at any time with the **Rotate Secret** button on your API Security page, and you should do so whenever you believe a secret has been exposed. Doing so will invalidate all tokens. This documentation assumes that software developers who use the UniCourt API have reasonable practices for securing API access credentials.

## The two token scopes

DEEP tokens come in two scopes. Pick the one that matches the operation.

| Scope | Use it for | Generate with |
| --- | --- | --- |
| **Account token** | Account-wide operations, including creating and managing workspaces | `POST /generateNewToken` |
| **Workspace token** | Day-to-day data calls scoped to one workspace (search, read, track, order) | `POST /generateNewWorkspaceToken` |

Most of your calls use a workspace token. You reach for an account token when you are managing workspaces or performing other account-level administration. A workspace token only grants access to the single workspace it was issued for. For how workspaces relate to accounts and when each token scope fits, see [Account & Workspace Management](../getting-started/account-workspace-management.md).

## Generate an account token

Exchange your Client ID and Client Secret for an account token by calling `POST /generateNewToken`. UniCourt validates the credentials together with your incoming host or IP address, then returns a token.

- cURL-Bash
- cURL-Powershell
- cURL-CMD

Generate account token

```shell
curl -X 'POST' \  'https://deep-api.unicourt.com/generateNewToken' \  -H 'accept: application/json' \  -H 'Content-Type: application/json' \  -d '{  "clientId": "<your clientId>",  "clientSecret": "<your clientSecret>"}'
```

Generate account token

```shell
curl.exe -X 'POST' `  'https://deep-api.unicourt.com/generateNewToken' `  -H 'accept: application/json' `  -H 'Content-Type: application/json' `  -d @"{  \"clientId\": \"<your clientId>\",  \"clientSecret\": \"<your clientSecret>\"}"@
```

Generate account token

```shell
curl -X "POST" ^  "https://deep-api.unicourt.com/generateNewToken" ^  -H "accept: application/json" ^  -H "Content-Type: application/json" ^  -d ^"{^  ""clientId"": ""<your clientId>"",^  ""clientSecret"": ""<your clientSecret>""^}"
```

The response returns the token and its ID:

Account token response

```json
{  "object": "AccessTokenResponse",  "accessToken": "<your JWT accessToken>",  "tokenId": "<tokenId>",  "tokenType": "Bearer"}
```

## Generate a workspace token

A workspace token is scoped to a single workspace. Generate one with `POST /generateNewWorkspaceToken`, supplying your Client ID, Client Secret, and the target `workspaceId` in the request body. Unlike account-token calls, this endpoint does not take an account access token in the `Authorization` header; your credentials and the `workspaceId` are all it needs.

- cURL-Bash
- cURL-Powershell
- cURL-CMD

Generate workspace token

```shell
curl -X 'POST' \  'https://deep-api.unicourt.com/generateNewWorkspaceToken' \  -H 'accept: application/json' \  -H 'Content-Type: application/json' \  -d '{  "clientId": "<your clientId>",  "clientSecret": "<your clientSecret>",  "workspaceId": "<your workspaceId>"}'
```

Generate workspace token

```shell
curl.exe -X 'POST' `  'https://deep-api.unicourt.com/generateNewWorkspaceToken' `  -H 'accept: application/json' `  -H 'Content-Type: application/json' `  -d @"{  \"clientId\": \"<your clientId>\",  \"clientSecret\": \"<your clientSecret>\",  \"workspaceId\": \"<your workspaceId>\"}"@
```

Generate workspace token

```shell
curl -X "POST" ^  "https://deep-api.unicourt.com/generateNewWorkspaceToken" ^  -H "accept: application/json" ^  -H "Content-Type: application/json" ^  -d ^"{^  ""clientId"": ""<your clientId>"",^  ""clientSecret"": ""<your clientSecret>"",^  ""workspaceId"": ""<your workspaceId>""^}"
```

The response returns the token along with its workspace and token IDs:

Workspace token response

```json
{  "object": "WorkspaceAccessToken",  "workspaceId": "<your workspaceId>",  "workspaceTokenId": "<workspaceTokenId>",  "accessToken": "<your JWT accessToken>",  "tokenType": "Bearer"}
```

## Send the token

All endpoints other than the token-generation calls require a token in the request header:

```text
Authorization: Bearer <your accessToken>
```

Provide this header wherever the documentation shows an authenticated request. Use a workspace token for data calls and an account token for account-level operations.

A workspace token is valid only for the workspace it was issued for. If you call a data endpoint under a different `workspaceId`—even with a still-valid workspace token—the API returns **`Unauthorized`**. The token itself has not expired or been invalidated; the path simply does not match the workspace the token belongs to.

Valid workspace token, mismatched workspaceId

```shell
curl -X 'GET' \  'https://deep-api.unicourt.com/workspace/<otherWorkspaceId>/...' \  -H 'accept: application/json' \  -H 'Authorization: Bearer <workspaceTokenForDifferentWorkspace>'
```

Unauthorized response

```json
{  "message": "Unauthorized"}
```

## Token lifetime and limits

You can hold up to ten account tokens at a time; the limit is per account. Each workspace can independently hold up to ten workspace tokens; that limit is per workspace, so a ten-token workspace does not affect your account token count or any other workspace's count. Both token types have no expiration date and stay valid until you invalidate them, so invalidating tokens you no longer use is the main way to keep each set clean and under its limit.

When you rotate your Client Secret, use the new secret to generate new tokens (account or workspace) going forward. Previously issued tokens remain valid after a secret rotation, so rotate the secret to cut off future token generation and separately invalidate any existing tokens you want to revoke.

## Manage account tokens

### List account tokens

Retrieve your existing account token IDs, each with its issue date and the address it was issued to:

List account token IDs

```shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/listAllTokenIds' \  -H 'accept: application/json' \  -H 'Content-Type: application/json' \  -d '{  "clientId": "<your clientId>",  "clientSecret": "<your clientSecret>"}'
```

List account token IDs response

```json
{  "object": "AccessTokenIdListResponse",  "accessTokenIdArray": [    {      "object": "AccessTokenIdResponse",      "tokenId": "<tokenId>",      "issuedDate": "2023-02-13T04:07:13+00:00",      "issueAddress": "<issue address>"    }  ]}
```

### Invalidate one account token

Invalidate an account token

```shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/invalidateToken' \  -H 'accept: application/json' \  -H 'Content-Type: application/json' \  -d '{  "clientId": "<your clientId>",  "clientSecret": "<your clientSecret>",  "tokenId": "<tokenId>"}'
```

Invalidate account token response

```json
{  "object": "Success",  "message": "Access token invalidated successfully."}
```

### Invalidate all account tokens

Invalidate all account tokens

```shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/invalidateAllTokens' \  -H 'accept: application/json' \  -H 'Content-Type: application/json' \  -d '{  "clientId": "<your clientId>",  "clientSecret": "<your clientSecret>"}'
```

Invalidate all account tokens response

```json
{  "object": "Success",  "message": "All the access tokens are invalidated successfully."}
```

## Manage workspace tokens

Workspace tokens have their own management endpoints, separate from account tokens. Each call is scoped by `workspaceId` and authenticates with your Client ID and Client Secret, the same pattern used to generate the token in the first place.

### List workspace tokens

Retrieve the active workspace token IDs for a given workspace, each with its issue date and the address it was issued to:

List workspace token IDs

```shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/listAllWorkspaceTokenIds' \  -H 'accept: application/json' \  -H 'Content-Type: application/json' \  -d '{  "clientId": "<your clientId>",  "clientSecret": "<your clientSecret>",  "workspaceId": "<your workspaceId>"}'
```

List workspace token IDs response

```json
{  "object": "WorkspaceAccessTokenIdsResponse",  "workspaceId": "<your workspaceId>",  "workspaceAccessTokenIdArray": [    {      "object": "WorkspaceAccessTokenId",      "workspaceTokenId": "<workspaceTokenId>",      "issuedDate": "2025-11-10T10:17:56+00:00",      "issueAddress": "<issue address>"    }  ]}
```

### Invalidate one workspace token

Target a single workspace token for revocation, leaving the workspace's other tokens active. You can get a `workspaceTokenId` from the list call above.

Invalidate a workspace token

```shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/invalidateWorkspaceToken' \  -H 'accept: application/json' \  -H 'Content-Type: application/json' \  -d '{  "clientId": "<your clientId>",  "clientSecret": "<your clientSecret>",  "workspaceId": "<your workspaceId>",  "workspaceTokenId": "<workspaceTokenId>"}'
```

Invalidate workspace token response

```json
{  "object": "Success",  "message": "Access token invalidated successfully."}
```

### Invalidate all workspace tokens

Revoke every active token for a given workspace in one call. This does not affect tokens for any other workspace, or your account token.

Invalidate all workspace tokens

```shell
curl -X 'PUT' \  'https://deep-api.unicourt.com/invalidateAllWorkspaceTokens' \  -H 'accept: application/json' \  -H 'Content-Type: application/json' \  -d '{  "clientId": "<your clientId>",  "clientSecret": "<your clientSecret>",  "workspaceId": "<your workspaceId>"}'
```

Invalidate all workspace tokens response

```json
{  "object": "Success",  "message": "All workspace access tokens invalidated successfully."}
```

## Host and IP Whitelisting

If you configure **IP Whitelisting** on the **API Security** page, UniCourt validates the caller’s IP address. When the list for a scope is empty, all IPs are allowed. Once IPs are added, requests from addresses outside that list fail with **403 Forbidden** even with valid credentials. Account IPs apply to all tokens for the account; workspace IPs apply only to a selected workspace and must also appear on the account list. Set up allowed addresses before relying on restricted access. See [Allowlisting & IP Whitelisting](../getting-started/white-list.md) for domain allowlisting and IP Whitelisting setup.

## Best practices

- Store the Client Secret and tokens in environment variables or a secrets manager. Never commit them.
- Use a workspace token for data calls and reserve the account token for account-level work.
- Rotate the Client Secret on any suspected exposure, then invalidate existing tokens you want to revoke.
- Invalidate account and workspace tokens you no longer use so each stays under its ten-token limit.
