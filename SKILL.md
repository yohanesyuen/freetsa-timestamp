---
name: freetsa-timestamp
description: Get a cryptographic, trusted-third-party proof of when a file Claude produced existed, using FreeTSA's free RFC 3161 timestamping authority. Use this whenever the user asks to "timestamp," "notarize," "prove when this was created," "get a trusted timestamp," or wants tamper-evident, dateable proof of a file's existence and provenance (e.g. for compliance, IP/prior-art records, audit trails, or chain-of-custody on AI-generated output) — even if they don't mention FreeTSA by name. Also use when the user mentions FreeTSA, RFC 3161, or TSA timestamping directly.
---

# FreeTSA Timestamping

## What this does and why

A timestamp from a Trusted Timestamping Authority (TSA) is third-party,
cryptographic proof that specific data existed at or before a specific time —
and that it hasn't changed since. Unlike a file's mtime (trivially fakeable),
a TSA timestamp is a digitally signed token from an independent server that
nobody party to the conversation controls. This is useful any time someone
might later need to show "this file, in this exact form, existed by this
date" — prior-art records, audit trails, compliance evidence, or just an
honest record of what Claude produced and when.

[FreeTSA](https://freetsa.org) runs a free public RFC 3161 timestamping
service. It signs a hash of whatever you send it and returns a signed token
(a `.tsr` file) — it never sees or stores your actual data, only a hash.

## The provenance envelope

Don't timestamp the raw file by itself — a timestamp on file bytes alone
proves the bytes existed, but says nothing about where they came from. Wrap
the file in a small JSON envelope that records *provenance*, then timestamp
the envelope. That way the timestamp also vouches for the metadata.

The envelope has these fields:

| Field | Who fills it in | Meaning |
|---|---|---|
| `data` | script (automatic) | The file's raw content if it's plaintext, otherwise base64 |
| `req_param` | **you, the calling Claude** | The parameters used to retrieve/produce the data (e.g. the API params, search query, prompt) |
| `retrieved_at` | **you, the calling Claude** | ISO 8601 timestamp of when the tool response was retrieved/generated |
| `source_of_data` | **you, the calling Claude** | Where the data came from / how it was generated (e.g. "WebFetch of https://...", "computed from user-provided CSV") |
| `tool_calls` | **you, the calling Claude** | What tools were used and what requests were passed in — e.g. `[{"tool": "WebFetch", "input": {"url": "..."}}]` |

The three `req_param` / `source_of_data` / `tool_calls` fields and
`retrieved_at` are things only you — the Claude session that produced the
file — actually know. Don't try to infer them from the file itself or leave
them vague; pull them from your own conversation context (what tool calls you
just made, what arguments you passed, when the response came back). If you
genuinely produced the file without any tool call (e.g. you wrote prose
directly), say so plainly: `"source_of_data": "Generated directly by Claude from the conversation, no external tool calls"` and `"tool_calls": []`.

## Workflow

1. **Identify the file to timestamp** — something Claude already wrote to disk in this conversation.

2. **Write a metadata JSON file** with the four fields above. Example:

   ```json
   {
     "req_param": {"url": "https://api.example.com/v1/widgets?since=2026-06-01"},
     "retrieved_at": "2026-06-20T14:32:00Z",
     "source_of_data": "Fetched via WebFetch from the public widgets API, then reformatted into a CSV",
     "tool_calls": [
       {"tool": "WebFetch", "input": {"url": "https://api.example.com/v1/widgets?since=2026-06-01"}}
     ]
   }
   ```

   Save it somewhere temporary, e.g. `meta.json` next to the target file.

3. **Run the timestamping script**:

   ```bash
   python scripts/timestamp_file.py <target_file> --metadata meta.json
   ```

   This builds `<target_file>.envelope.json` (the canonical JSON that gets
   timestamped), sends its SHA-512 hash to FreeTSA via `openssl ts -query`,
   submits it over HTTPS, saves the response as `<target_file>.tsr`, and
   immediately verifies the response against FreeTSA's bundled CA
   certificates (`assets/cacert.pem`, `assets/tsa.crt`). It prints a JSON
   summary including whether verification succeeded.

   Three files are produced alongside the target file — keep all three
   together, they're useless apart:
   - `<file>.envelope.json` — what was actually timestamped (data + provenance)
   - `<file>.tsq` — the timestamp request (needed to re-verify later)
   - `<file>.tsr` — the signed timestamp token from FreeTSA (the actual proof)

4. **Tell the user what happened** — confirm verification succeeded, point
   them to the three files, and mention that the `.tsr` token is the proof;
   anyone with OpenSSL and FreeTSA's CA cert can independently verify it
   without trusting Claude or this conversation.

5. **If the user wants to re-verify later** (a new conversation, or to check
   a `.tsr` someone else sent them), use:

   ```bash
   python scripts/verify_timestamp.py <envelope.json> <file.tsq> <file.tsr>
   ```

   This re-runs `openssl ts -verify` and also prints the decoded timestamp
   (the actual signed time) from the token.

## Notes

- This binds *when* the envelope existed, not that its contents are true —
  it doesn't make a false `source_of_data` claim true, it just proves that
  exact (possibly false) claim was made by that exact time. Fill in the
  provenance fields honestly.
- FreeTSA only ever receives a SHA-512 hash, never the actual file content —
  safe to use even on sensitive output, since nothing is uploaded to FreeTSA
  except the digest.
- FreeTSA is a free community service with no documented SLA — fine for the
  use cases above, but don't treat it as a substitute for a paid/contractual
  TSA if the user needs one with legal guarantees.
- Requires `openssl` and `curl` on PATH (already present in Git Bash on this
  machine).
