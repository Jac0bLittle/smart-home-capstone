#!/usr/bin/env python3
"""Check the broker's logins and topic rules (sheet section 2).

For every node login it checks that:
  * the right password connects and a wrong one is refused,
  * the node can publish in its own branch (home/<sub>/...),
  * the node can NOT publish into another subsystem's branch,
  * the node can NOT read another subsystem's branch,
and that anonymous clients are refused. The tester login watches as referee.

Passwords: env PASS_<USER> (e.g. PASS_CLIMATE) or asked for each one.
  python3 acl_test.py --host 192.168.0.10
"""
import getpass
import os
import time

from tb import SUBS, base_args, client, connect

results = []


def check(name, ok):
    results.append((name, ok))
    print(f"  {'PASS' if ok else 'FAIL'}  {name}")


def try_connect(a, user, pw):
    c = client(f"acltest-{user}-{int(time.time() * 1000) % 100000}", user, pw)
    got = {}
    c.on_connect = lambda cl, u, f, *r: got.setdefault("rc", int(getattr(r[0], "value", r[0])) if r else 0)
    try:
        c.connect(a.host, a.port, 10)
    except OSError as e:
        return None, f"socket error {e}"
    c.loop_start()
    t = time.time()
    while "rc" not in got and time.time() - t < 4:
        time.sleep(0.02)
    if got.get("rc") != 0:
        c.loop_stop()
        c.disconnect()
        return None, got.get("rc")
    return c, 0


def main():
    p = base_args(__doc__)
    a = p.parse_args()
    ref, ok, rc = connect(a, "acltest-referee")
    if not ok:
        raise SystemExit(f"tester login failed (rc {rc})")
    seen = []
    ref.on_message = lambda cl, u, m: seen.append(m.topic)
    ref.subscribe("home/#", qos=1)
    time.sleep(0.5)

    print("anonymous client")
    c, rc = try_connect(a, None, None)
    check("anonymous connection refused", c is None)

    for sub in SUBS:
        pw = os.environ.get(f"PASS_{sub.upper()}") or getpass.getpass(f"password for {sub}: ")
        print(f"login '{sub}'")
        c, rc = try_connect(a, sub, pw + "x")
        check("wrong password refused", c is None)
        c, rc = try_connect(a, sub, pw)
        check("correct password accepted", c is not None)
        if c is None:
            continue
        other = SUBS[(SUBS.index(sub) + 1) % len(SUBS)]
        own_t = f"home/{sub}/node1/tele/acl_probe"
        bad_t = f"home/{other}/node1/state/acl_probe"
        got = []
        c.on_message = lambda cl, u, m: got.append(m.topic)
        c.subscribe(f"home/{other}/#", qos=1)
        time.sleep(0.3)
        seen.clear()
        c.publish(own_t, "1", qos=1)
        c.publish(bad_t, "1", qos=1)
        ref.publish(f"home/{other}/node1/tele/acl_probe", "1", qos=1)
        time.sleep(0.8)
        check(f"can publish to own branch ({own_t})", own_t in seen)
        check(f"cannot publish to {other}'s branch", bad_t not in seen)
        check(f"cannot read {other}'s branch", not got)
        c.loop_stop()
        c.disconnect()

    failed = [n for n, ok in results if not ok]
    print(f"\n{len(results) - len(failed)}/{len(results)} checks passed")
    fname = f"acl_test_{time.strftime('%Y%m%d_%H%M%S')}.csv"
    with open(fname, "w", newline="") as f:
        f.write("check,result\n")
        for n, ok in results:
            name = n.replace('"', '""')
            f.write(f"\"{name}\",{'PASS' if ok else 'FAIL'}\n")
    print(f"saved {fname}")
    raise SystemExit(1 if failed else 0)


if __name__ == "__main__":
    main()
