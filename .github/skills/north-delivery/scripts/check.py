#!/usr/bin/env python3
"""Model-check the north service's delivery position with TLC.

Runs every config in ../model (or the ones named) and compares each result
with EXPECTED. Exit 0 only when every result matches.

    python .github/skills/north-delivery/scripts/check.py
    python .github/skills/north-delivery/scripts/check.py today --trace
    python .github/skills/north-delivery/scripts/check.py --print-jar

Java: $JAVA, else `java` on PATH, else Docker ($TLC_DOCKER_IMAGE,
default eclipse-temurin:21-jre-alpine). TLC: $TLA2TOOLS, else the pinned
tla2tools.jar downloaded once into a user cache and checked by sha256.
"""
import argparse
import hashlib
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.request
from pathlib import Path

MODEL_DIR = Path(__file__).resolve().parent.parent / "model"
SPEC = "NorthDelivery"

TLC_VERSION = "1.7.4"
TLC_URL = f"https://github.com/tlaplus/tlaplus/releases/download/v{TLC_VERSION}/tla2tools.jar"
TLC_SHA256 = "936a262061c914694dfd669a543be24573c45d5aa0ff20a8b96b23d01e050e88"
DOCKER_IMAGE = os.environ.get("TLC_DOCKER_IMAGE", "eclipse-temurin:21-jre-alpine")

# config -> expected outcome: "ok" or the name of the invariant TLC must report.
EXPECTED = {
    "today": "PositionNeverPassesUnsent",
    "partial-send": "PositionNeverPassesUnsent",
    "filter-end": "PositionNeverPassesUnsent",
    "sender-filtered": "PositionNeverPassesUnsent",
    "fixed": "ok",
    "witness-send": "CannotDeliverAll",
    "witness-filter": "CannotFilterAll",
}

SITES = {
    "Initial": "start: DataLoad constructor, streams.last_object = 0",
    "LoadWaitForRequest": "load  DataLoad::waitForReadRequest returns",
    "LoadReadBlock": "load  loadThread loop -> DataLoad::readBlock readingFetch",
    "LoadIdleFlush": "load  readBlock, no new readings -> flushLastSentId",
    "LoadIdleExit": "load  readBlock exits on shutdown",
    "LoadFilter": "load  bufferReadings filter pipeline -> DataLoad::pipelineEnd",
    "LoadFlush": "load  updateLastSentId -> flushLastSentId",
    "LoadPush": "load  pipelineEnd m_queue.push_back",
    "SendTop": "send  sendThread loop",
    "SendFetch": "send  DataLoad::fetchReadings",
    "SendWake": "send  m_fetchCV wakes",
    "SendPlugin": "send  DataSender::send -> plugin_send",
    "SendFiltered": "send  sendThread \"All readings filtered out\"",
    "SendDispatchShutdown": "send  shutdown seen, readings = NULL",
    "SendUpdate": "send  DataLoad::updateLastSentId",
    "SendFlush": "send  updateLastSentId -> flushLastSentId",
    "Stop": "main  DataLoad::shutdown",
    "StopSender": "main  ~DataSender sets m_shutdown",
    "JoinSender": "main  ~DataSender joins the send thread",
    "JoinLoad": "main  ~DataLoad joins, flushes if m_flushRequired, drops queue",
    "Stopped": "main  stopped",
}

# Variables shown in traces, in this order; the rest are thread-local detail.
SHOWN = ["stored", "streamSent", "nextUpdate", "lastFetched", "queue", "held",
         "pending", "delivered", "filtered", "loadShutdown", "sendShutdown"]


def cache_dir() -> Path:
    # Not %LOCALAPPDATA%: Microsoft Store Python redirects writes there into its
    # package sandbox, where Docker and other processes cannot see them.
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base) / "fledge-north-delivery"


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def tla2tools() -> Path:
    if os.environ.get("TLA2TOOLS"):
        jar = Path(os.environ["TLA2TOOLS"])
        if not jar.is_file():
            sys.exit(f"TLA2TOOLS={jar} does not exist")
        return jar
    jar = cache_dir() / f"tla2tools-{TLC_VERSION}.jar"
    if jar.is_file() and sha256(jar) == TLC_SHA256:
        return jar
    jar.parent.mkdir(parents=True, exist_ok=True)
    print(f"downloading {TLC_URL}", file=sys.stderr)
    tmp = jar.with_suffix(".part")
    urllib.request.urlretrieve(TLC_URL, tmp)
    got = sha256(tmp)
    if got != TLC_SHA256:
        tmp.unlink()
        sys.exit(f"tla2tools.jar sha256 {got} != pinned {TLC_SHA256}")
    tmp.replace(jar)
    return jar


