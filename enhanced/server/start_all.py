"""Start the servers the game needs: http_config.py on 443 (https://APSEODESK172, plus the
admin page on :8088) and messenger.py on :28002.

Streams both outputs prefixed, and on Ctrl-C (or --selftest) terminates both so
nothing is left listening. (It used to also start server.py and a second http_config.py
on 8080; the client uses neither, and the two http_config.py fought over the admin port.)

Usage:
    python start_all.py
    python start_all.py --selftest   # start, verify alive ~3s, stop, exit
"""
import os, queue, subprocess, sys, threading, time

HERE = os.path.dirname(os.path.abspath(__file__))
selftest = "--selftest" in sys.argv

procs = []
CONSOLE_QUEUE = queue.Queue(maxsize=256)


def console(line):
    # Console output is only a mirror. Never stop draining a child's pipe when
    # a terminal is paused or its reader stops consuming output.
    try:
        CONSOLE_QUEUE.put_nowait(line[:16384])
    except queue.Full:
        pass  # the complete child output is retained in captures/*-service.log


def console_worker():
    while True:
        line = CONSOLE_QUEUE.get()
        try:
            sys.stdout.write(line)
            sys.stdout.flush()
        except (OSError, ValueError):
            return  # closed console; pipe pumps and file logging keep running
        finally:
            CONSOLE_QUEUE.task_done()


def pump(name, proc):
    os.makedirs(os.path.join(HERE, "captures"), exist_ok=True)
    path = os.path.join(HERE, "captures", name + "-service.log")
    with open(path, "a", encoding="utf-8", buffering=1) as log:
        for line in proc.stdout:
            log.write(line)
            console(f"[{name}] {line}")


def start(name, extra):
    p = subprocess.Popen([sys.executable, "-u", os.path.join(HERE, name), *extra],
                         cwd=HERE, stdout=subprocess.PIPE, stderr=subprocess.STDOUT,
                         text=True, bufsize=1)
    threading.Thread(target=pump, args=(name, p), daemon=True).start()
    procs.append((name, p))


def shutdown():
    for name, p in procs:
        if p.poll() is None:
            p.terminate()
    for name, p in procs:
        try:
            p.wait(timeout=5)
        except subprocess.TimeoutExpired:
            p.kill()


def main():
    threading.Thread(target=console_worker, name="console-mirror", daemon=True).start()
    start("http_config.py", ["443", "--tls"])  # https://APSEODESK172 (hardcoded in fifazf.exe)
    start("messenger.py", [])  # :28002, address handed out by /info/my/services/messenger/2
    console("[start_all] http_config.py (:443 https, admin :8088) + messenger.py (:28002) up. Ctrl-C to stop.\n")

    if selftest:
        time.sleep(3)
        alive = all(p.poll() is None for _, p in procs)
        shutdown()
        console("[start_all] selftest " + ("OK" if alive else "FAILED") + "\n")
        sys.exit(0 if alive else 1)

    try:
        while all(p.poll() is None for _, p in procs):
            time.sleep(0.5)
    except KeyboardInterrupt:
        pass
    finally:
        shutdown()
        console("[start_all] stopped.\n")


if __name__ == "__main__":
    main()
