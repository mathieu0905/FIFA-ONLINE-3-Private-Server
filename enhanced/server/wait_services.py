"""Check the local HTTPS API, admin and messenger before launching FO3."""
import argparse
import json
import socket
import ssl
import time
import urllib.request


def ready():
    context = ssl._create_unverified_context()  # This installation uses a local self-signed certificate.
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}),
                                        urllib.request.HTTPSHandler(context=context))
    with opener.open('https://127.0.0.1/info/my/services/messenger/2', timeout=1) as response:
        service = json.load(response)
    if service.get('result') is not True or service.get('address') != '127.0.0.1' or service.get('port') != 28002:
        raise RuntimeError('Unexpected local messenger configuration')
    with opener.open('http://127.0.0.1:8088/', timeout=1) as response:
        if b'FO3ID admin' not in response.read():
            raise RuntimeError('FO3ID admin page is unavailable')
    with socket.create_connection(('127.0.0.1', 28002), timeout=1):
        pass


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--timeout', type=float, default=25)
    args = parser.parse_args()
    deadline = time.monotonic() + args.timeout
    error = 'Services have not started'
    while True:
        try:
            ready()
            print('FO3ID ready: HTTPS API, admin and messenger.')
            break
        except (OSError, ValueError, RuntimeError) as exc:
            error = str(exc)
        if time.monotonic() >= deadline:
            parser.exit(1, 'FO3ID startup failed: ' + error + '\n')
        time.sleep(0.4)
