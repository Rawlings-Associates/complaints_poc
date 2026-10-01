---
title: "Allowlisting & IP Whitelisting"
source: https://dart.unicourt.com/res-deep/assets/deep-v3-api-doc/getting-started/white-list/
retrieved: 2026-10-01
---

# Allowlisting & IP Whitelisting

This page covers two related but different controls:

- **Allowlisting** is what *your* network does: if your organization filters outbound (egress) traffic, you must permit UniCourt’s domains so DEEP API calls, callbacks, document downloads, and DART links are not blocked by your firewall.
- **IP Whitelisting** is what *UniCourt* does: you restrict which client IP addresses may call the DEEP API. Configure it on the **API Security** page in DART.

## Allowlisting

If your organization controls outbound (egress) traffic, you must allowlist UniCourt. Configure the domains below so your DEEP v3 API calls, WebSocket callbacks, document downloads, and DART links are not blocked.

### v3 domains

DEEP v3 and DART domains to allowlist

| Domain | Protocol | Port | Used by |
| --- | --- | --- | --- |
| deep-api.unicourt.com | HTTPS | 443 | DEEP v3 REST API |
| deep-callbacks.unicourt.com | WSS | 443 | DEEP v3 WebSocket callbacks |
| dart.unicourt.com | HTTPS | 443 | DART |
| casedocs.unicourt.com | HTTPS | 443 | Case document downloads |
| casedocs2.unicourt.com | HTTPS | 443 | Case document downloads |
| ctf.unicourt.com | HTTPS | 443 | Court document retrieval |

## IP Whitelisting

Use **IP Whitelisting** on the **API Security** page to restrict DEEP API access to trusted IP addresses. When no IP addresses are configured, API access is allowed from any IP address. Once you add one or more IPs for a scope, only those IPs are permitted for that scope. Requests blocked by IP Whitelisting return **403 Forbidden**.

There are two levels:

| Level | Applies to | Behavior |
| --- | --- | --- |
| **Account IPs** | All account tokens and all workspace tokens for the account | If any account IP is listed, only listed account IPs may call the API for this account. |
| **Workspace IPs** | Tokens for a selected workspace | Applied **in addition to** Account IPs, and only for that workspace. |

**Workspace IPs** are useful when you share a **workspace token** with a third party and want that token usable only from a specific IP. If both account and workspace lists have IPs, then the requested IP should be present in one of the lists in order to be accessible.

### Configure IP Whitelisting

1. Open **API Security** in DART (Platform sidebar).
2. In the **IP Whitelisting** section, add **Account IPs** and, if needed, select a workspace and add **Workspace IPs**.
3. For each entry, provide a **Name**, an **IP address**, and an optional CIDR mask (for example `/32` for a single host).

Default behavior is unchanged until you add IPs: an empty list means nothing is restricted. After IPs are added, only those IPs are allowed for that scope.
