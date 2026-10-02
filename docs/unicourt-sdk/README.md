# UniCourt Python SDK (reference copy)

`unicourt-1.0-py3-none-any.whl` is UniCourt's official Python SDK for the DEEP
v3 APIs, stored here for reference. **This project does not use it.**
`unicourt_state` talks to the API directly with the standard library.

| | |
| --- | --- |
| Package | `unicourt` 1.0, by UniCourt (support@unicourt.com) |
| License | Apache-2.0 (inside the wheel: `unicourt-1.0.dist-info/licenses/LICENSE`) |
| Python | 3.11 or later |
| Dependencies | `urllib3==2.7.0`, `python-dateutil==2.9.0.post0`, `pydantic==2.13.4`, `typing-extensions==4.16.0` |
| Supported API versions | `2026-07-15`, `2026-08-03`, per [the SDK page](../unicourt-deep-v3-api-docs/knowledge-base/python-sdk.md) |
| SHA-256 | `bbadbfcffd8824e17dcabdcb4eef98113d9e5a0463e23838d91a527904a134ae` |
| Archived | 2026-10-01 |

**Contents.** The SDK is generated from the OpenAPI spec (OpenAPI Generator):

- `unicourt/api/`: one module per API group.
- `unicourt/model/`: the request and response models.
- `unicourt/sdk/`: the friendlier wrappers that the docs use, such as
  `CaseSearch` and `Authentication`.

**Notes for this project:**

- **Base URL:** the SDK's default host is `https://deep-api.unicourt.com`, with
  no `/v3`, which matches `unicourt_state` and the live check recorded in
  [../unicourt-deep-v3-api-docs/ARCHIVE-NOTES.md](../unicourt-deep-v3-api-docs/ARCHIVE-NOTES.md).
- **No rate-limit handling:** the SDK has no handling of the 30 requests per 5
  seconds limit and no retry on 429. Callers must do that themselves, as
  `unicourt_state` does.

**Inspecting or trying it** in a separate virtual environment, so its pinned
dependencies stay out of this project:

```console
$ unzip -l docs/unicourt-sdk/unicourt-1.0-py3-none-any.whl     # list the contents
$ python3.11 -m venv .venv-sdk && . .venv-sdk/bin/activate
$ pip install docs/unicourt-sdk/unicourt-1.0-py3-none-any.whl
```

Usage is documented in
[../unicourt-deep-v3-api-docs/knowledge-base/python-sdk.md](../unicourt-deep-v3-api-docs/knowledge-base/python-sdk.md).
That page's "Download" links are `#` placeholders in the scraped copy. The
wheel is this file.
