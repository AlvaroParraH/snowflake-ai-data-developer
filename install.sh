#!/usr/bin/env bash
set -euo pipefail

if [[ $# -eq 0 ]]; then
    set -- --shared --yes --personal-skills
fi

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
AUTO_YES=0
NO_INSTALL=0
for argument in "$@"; do
    case "$argument" in
        --yes) AUTO_YES=1 ;;
        --no-install|--dry-run|--help|-h|--update) NO_INSTALL=1 ;;
    esac
done

detect_python() {
    local candidate
    for candidate in "${PYTHON:-}" python3.15 python3.14 python3.13 python3.12 python3.11 python3.10 python3; do
        [[ -n "$candidate" ]] || continue
        if command -v "$candidate" >/dev/null 2>&1 &&
            "$candidate" -c 'import sys; sys.exit(sys.version_info < (3, 10))' >/dev/null 2>&1; then
            printf '%s\n' "$candidate"
            return 0
        fi
    done
    return 1
}

run_privileged() {
    if [[ "$EUID" -eq 0 ]]; then
        "$@"
    elif command -v sudo >/dev/null 2>&1; then
        sudo "$@"
    else
        printf '%s\n' "Error: sudo is required to install Python packages." >&2
        return 1
    fi
}

PYTHON_BIN="$(detect_python || true)"
if [[ -z "$PYTHON_BIN" ]]; then
    INSTALL_COMMAND=()
    case "$(uname -s)" in
        Darwin)
            if command -v brew >/dev/null 2>&1; then
                INSTALL_COMMAND=(brew install python@3.11)
            fi
            ;;
        Linux)
            if [[ -f /run/ostree-booted ]]; then
                printf '%s\n' \
                    "Error: Missing Python 3.10+ on a Fedora Atomic/OSTree host." \
                    "Automatic Python installation is disabled here, even with --yes." \
                    "System package layering requires a reboot. Review and run manually:" \
                    "  sudo rpm-ostree install python3 python3-pip" \
                    "  systemctl reboot" \
                    "Then rerun the installer from the host terminal."
                if command -v distrobox >/dev/null 2>&1; then
                    printf '%s\n' \
                        "Alternatively, install inside an existing Fedora Distrobox:" \
                        "  distrobox enter <your-box> -- sudo dnf install -y python3 python3-pip" \
                        "Then rerun the installer inside that box, not on the host."
                fi
                exit 1
            fi
            if command -v apt-get >/dev/null 2>&1; then
                INSTALL_COMMAND=(run_privileged apt-get install -y python3 python3-venv python3-pip)
            elif command -v dnf >/dev/null 2>&1; then
                INSTALL_COMMAND=(run_privileged dnf install -y python3 python3-pip)
            elif command -v pacman >/dev/null 2>&1; then
                INSTALL_COMMAND=(run_privileged pacman -S --noconfirm python python-pip)
            fi
            ;;
    esac
    if [[ "${#INSTALL_COMMAND[@]}" -eq 0 ]]; then
        printf '%s\n' "Error: Python 3.10+ is required. Install it manually (Homebrew is required on macOS), then rerun." >&2
        exit 1
    fi
    printf 'Missing Python 3.10+. Installation command:'
    printf ' %s' "${INSTALL_COMMAND[@]}"
    printf '\n'
    if [[ "$NO_INSTALL" -eq 1 ]]; then
        printf '%s\n' "Error: Python installation is disabled by --no-install, --dry-run, --help, or --update. Install Python manually to continue." >&2
        exit 1
    fi
    if [[ "$AUTO_YES" -ne 1 ]]; then
        if [[ ! -t 0 ]]; then
            printf '%s\n' "Error: Python installation requires confirmation or --yes." >&2
            exit 1
        fi
        read -r -p "Install Python using the command above? [y/N] " reply
        if [[ "$reply" != "y" && "$reply" != "Y" && "$reply" != "yes" && "$reply" != "YES" ]]; then
            printf '%s\n' "Error: Python installation declined; nothing installed." >&2
            exit 1
        fi
    fi
    if ! "${INSTALL_COMMAND[@]}"; then
        printf '%s\n' "Error: Python installation failed. Inspect the package-manager output and install Python 3.10+ manually." >&2
        exit 1
    fi
    hash -r
    PYTHON_BIN="$(detect_python || true)"
    if [[ -z "$PYTHON_BIN" ]]; then
        printf '%s\n' "Error: Installation completed but Python 3.10+ is not on PATH. Fix PATH or set PYTHON to its executable, then rerun." >&2
        exit 1
    fi
fi
if [[ "${1:-}" == "--shared" ]]; then
    shift
    exec "$PYTHON_BIN" "$SCRIPT_DIR/scripts/install_shared.py" "$@"
fi
exec "$PYTHON_BIN" "$SCRIPT_DIR/scripts/install_kit.py" "$@"
