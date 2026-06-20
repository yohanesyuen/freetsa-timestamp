# FreeTSA Timestamp Skill

A skill for [Claude Code](https://claude.com/claude-code) that proves *when*
a file existed — using a free, independent, internet-wide notary service
called [FreeTSA](https://freetsa.org). Think of it as getting a postmark
from a third party nobody in the conversation controls.

## What problem does this solve?

Say Claude writes you a report, a contract draft, or some data pulled from
an API. The file on your disk says it was "modified" at some time — but
that's just a note your own computer wrote about itself. Anyone (including
you) could change it after the fact and nobody would know.

A **trusted timestamp** fixes that. It's a digital "notary stamp" signed by
an independent server, proving that an exact piece of data existed by an
exact moment in time, and that it hasn't been touched since. If anything in
the file changes later — even one character — the stamp no longer matches,
and that mismatch is provable by anyone, not just you.

This is useful for things like:
- Proving you had an idea or a draft by a certain date (e.g. for IP records)
- Keeping an honest audit trail of AI-generated reports or analysis
- Showing a regulator or auditor "this is exactly the file as it was on this date"

## How it works, in plain terms

1. Claude writes a short note alongside your file explaining where the data
   came from (which tool fetched it, what was asked for, when).
2. Claude calculates a fingerprint (a "hash") of your file plus that note.
   A fingerprint is a short code that's unique to that exact content — change
   one letter and the fingerprint completely changes.
3. That fingerprint (never your actual file or its content) gets sent to
   [FreeTSA](https://freetsa.org), a free, independent timestamping service.
4. FreeTSA signs the fingerprint with the current time and sends back a
   small certificate-like file. That's your proof.
5. Anyone — not just Claude, not just you — can later check that certificate
   against the fingerprint and confirm "yes, this exact content existed by
   this exact time," using freely available tools.

FreeTSA never sees your actual file contents, only the fingerprint, so this
is safe to use even on sensitive material.

## Installing it

This is a **skill** — an instruction pack Claude Code reads to know how to
do a specific job. Installing it just means putting this folder where
Claude Code looks for skills.

**Using Claude Code (CLI)?** Open it and paste this single prompt:

```
Install the Claude Code skill from https://github.com/yohanesyuen/freetsa-timestamp
by cloning it into ~/.claude/skills/freetsa-timestamp (replacing the folder if it
already exists), then confirm it now appears in the available skills list.
```

Claude Code will clone the repo into the right place automatically. No
manual file copying needed.

**Using Claude on the web (claude.ai)?** Skills there work a little
differently — you upload the packaged skill file instead of pointing Claude
at a repo:

1. Make sure code execution is turned on: **Settings → Capabilities**, enable
   it if it isn't already (required for skills to run on Free/Pro/Max plans).
2. Go to **Settings → Capabilities → Skills** (sometimes shown as
   **Customize → Skills**).
3. Click **+ Create skill**, then choose **Upload a skill**.
4. Download [`freetsa-timestamp.skill`](freetsa-timestamp.skill) from this
   repo to your computer first, then select that file in the upload dialog.
5. Once it appears in your skills list, just ask Claude to "timestamp this
   file" in a new chat — same as below.

This also works the same way in **Cowork**.

## Using it

Once installed, just ask naturally — you don't need to remember any
commands:

> "Can you timestamp that CSV you just made, so I have proof of when it was generated?"

> "Notarize this report for our compliance records."

Claude will fill in the provenance details itself (what produced the file,
when, from where), run the timestamping, and hand you back three small
files alongside your original — together they're your proof. Keep all
three; the proof only works with all of them present.

## What's inside this repo

- `SKILL.md` — the instructions Claude Code follows
- `scripts/timestamp_file.py` — builds the fingerprint and gets it stamped by FreeTSA
- `scripts/verify_timestamp.py` — re-checks a stamp later, independent of the original run
- `assets/` — FreeTSA's public certificates, needed to check a stamp is genuine
- `freetsa-timestamp.skill` — the same skill, packaged for one-click install on claude.ai/Cowork

## Trust and limits

- FreeTSA is a free community service. It's a real, working notary — but if
  you need a timestamp with a paid SLA or contractual legal guarantee, use a
  commercial timestamping authority instead.
- A timestamp proves *when* something existed, not that its contents are
  true. If the provenance note is inaccurate, the stamp just proves that
  exact (possibly inaccurate) note existed by that time — garbage in, garbage out.
- Requires `openssl` and `curl` to be available on your machine (both come
  bundled with Git for Windows / Git Bash, and are standard on macOS/Linux).

## License

MIT
