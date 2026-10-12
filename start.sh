#!/usr/bin/env sh
case "$(uname -s)" in
  Darwin) exec "$(dirname "$0")/scripts/start_macos.sh" ;;
  Linux*) exec "$(dirname "$0")/scripts/start_linux.sh" ;;
  *) echo "Unsupported operating system." >&2; exit 1 ;;
esac
