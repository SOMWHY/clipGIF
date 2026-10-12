import sys
import time
from urllib.request import urlopen


def main() -> int:
    port = int(sys.argv[1])
    health_url = f"http://127.0.0.1:{port}/health"
    for _ in range(20):
        try:
            with urlopen(health_url, timeout=1) as response:
                if response.status == 200:
                    return 0
        except OSError:
            time.sleep(1)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
