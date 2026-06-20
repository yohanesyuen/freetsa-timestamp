#!/usr/bin/env python3
"""
Build a provenance envelope for a Claude-generated file and get it
timestamped by FreeTSA (RFC 3161). See ../SKILL.md for the full workflow.

Usage:
    python timestamp_file.py <target_file> --metadata <metadata.json> [--outdir DIR]

metadata.json must contain (caller/Claude fills these in from its own
conversation context -- see SKILL.md):
    req_param       - the parameters used to retrieve/produce the data
    source_of_data  - where the data came from / how it was generated
    tool_calls      - list of {tool, input} describing what was called
    retrieved_at    - ISO 8601 timestamp of when the tool response was retrieved
                      (optional: if omitted, caller must supply it themselves --
                      this script does not invent timestamps)
"""
import argparse
import base64
import hashlib
import json
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CACERT = SKILL_DIR / "assets" / "cacert.pem"
TSACERT = SKILL_DIR / "assets" / "tsa.crt"
TSA_URL = "https://freetsa.org/tsr"

REQUIRED_METADATA_FIELDS = ["req_param", "source_of_data", "tool_calls", "retrieved_at"]


def is_probably_text(raw: bytes) -> bool:
    try:
        raw.decode("utf-8")
        return b"\x00" not in raw
    except UnicodeDecodeError:
        return False


def build_envelope(target: Path, metadata: dict) -> dict:
    raw = target.read_bytes()
    if is_probably_text(raw):
        data_field = raw.decode("utf-8")
        encoding = "utf-8"
    else:
        data_field = base64.b64encode(raw).decode("ascii")
        encoding = "base64"

    envelope = {
        "filename": target.name,
        "encoding": encoding,
        "data": data_field,
        "req_param": metadata["req_param"],
        "retrieved_at": metadata["retrieved_at"],
        "source_of_data": metadata["source_of_data"],
        "tool_calls": metadata["tool_calls"],
    }
    return envelope


def canonical_json_bytes(obj: dict) -> bytes:
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def run(cmd, **kwargs):
    result = subprocess.run(cmd, capture_output=True, **kwargs)
    if result.returncode != 0:
        sys.stderr.write(result.stderr.decode(errors="replace"))
        raise SystemExit(f"command failed: {' '.join(cmd)}")
    return result


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("target_file", type=Path, help="File Claude generated that should be timestamped")
    ap.add_argument("--metadata", type=Path, required=True, help="JSON file with req_param/source_of_data/tool_calls/retrieved_at")
    ap.add_argument("--outdir", type=Path, default=None, help="Where to write envelope/tsq/tsr (default: alongside target file)")
    args = ap.parse_args()

    if not args.target_file.exists():
        raise SystemExit(f"target file not found: {args.target_file}")
    metadata = json.loads(args.metadata.read_text(encoding="utf-8"))
    missing = [f for f in REQUIRED_METADATA_FIELDS if f not in metadata]
    if missing:
        raise SystemExit(f"metadata.json is missing required fields: {missing}")

    outdir = args.outdir or args.target_file.parent
    outdir.mkdir(parents=True, exist_ok=True)
    stem = args.target_file.name

    envelope = build_envelope(args.target_file, metadata)
    envelope_path = outdir / f"{stem}.envelope.json"
    envelope_bytes = canonical_json_bytes(envelope)
    envelope_path.write_bytes(envelope_bytes)

    envelope_sha512 = hashlib.sha512(envelope_bytes).hexdigest()

    tsq_path = outdir / f"{stem}.tsq"
    tsr_path = outdir / f"{stem}.tsr"

    run([
        "openssl", "ts", "-query",
        "-data", str(envelope_path),
        "-no_nonce", "-sha512", "-cert",
        "-out", str(tsq_path),
    ])

    curl = run([
        "curl", "-sS",
        "-H", "Content-Type: application/timestamp-query",
        "--data-binary", f"@{tsq_path}",
        "-o", str(tsr_path),
        "-w", "%{http_code}",
        TSA_URL,
    ])
    http_code = curl.stdout.decode().strip()
    if http_code != "200" or not tsr_path.exists() or tsr_path.stat().st_size == 0:
        raise SystemExit(f"FreeTSA request failed (HTTP {http_code}); see {tsr_path} for any partial response")

    verify = subprocess.run([
        "openssl", "ts", "-verify",
        "-in", str(tsr_path),
        "-queryfile", str(tsq_path),
        "-CAfile", str(CACERT),
        "-untrusted", str(TSACERT),
    ], capture_output=True)

    print(json.dumps({
        "envelope_file": str(envelope_path),
        "envelope_sha512": envelope_sha512,
        "tsq_file": str(tsq_path),
        "tsr_file": str(tsr_path),
        "verified": verify.returncode == 0,
        "verify_output": verify.stdout.decode(errors="replace").strip() + verify.stderr.decode(errors="replace").strip(),
    }, indent=2))

    if verify.returncode != 0:
        raise SystemExit("timestamp token received but verification failed -- do not trust it")


if __name__ == "__main__":
    main()
