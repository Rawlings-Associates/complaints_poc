---
title: "API Versioning"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/getting-started/api-versioning/
retrieved: 2026-10-01
---

# API Versioning

This page is the contract for the DEEP v3 API. Read it to understand what is safe to build on for production, how to tell when a change requires action on your side, and how much runway you have before anything is retired.

## What is versioned

The DEEP API is versioned at General Availability (GA). GA is feature-complete and production-safe, and it is where the versioning contract on this page lives. Breaking changes are never made to a GA version in place; they ship as a new versioned release.

Beta capabilities are public but unversioned and may change as they evolve. If you need a stable API contract, build on GA.

## Versioning model

GA uses calendar-based versioning. Each GA release is identified by its release date.

### Calendar versions

A release is named by its date in `YYYY-MM-DD` form, for example `2026-08-03`. You pin to a version, and you are never moved off it without your action.

### Pinning a version

Send the version in a request header. All calls then run against that version's behavior.

```http
X-API-Version: 2026-08-03
```

If you omit the header, the API responds with the latest version.

```http
X-API-Latest-Version: 2026-08-03
```

Important

Omitting the header may be convenient while you build, but it is not recommended for production, because a future release could change behavior under you. Every response reports the current latest version, so you always know whether your pinned version is behind.

If your pinned version is deprecated, two more headers appear in the response: `X-API-Deprecated` and `X-API-Sunset`.

| Header | Description |
| --- | --- |
| `X-API-Version` | Version used to process the request |
| `X-API-Latest-Version` | Latest version available |
| `X-API-Deprecated` | Indicates whether the requested version is deprecated |
| `X-API-Sunset` | Sunset date for deprecated versions |

A deprecated request also returns a standard HTTP warning header describing the sunset date and recommended replacement:

```http
HTTP/1.1 200 OKContent-Type: application/jsonX-API-Version: 2026-07-15X-API-Latest-Version: 2026-08-03X-API-Deprecated: trueX-API-Sunset: 2027-02-03Warning: 299 - "This API version is deprecated and will sunset on 2027-02-03. Please upgrade to 2026-08-03."
```

Recommended

Pin a version in production with `X-API-Version`, and watch `X-API-Latest-Version` so you know when a newer version is available.

## Version behavior at a glance

| Scenario | Behavior |
| --- | --- |
| Version provided and supported | The requested version is used |
| Version omitted | The latest version is used |
| Deprecated version | Request succeeds, and deprecation metadata is returned |
| Sunset version | Request is rejected with an error |
| Unsupported or invalid version | Request is rejected with an error indicating the version isn't supported |

## WebSocket APIs

WebSocket connections are versioned the same way as REST calls, but the version travels in the handshake instead of a request header.

### Connection request

The API version is specified during the WebSocket handshake using the `Sec-WebSocket-Protocol` header. If no version is provided, the server connects using the latest supported version.

```http
GET /ws HTTP/1.1Host: deep-api.unicourt.comUpgrade: websocketConnection: UpgradeSec-WebSocket-Protocol: 2026-08-03
```

### Connection acknowledgement

After a successful connection, the server sends a `connection_ack` event containing the negotiated API version and version metadata.

```json
{  "type": "connection_ack",  "status": "connected",  "api": {    "version": "2026-08-03",    "latestVersion": "2026-08-03",    "deprecated": false,    "sunset": null  },  "timestamp": "2026-08-03T06:37:09.887Z"}
```

If the negotiated version is deprecated, the `connection_ack` event carries the same metadata you'd see in REST response headers, plus a warning message:

```json
{  "type": "connection_ack",  "status": "connected",  "api": {    "version": "2026-07-15",    "latestVersion": "2026-08-03",    "deprecated": true,    "sunset": "2027-02-03",    "warning": "This API version is deprecated and will sunset on 2027-02-03. Please upgrade to 2026-08-03."  },  "timestamp": "2026-08-03T06:37:09.887Z"}
```

## Version lifecycle

Every GA version moves through three stages. The retirement clock for a version starts when its successor is released.

- **Active / Latest:** Fully supported and recommended for new integrations. Receives full feature development, bug fixes, and security updates. Stays active indefinitely until it is deprecated.
- **Deprecated:** Functional but no longer recommended, with a successor version available. Receives critical fixes and security patches only. Carries an assigned retirement date.
- **Retired:** No longer functional. Calls pinned to a retired version will fail.

Important

Deprecated versions are likely to be less reliable than active versions. We urge you to move to an active version to maintain the highest level of support and reliability.

## Migrating to a new version

When a version you depend on is deprecated, you can migrate on your own schedule as long as you finish before the retirement date.

1. **Review the release notes for the successor.** See what changed and what your integration needs to account for.
2. **Pin the new version in a staging environment.** Set `X-API-Version` to the new date and test against it.
3. **Verify your integration.** Confirm that responses, pagination, and any fields your code depends on behave as expected.
4. **Deploy to production.** Update the pinned version, then confirm it matches `X-API-Latest-Version` in responses.

## Support and notifications

When a new GA version is released, the previous version is deprecated. Deprecated versions remain available for at least six months from the successor's release date, after which they are retired.

## Auditing your version usage

To find out which versions your integration is calling, and whether any are deprecated:

- Compare the `X-API-Latest-Version` response header against the version you pin. If they differ, you are behind.
- Review your call volume with `GET /workspace/{workspaceId}/monthlyUsage/{month}` and `GET /workspace/{workspaceId}/dailyUsage/{date}`.
- If you run multiple integrations, audit each one's pinned version against the release notes so you can prioritize migrations before any retirement date.

## Version status

Current GA versions are listed below with their status. Example lifecycle rows are shown separately so they are not confused with live production status.

### Current GA versions

| Version | Current State | Deprecated | Retirement date |
| --- | --- | --- | --- |
| `2026-08-03` | Active | N/A | N/A |
| `2026-07-15` | Deprecated | `2026-08-03` | `2027-02-03` |

### Example lifecycle

Example only

The rows below are illustrative and do not represent live DEEP API version status.

| Version | Current State | Deprecated | Retirement date |
| --- | --- | --- | --- |
| `2026-10-15` | Active | N/A | N/A |
| `2026-07-15` | Deprecated | `2026-10-15` | `2027-04-15` |
| `2026-04-01` | Retired | `2026-07-15` | `2027-01-15` |
