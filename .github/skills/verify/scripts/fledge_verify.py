#!/usr/bin/env python3
"""Drive a disposable Fledge container built from this checkout and record evidence.

Every instance is a container labelled with its run id, on its own host port and data
volume, so several runs can coexist and cleanup removes only what this script started.
Evidence for run <run> lands in <repo>/.verify-evidence/<run>/ and survives cleanup.

    python .github/skills/verify/scripts/fledge_verify.py build
    python .github/skills/verify/scripts/fledge_verify.py launch [--run NAME] [--port N]
    python .github/skills/verify/scripts/fledge_verify.py doctor
    python .github/skills/verify/scripts/fledge_verify.py api GET /fledge/ping --label ping
    python .github/skills/verify/scripts/fledge_verify.py sql "SELECT code FROM log ORDER BY id DESC LIMIT 5"
    python .github/skills/verify/scripts/fledge_verify.py exec -- ls /usr/local/fledge/data/backup
    python .github/skills/verify/scripts/fledge_verify.py cleanup
    python .github/skills/verify/scripts/fledge_verify.py list

Commands after launch default to the latest run (.verify-evidence/LATEST); pass --run to pick another.
Stdlib only: runs on the host with python3 (Linux/macOS) or python (Windows).
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parents[4]
EVIDENCE_ROOT = REPO / ".verify-evidence"
COMPOSE_FILE = REPO / ".ci" / "local" / "docker-compose.yml"
IMAGE = "fledge-local:dev"
LABEL_RUN = "fledge.verify.run"
LABEL_REPO = "fledge.verify.repo"
FLEDGE_DATA = "/usr/local/fledge/data"
DB_PATH = FLEDGE_DATA + "/fledge.db"
DEFAULT_USER = ("admin", "fledge")
BUILD_EXCLUDES = [":(exclude).github", ":(exclude).verify-evidence"]
NET_ERRORS = (urllib.error.URLError, ConnectionError, socket.timeout, OSError)


def die(msg, code=1):
    print("ERROR: " + msg, file=sys.stderr)
    sys.exit(code)


def run(cmd, check=True):
    res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    if check and res.returncode != 0:
        die("command failed ({}): {}\n{}".format(res.returncode, " ".join(cmd), (res.stderr or "").strip()))
    return res


def now_iso():
    return dt.datetime.now().isoformat(timespec="seconds")


def source_fingerprint():
    """HEAD plus a hash of tracked changes and untracked files, ignoring paths the image build skips."""
    head = run(["git", "-C", str(REPO), "rev-parse", "HEAD"]).stdout.strip()
    diff = run(["git", "-C", str(REPO), "diff", "HEAD", "--binary", "--", "."] + BUILD_EXCLUDES).stdout
    untracked = run(["git", "-C", str(REPO), "ls-files", "--others", "--exclude-standard", "--", "."]
                    + BUILD_EXCLUDES).stdout.splitlines()
    h = hashlib.sha256(diff.encode("utf-8", "replace"))
    for rel in sorted(untracked):
        p = REPO / rel
        h.update(rel.encode())
        if p.is_file():
            h.update(p.read_bytes())
    return {"head": head, "worktree_sha256": h.hexdigest(), "dirty": bool(diff or untracked)}


def image_id(ref=IMAGE):
    res = run(["docker", "image", "inspect", "--format", "{{.Id}}", ref], check=False)
    return res.stdout.strip() if res.returncode == 0 else None


def free_port():
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]


def run_dir(name):
    return EVIDENCE_ROOT / name


def resolve_run(name):
    if name:
        return name
    latest = EVIDENCE_ROOT / "LATEST"
    if not latest.exists():
        die("no --run given and no .verify-evidence/LATEST; launch one first")
    return latest.read_text().strip()


def load_instance(name):
    p = run_dir(name) / "instance.json"
    if not p.exists():
        die("run '{}' has no instance.json under {}".format(name, run_dir(name)))
    return json.loads(p.read_text())


def save_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")


def next_evidence_path(name, label):
    d = run_dir(name)
    d.mkdir(parents=True, exist_ok=True)
    nums = [int(m.group(1)) for p in d.iterdir() for m in [re.match(r"^(\d{3})-", p.name)] if m]
    slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", label).strip("-") or "step"
    return d / "{:03d}-{}.json".format((max(nums) + 1) if nums else 1, slug)


def http(port, method, path, body=None, token=None, timeout=30):
    url = "http://127.0.0.1:{}{}".format(port, path)
    data = None
    headers = {}
    if body is not None:
        data = body.encode("utf-8") if isinstance(body, str) else json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    if token:
        headers["authorization"] = token
    req = urllib.request.Request(url, data=data, method=method.upper(), headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            status, reason, raw = resp.status, resp.reason, resp.read()
    except urllib.error.HTTPError as e:
        status, reason, raw = e.code, e.reason, e.read()
    text = raw.decode("utf-8", "replace")
    try:
        parsed = json.loads(text) if text else None
    except ValueError:
        parsed = text
    return status, reason, parsed


def login(name, port, user, password):
    status, reason, body = http(port, "POST", "/fledge/login", {"username": user, "password": password})
    if status != 200 or not isinstance(body, dict) or "token" not in body:
        return None, status, reason, body
    tokens_path = run_dir(name) / "tokens.json"
    tokens = json.loads(tokens_path.read_text()) if tokens_path.exists() else {}
    tokens[user] = {"token": body["token"], "pw": pw_tag(password)}
    save_json(tokens_path, tokens)
    return body["token"], status, reason, body


def pw_tag(password):
    return hashlib.sha256(password.encode("utf-8")).hexdigest()[:12]


def cached_token(name, user, password):
    """A cached token only stands in for the same user AND password, so a wrong password never rides on it."""
    p = run_dir(name) / "tokens.json"
    entry = json.loads(p.read_text()).get(user) if p.exists() else None
    return entry["token"] if isinstance(entry, dict) and entry.get("pw") == pw_tag(password) else None


def parse_as(value):
    if value == "none":
        return None
    if value == "admin":
        return DEFAULT_USER
    if ":" not in value:
        die("--as takes admin, none, or user:password")
    user, password = value.split(":", 1)
    return user, password


def container_state(cname):
    res = run(["docker", "inspect", "--format", "{{json .State}}", cname], check=False)
    return json.loads(res.stdout) if res.returncode == 0 else None


def container_labels(cname):
    res = run(["docker", "inspect", "--format", "{{json .Config.Labels}}", cname], check=False)
    return (json.loads(res.stdout) or {}) if res.returncode == 0 else None


# ---------------------------------------------------------------- commands

def cmd_build(args):
    print("building {} from {} (first build: 15-40 min)".format(IMAGE, REPO), flush=True)
    fp = source_fingerprint()
    res = subprocess.run(["docker", "compose", "-f", str(COMPOSE_FILE), "build", "fledge"])
    if res.returncode != 0:
        die("image build failed")
    info = {"image": IMAGE, "image_id": image_id(), "built_at": now_iso(), "source": fp}
    save_json(EVIDENCE_ROOT / "build.json", info)
    print(json.dumps(info, indent=2))


def wait_ready(name, port, cname, timeout):
    deadline = time.time() + timeout
    stage, last, token = "ping", "", None
    while time.time() < deadline:
        state = container_state(cname)
        if not state or not state.get("Running"):
            logs = run(["docker", "logs", "--tail", "80", cname], check=False)
            die("container stopped during startup (state={}):\n{}{}".format(
                state and state.get("Status"), logs.stdout, logs.stderr))
        try:
            if stage == "ping":
                status = http(port, "GET", "/fledge/ping", timeout=5)[0]
                last = "ping HTTP {}".format(status)
                if status == 200:
                    stage = "login"
            if stage == "login":
                token, status, _, body = login(name, port, *DEFAULT_USER)
                last = "login HTTP {} {}".format(status, body)
                if token:
                    stage = "services"
            if stage == "services":
                status, _, body = http(port, "GET", "/fledge/service", token=token, timeout=10)
                svcs = {s["type"]: s["status"] for s in (body or {}).get("services", [])} if status == 200 else {}
                last = "services HTTP {} {}".format(status, svcs)
                if svcs.get("Core") == "running" and svcs.get("Storage") == "running":
                    stage = "seed"
            if stage == "seed":
                status, _, body = http(port, "GET", "/fledge/schedule", token=token, timeout=10)
                names = [s["name"] for s in (body or {}).get("schedules", [])] if status == 200 else []
                last = "schedules HTTP {} {}".format(status, names)
                if "purge" in names and "backup on demand" in names:
                    return None
        except NET_ERRORS as e:
            last = "{}: {}".format(stage, e)
        time.sleep(2)
    return last


def cmd_launch(args):
    img = image_id()
    if not img:
        die("image {} not found; run the build command first".format(IMAGE))
    name = args.run or "run-" + dt.datetime.now().strftime("%Y%m%d-%H%M%S")
    d = run_dir(name)
    if (d / "instance.json").exists() and not load_instance(name).get("cleaned_at"):
        die("run '{}' already has a live instance; pick another --run or clean it up".format(name))
    port = args.port or free_port()
    cname = "fledge-verify-" + name
    volume = cname + "-data"
    if container_state(cname):
        die("container {} already exists and is not tracked by this run; not reusing it".format(cname))
    run(["docker", "run", "-d", "--name", cname,
         "--label", "{}={}".format(LABEL_RUN, name), "--label", "{}={}".format(LABEL_REPO, str(REPO)),
         "-p", "127.0.0.1:{}:8081".format(port), "-v", "{}:{}".format(volume, FLEDGE_DATA), IMAGE])
    inst = {"run": name, "container": cname, "volume": volume, "port": port, "image": IMAGE,
            "image_id": img, "launched_at": now_iso(), "evidence_dir": str(d)}
    save_json(d / "instance.json", inst)
    (EVIDENCE_ROOT / "LATEST").write_text(name + "\n")
    print("launched {} on http://127.0.0.1:{} (run {}); waiting for ready".format(cname, port, name), flush=True)

    start = time.time()
    last = wait_ready(name, port, cname, args.timeout)
    if last is not None:
        die("not ready after {}s; last check: {}\nrun doctor, then cleanup".format(args.timeout, last))
    inst["ready_after_s"] = round(time.time() - start, 1)
    save_json(d / "instance.json", inst)
    ping = http(port, "GET", "/fledge/ping")[2]
    save_json(d / "000-ready.json", {"ts": now_iso(), "ready_after_s": inst["ready_after_s"], "ping": ping})
    print("READY after {}s: http://127.0.0.1:{}  version={}  evidence={}".format(
        inst["ready_after_s"], port, (ping or {}).get("version"), d))


def cmd_doctor(args):
    name = resolve_run(args.run)
    inst = load_instance(name)
    ok = True

    def check(label, passed, detail=""):
        nonlocal ok
        ok = ok and passed
        print("[{}] {}{}".format("ok" if passed else "FAIL", label, (": " + detail) if detail else ""))

    if inst.get("cleaned_at"):
        check("instance live", False, "run was cleaned up at " + inst["cleaned_at"])
        sys.exit(1)
    check("docker daemon", run(["docker", "info", "--format", "{{.ServerVersion}}"], check=False).returncode == 0)
    state = container_state(inst["container"])
    check("container running", bool(state and state.get("Running")), state.get("Status") if state else "missing")
    lbl = container_labels(inst["container"]) or {}
    check("container is ours", lbl.get(LABEL_RUN) == name, "label {}={}".format(LABEL_RUN, lbl.get(LABEL_RUN)))
    port_map = run(["docker", "port", inst["container"], "8081/tcp"], check=False).stdout.strip()
    check("port mapping", port_map.endswith(":{}".format(inst["port"])), port_map or "none")
    current = image_id()
    check("container runs the latest built image", current == inst["image_id"],
          "container {} vs {} {}".format(inst["image_id"][7:19], IMAGE, (current or "missing")[7:19]))
    build = EVIDENCE_ROOT / "build.json"
    if build.exists():
        built = json.loads(build.read_text())
        fp = source_fingerprint()
        same = built.get("image_id") == current and built["source"]["head"] == fp["head"] \
            and built["source"]["worktree_sha256"] == fp["worktree_sha256"]
        check("image built from current source", same,
              "" if same else "source changed since build at {}; rebuild and relaunch".format(built["built_at"]))
    else:
        check("image built from current source", False, "no .verify-evidence/build.json; run the build command")
    repo_version = " ".join((REPO / "VERSION").read_text().split())
    cver = run(["docker", "exec", inst["container"], "cat", "/usr/local/fledge/VERSION"], check=False).stdout
    cver = " ".join(cver.split())
    check("VERSION matches checkout", cver == repo_version, "container [{}] repo [{}]".format(cver, repo_version))
    try:
        status, _, ping = http(inst["port"], "GET", "/fledge/ping", timeout=5)
        check("ping", status == 200, "health={} uptime={} safeMode={}".format(
            ping.get("health"), ping.get("uptime"), ping.get("safeMode")) if status == 200 else str(status))
        token = cached_token(name, *DEFAULT_USER)
        if not token or http(inst["port"], "GET", "/fledge/user", token=token)[0] == 401:
            token = login(name, inst["port"], *DEFAULT_USER)[0]
        check("admin login", bool(token))
        status, _, body = http(inst["port"], "GET", "/fledge/service", token=token)
        svcs = {s["type"]: s["status"] for s in (body or {}).get("services", [])} if status == 200 else {}
        check("core and storage running", svcs.get("Core") == "running" and svcs.get("Storage") == "running",
              json.dumps(svcs))
    except NET_ERRORS as e:
        check("api reachable", False, str(e))
    print("doctor: {} (run {}, http://127.0.0.1:{})".format("healthy" if ok else "NOT healthy", name, inst["port"]))
    sys.exit(0 if ok else 1)


def cmd_api(args):
    name = resolve_run(args.run)
    inst = load_instance(name)
    creds = parse_as(args.as_user)
    token = None
    if creds:
        token = cached_token(name, *creds)
        if not token and args.no_relogin:
            die("--no-relogin needs a cached token for {}; log in with an earlier call".format(creds[0]))
        token = token or login(name, inst["port"], *creds)[0]
        if not token:
            die("login failed for user {}".format(creds[0]))
    body = args.data
    if body is not None and body.startswith("@"):
        body = Path(body[1:]).read_text(encoding="utf-8")
    if body is not None:
        try:
            body = json.loads(body)
        except ValueError:
            pass
    status, reason, resp = http(inst["port"], args.method, args.path, body, token, timeout=args.timeout)
    if status == 401 and creds and not args.no_relogin:
        token = login(name, inst["port"], *creds)[0]
        status, reason, resp = http(inst["port"], args.method, args.path, body, token, timeout=args.timeout)
    out = next_evidence_path(name, args.label or "{}-{}".format(args.method.lower(), args.path))
    save_json(out, {"ts": now_iso(), "request": {"method": args.method.upper(), "path": args.path,
                    "as": creds[0] if creds else None, "body": body},
                    "response": {"status": status, "reason": reason, "body": resp}})
    print("HTTP {} {}".format(status, reason))
    print(json.dumps(resp, indent=2) if not isinstance(resp, str) else resp)
    print("evidence: " + str(out))
    if args.expect is not None and status != args.expect:
        die("expected HTTP {}, got {}".format(args.expect, status))


def cmd_sql(args):
    name = resolve_run(args.run)
    inst = load_instance(name)
    res = run(["docker", "exec", inst["container"], "sqlite3", "-readonly", "-json", args.db, args.query], check=False)
    rows = (json.loads(res.stdout) if res.stdout.strip() else []) if res.returncode == 0 else None
    out = next_evidence_path(name, args.label or "sql")
    save_json(out, {"ts": now_iso(), "db": args.db, "query": args.query, "rows": rows,
                    "stderr": res.stderr.strip() or None})
    if res.returncode != 0:
        die("sqlite3 failed: {}".format(res.stderr.strip()))
    print(json.dumps(rows, indent=2))
    print("evidence: " + str(out))


def cmd_exec(args):
    name = resolve_run(args.run)
    inst = load_instance(name)
    cmd = args.cmd[1:] if args.cmd and args.cmd[0] == "--" else args.cmd
    if not cmd:
        die("exec needs a command after --")
    res = run(["docker", "exec", inst["container"]] + cmd, check=False)
    out = next_evidence_path(name, args.label or "exec")
    save_json(out, {"ts": now_iso(), "cmd": cmd, "exit": res.returncode, "stdout": res.stdout, "stderr": res.stderr})
    sys.stdout.write(res.stdout)
    sys.stderr.write(res.stderr)
    print("evidence: " + str(out))
    sys.exit(res.returncode)


def cleanup_one(name):
    d = run_dir(name)
    p = d / "instance.json"
    inst = json.loads(p.read_text()) if p.exists() else {
        "run": name, "container": "fledge-verify-" + name, "volume": "fledge-verify-" + name + "-data"}
    lbl = container_labels(inst["container"])
    if lbl is not None:
        if lbl.get(LABEL_RUN) != name:
            die("container {} lacks label {}={}; not removing what this script did not start".format(
                inst["container"], LABEL_RUN, name))
        logs = run(["docker", "logs", inst["container"]], check=False)
        d.mkdir(parents=True, exist_ok=True)
        (d / "container.log").write_text(logs.stdout + logs.stderr, encoding="utf-8")
        run(["docker", "rm", "-f", inst["container"]], check=False)
        print("removed container {} (logs saved to {})".format(inst["container"], d / "container.log"))
    else:
        print("container {} already gone".format(inst["container"]))
    if run(["docker", "volume", "inspect", inst["volume"]], check=False).returncode == 0:
        run(["docker", "volume", "rm", inst["volume"]], check=False)
        print("removed volume {}".format(inst["volume"]))
    inst["cleaned_at"] = now_iso()
    save_json(p, inst)
    print("evidence kept in {}".format(d))


def cmd_cleanup(args):
    if not args.all:
        cleanup_one(resolve_run(args.run))
        return
    res = run(["docker", "ps", "-a", "--filter", "label={}={}".format(LABEL_REPO, str(REPO)),
               "--format", "{{.Label \"" + LABEL_RUN + "\"}}"])
    names = sorted(set(n for n in res.stdout.split() if n))
    if not names:
        print("no verify containers from this checkout")
    for n in names:
        cleanup_one(n)


def cmd_list(args):
    res = run(["docker", "ps", "-a", "--filter", "label={}".format(LABEL_RUN),
               "--format", "{{.Names}}\t{{.Status}}\t{{.Ports}}\t{{.Label \"" + LABEL_REPO + "\"}}"])
    print(res.stdout.strip() or "no verify containers")


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = ap.add_subparsers(dest="command", required=True)
    sub.add_parser("build", help="build fledge-local:dev from this checkout").set_defaults(fn=cmd_build)

    p = sub.add_parser("launch", help="start a fresh instance and wait until usable")
    p.add_argument("--run", help="run id (default run-<timestamp>)")
    p.add_argument("--port", type=int, help="host port (default: a free one)")
    p.add_argument("--timeout", type=int, default=300)
    p.set_defaults(fn=cmd_launch)

    p = sub.add_parser("doctor", help="is this instance worth driving?")
    p.add_argument("--run")
    p.set_defaults(fn=cmd_doctor)

    p = sub.add_parser("api", help="call the REST API and record request and response")
    p.add_argument("method")
    p.add_argument("path", help="e.g. /fledge/category")
    p.add_argument("--data", help="JSON body, or @file")
    p.add_argument("--as", dest="as_user", default="admin", help="admin (default), none, or user:password")
    p.add_argument("--label", help="evidence file label")
    p.add_argument("--expect", type=int, help="exit 1 unless this HTTP status comes back")
    p.add_argument("--no-relogin", action="store_true",
                   help="send the cached token as-is and record a 401 instead of logging in again")
    p.add_argument("--timeout", type=int, default=60)
    p.add_argument("--run")
    p.set_defaults(fn=cmd_api)

    p = sub.add_parser("sql", help="read-only sqlite query inside the container")
    p.add_argument("query")
    p.add_argument("--db", default=DB_PATH)
    p.add_argument("--label")
    p.add_argument("--run")
    p.set_defaults(fn=cmd_sql)

    p = sub.add_parser("exec", help="run a command in the container and record its output")
    p.add_argument("--label")
    p.add_argument("--run")
    p.add_argument("cmd", nargs=argparse.REMAINDER)
    p.set_defaults(fn=cmd_exec)

    p = sub.add_parser("cleanup", help="remove the run's container and volume, keep evidence")
    p.add_argument("--run")
    p.add_argument("--all", action="store_true", help="every verify container started from this checkout")
    p.set_defaults(fn=cmd_cleanup)

    sub.add_parser("list", help="list verify containers on this Docker host").set_defaults(fn=cmd_list)

    args = ap.parse_args()
    args.fn(args)


if __name__ == "__main__":
    main()
