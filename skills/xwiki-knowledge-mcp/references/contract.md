# xWiki Knowledge Action Contract

Use the connected server's live schema as the authority. This reference records
the repository's current `knowledge` tool so the skill remains useful outside a
checkout.

## Request envelope

Tool arguments are a JSON object containing one `requests` list with 1-10
independent actions. Every item requires `action`; unknown fields are rejected.

| Action | Required besides `action` | Optional fields |
| --- | --- | --- |
| `search` | None | `query`, `pageType`, `status`, `limit`, `includeSources` |
| `browse` | None | `pageId`, `limit`, `offset` |
| `view` | `pageId` | `section`, `offset`, `maxCharacters`, `version` |
| `read` | `sourcePath` | `start`, `limit` |

Use returned values rather than titles or example paths invented from memory.
Items in the same batch cannot reference one another's output.

## Search

- `query` is optional lexical text up to 500 characters. Empty text lists Wiki
  pages under any supplied filters.
- `pageType` is one of `topic`, `concept`, `entity`, `source`, `synthesis`,
  `question`, `timeline`, `index`, `log`, or `unknown`.
- `status` is `draft`, `active`, or `needs-review`.
- `limit` is 1-100 and defaults to 10. `includeSources` defaults to true.

Normalized query terms combine with AND. Search covers Wiki page metadata and
bodies, section bodies, and optionally extracted originals. A `pageType` or
`status` filter scopes the result to Wiki pages and suppresses raw-source hits.
Results have `kind: page` or `kind: source`; page hits can include matching
section IDs, while source hits include a `sourcePath`, warnings, and matching
segment ordinals. `candidatePoolTruncated: true` means more candidates existed
than were ranked, so a negative or partial result is not exhaustive.

## Browse

Without `pageId`, `browse` returns L0 topics. `limit` is 1-1000, `offset` is
nonnegative, and the response includes `total`, `offset`, and `topics`.

With a returned `pageId`, `browse` returns that page's graph neighborhood:
`outgoing`, `incoming`, cited `sources`, source-page `citedBy` pages, and a
`truncated` flag. Each edge reports its direction-specific page ID, relation,
and resolution details. `offset` does not paginate a page neighborhood in the
current implementation; reduce or increase `limit` deliberately.

## View

An initial `view` requires only a returned `pageId`. It returns bounded `body`,
page metadata, all section descriptors, cited sources, a content-hash `version`,
and continuation fields.

`section` uses a returned ID such as `section-3`, never a guessed heading.
Section reads and all nonzero `offset` reads require the initial `version`.
`maxCharacters` is 1,000-50,000 and defaults to 12,000. Continue with the same
page, optional section, and version at `nextOffset`. A version mismatch means
the page changed; restart from an initial view instead of joining snapshots.

## Read original-source extraction

`read` requires an indexed `sourcePath` beginning with `_raw/`, normally
discovered through `search`, `browse`, or `view`. `start` is a zero-based source
segment ordinal and defaults to 0. `limit` is 1-10 and defaults to 3.

The result includes source identity and hash, extraction warnings,
`totalSegments`, bounded `segments`, and `nextStart`. Each segment carries its
ordinal, heading, extracted text, and format-specific `locator`. The server
verifies that the original remains under `_raw/` and that its current SHA-256
matches the index before returning text.

Extraction does not perform OCR, interpret figures, preserve every table layout,
or evaluate spreadsheet formulas. A valid locator proves where text came from,
not that a downstream interpretation is correct.

## Results and failures

The batch result has `total`, `succeeded`, `failed`, and ordered `results`. Each
item has zero-based `requestIndex`, `action`, `ok`, and either `result` or
`error: {code, detail}`. Inspect every item even when the MCP call itself
succeeds.

Common failures:

| Condition | Handling |
| --- | --- |
| Missing or incompatible database | Ask the vault maintainer to build the index; retrieval must not build it |
| Empty successful search | Try justified synonyms or narrower individual terms; disclose changed queries |
| Invalid or ambiguous page ID | Rediscover an exact `pageId` through search or browse |
| Missing `version` | Repeat an initial page view, then use the returned version |
| Page version changed | Discard partial text and restart that page view |
| Source changed after indexing | Do not claim it was read; ask for an offline rebuild |
| Source text unavailable | Use Wiki evidence or report that original extraction is unavailable |
| Transport failure | Retry at most once when useful, then report the evidence gap |

The local tool returns repository-relative paths rather than public URLs. Keep
those paths and physical locators in citations; do not fabricate web links or
expose machine-specific absolute paths.
