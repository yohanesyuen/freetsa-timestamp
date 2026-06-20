#!/usr/bin/env python3
"""
Re-verify a FreeTSA timestamp token against its envelope, independent of
the original timestamp_file.py run. Useful at audit time, or to check a
timestamp received from someone else.

Usage:
    python verify_timestamp.py <envelope.json> <file.tsq> <file.tsr>
"""
import argparse
import subprocess
import sys
from pathlib import Path

SKILL_DIR = Path(__file__).resolve().parent.parent
CACERT = SKILL_DIR / "assets" / "cacert.pem"
TSACERT = SKILL_DIR / "assets" / "tsa.crt"


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("envelope", type=Path)
    ap.add_argument("tsq", type=Path)
    ap.add_argument("tsr", type=Path)
    args = ap.parse_args()

    for p in (args.envelope, args.tsq, args.tsr, CACERT, TSACERT):
        if not p.exists():
            raise SystemExit(f"missing file: {p}")

    result = subprocess.run([
        "openssl", "ts", "-verify",
        "-in", str(args.tsr),
        "-queryfile", str(args.tsq),
        "-CAfile", str(CACERT),
        "-untrusted", str(TSACERT),
    ], capture_output=True)

    sys.stdout.write(result.stdout.decode(errors="replace"))
    sys.stderr.write(result.stderr.decode(errors="replace"))

    reply = subprocess.run(["openssl", "ts", "-reply", "-in", str(args.tsr), "-text"], capture_output=True)
    sys.stdout.write(reply.stdout.decode(errors="replace"))

    raise SystemExit(0 if result.returncode == 0 else 1)


if __name__ == "__main__":
    main()