def java_command(jar: Path, workdir: Path) -> list:
    tlc = ["-XX:+UseParallelGC", "-cp"]
    java = os.environ.get("JAVA") or shutil.which("java")
    if java:
        return [java, *tlc, str(jar), "tlc2.TLC"]
    if not shutil.which("docker"):
        sys.exit("no Java: set JAVA, put java on PATH, or install Docker")
    return ["docker", "run", "--rm",
            "-v", f"{workdir}:/work", "-v", f"{jar.parent}:/tla:ro", "-w", "/work",
            DOCKER_IMAGE, "java", *tlc, f"/tla/{jar.name}", "tlc2.TLC"]


def outcome(out: str) -> str:
    if "No error has been found" in out:
        return "ok"
    m = re.search(r"Invariant (\w+) is violated", out)
    if m:
        return m.group(1)
    if "Deadlock reached" in out:
        return "deadlock"
    return "error"


def states(out: str) -> str:
    m = re.search(r"([\d,]+) distinct states found", out)
    return m.group(1) if m else "?"


def parse_trace(out: str) -> list:
    steps = []
    for block in re.split(r"\n(?=State \d+: )", out):
        head = re.match(r"State \d+: <(\w+)", block)
        if not head:
            continue
        action = head.group(1)
        values, name = {}, None
        for line in block.splitlines()[1:]:
            m = re.match(r"/\\ (\w+) = (.*)", line)
            if m:
                name = m.group(1)
                values[name] = m.group(2).strip()
            elif name and line.strip():
                values[name] += " " + line.strip()
        values = {k: v.replace("[ids |-> <<>>, src |-> 0]", "NULL") for k, v in values.items()}
        steps.append((action, values))
    return steps


def print_trace(out: str) -> None:
    prev = {}
    for i, (action, values) in enumerate(parse_trace(out), 1):
        changed = [f"{k}={values[k]}" for k in SHOWN if k in values and values[k] != prev.get(k)]
        print(f"    {i:2}. {SITES.get(action, action)}")
        if changed:
            print("        " + "  ".join(changed))
        prev = values


def run(config: str, jar: Path, trace: bool) -> bool:
    runs = cache_dir() / "runs"
    runs.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix=f"{config}-", dir=runs) as tmp:
        work = Path(tmp)
        shutil.copy(MODEL_DIR / f"{SPEC}.tla", work)
        shutil.copy(MODEL_DIR / f"{config}.cfg", work)
        cmd = java_command(jar, work) + [
            "-config", f"{config}.cfg", "-workers", "1", "-metadir", "states", f"{SPEC}.tla"]
        start = time.monotonic()
        proc = subprocess.run(cmd, cwd=work, capture_output=True, text=True)
        took = time.monotonic() - start
    out = proc.stdout + proc.stderr
    got, want = outcome(out), EXPECTED[config]
    match = got == want
    print(f"{'PASS' if match else 'FAIL'}  {config:16} expected {want:26} got {got:26} "
          f"{states(out):>9} states  {took:5.1f}s")
    if got == "error" or (not match and got == "ok"):
        print("    " + "\n    ".join(out.strip().splitlines()[-25:]))
    elif trace or not match:
        print_trace(out)
    return match


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("configs", nargs="*", metavar="config",
                        help=f"configs to run (default all): {', '.join(EXPECTED)}")
    parser.add_argument("--trace", action="store_true", help="print each counterexample in code terms")
    parser.add_argument("--print-jar", action="store_true", help="print the tla2tools.jar path and exit")
    args = parser.parse_args()
    unknown = [c for c in args.configs if c not in EXPECTED]
    if unknown:
        parser.error(f"unknown config {', '.join(unknown)}; choose from {', '.join(EXPECTED)}")
    jar = tla2tools()
    if args.print_jar:
        print(jar)
        return 0
    results = [run(c, jar, args.trace) for c in (args.configs or EXPECTED)]
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
