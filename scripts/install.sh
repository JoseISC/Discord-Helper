#!/usr/bin/env bash
# Discord Helper — cross-platform installer (Linux + macOS)
# Usage: curl -fsSL https://raw.githubusercontent.com/JoseISC/Discord-Helper/instalador/scripts/install.sh | bash
set -euo pipefail

APP_NAME="discord-helper"
REPO_URL="https://github.com/JoseISC/Discord-Helper.git"
BRANCH="${DISCORD_HELPER_BRANCH:-instalador}"
INSTALL_DIR="$HOME/.local/share/$APP_NAME/source"

# ── helpers ──────────────────────────────────────────────────────────────────

_print()  { printf "\n%s\n" "$*"; }
_ok()     { printf "  [OK] %s\n" "$*"; }
_warn()   { printf "  [!]  %s\n" "$*"; }
_fail()   { printf "\n[ERROR] %s\n" "$*" >&2; exit 1; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

OS="$(uname -s)"

# ── dependency checks ────────────────────────────────────────────────────────

ensure_python() {
  if ! command_exists python3; then
    _fail "Python 3 is required but was not found. Install Python 3.10+ and rerun."
  fi

  local ver
  ver="$(python3 -c 'import sys; print(sys.version_info[:2])')"
  _ok "Python: $ver"
}

ensure_git() {
  if ! command_exists git; then
    _fail "git is required but was not found. Install git and rerun."
  fi
  _ok "git: $(git --version)"
}

ensure_pipx() {
  if command_exists pipx; then
    _ok "pipx: $(pipx --version)"
    return
  fi

  _warn "pipx not found — installing via pip..."
  python3 -m pip install --user --quiet pipx
  python3 -m pipx ensurepath || true
  _ok "pipx installed"
}

# ── ffmpeg ────────────────────────────────────────────────────────────────────

install_ffmpeg() {
  if command_exists ffmpeg; then
    _ok "FFmpeg: $(ffmpeg -version 2>&1 | head -1)"
    return
  fi

  _warn "FFmpeg not found — attempting automatic installation..."

  if [ "$OS" = "Darwin" ]; then
    if command_exists brew; then
      brew install --quiet ffmpeg && _ok "FFmpeg installed via Homebrew"
    else
      _warn "Homebrew not found. Install FFmpeg manually: https://ffmpeg.org/download.html"
    fi
  elif [ "$OS" = "Linux" ]; then
    if command_exists apt-get; then
      sudo apt-get install -y -qq ffmpeg && _ok "FFmpeg installed via apt"
    elif command_exists dnf; then
      sudo dnf install -y -q ffmpeg && _ok "FFmpeg installed via dnf"
    elif command_exists pacman; then
      sudo pacman -S --noconfirm --quiet ffmpeg && _ok "FFmpeg installed via pacman"
    else
      _warn "Unknown package manager. Install FFmpeg manually: https://ffmpeg.org/download.html"
    fi
  fi
}

# ── NVIDIA / CUDA detection ───────────────────────────────────────────────────

detect_nvidia() {
  if command_exists nvidia-smi; then
    _ok "NVIDIA GPU detected — will install with [cuda] extras"
    INSTALL_EXTRAS="[cuda]"
  else
    _warn "No NVIDIA GPU detected — installing CPU-only version"
    INSTALL_EXTRAS=""
  fi
}

# ── source install ────────────────────────────────────────────────────────────

install_source() {
  mkdir -p "$(dirname "$INSTALL_DIR")"

  if [ -d "$INSTALL_DIR/.git" ]; then
    _print "Updating existing source at $INSTALL_DIR"
    git -C "$INSTALL_DIR" fetch --quiet origin "$BRANCH"
    git -C "$INSTALL_DIR" checkout --quiet "$BRANCH"
    git -C "$INSTALL_DIR" pull --quiet origin "$BRANCH"
  else
    _print "Cloning $REPO_URL (branch: $BRANCH) into $INSTALL_DIR"
    git clone --quiet --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
  fi

  _ok "Source ready at $INSTALL_DIR"
}

install_package() {
  _print "Installing Discord Helper with pipx..."
  pipx install --force "$INSTALL_DIR${INSTALL_EXTRAS}"
  _ok "discord-helper installed"
}

verify_install() {
  if command_exists discord-helper || [ -f "$HOME/.local/bin/discord-helper" ]; then
    _ok "Binary: $(command -v discord-helper 2>/dev/null || echo "$HOME/.local/bin/discord-helper")"
  else
    _warn "discord-helper not found in PATH. You may need to restart your shell or run:"
    _warn "  export PATH=\"\$HOME/.local/bin:\$PATH\""
  fi
}

# ── main ──────────────────────────────────────────────────────────────────────

main() {
  printf "\nDiscord Helper Installer\n"
  printf "========================\n"

  INSTALL_EXTRAS=""

  ensure_python
  ensure_git
  ensure_pipx
  detect_nvidia
  install_source
  install_package
  install_ffmpeg
  verify_install

  printf "\n"
  printf "Installation complete!\n"
  printf "\nNext steps:\n"
  printf "  discord-helper setup       # configure your bot token + models\n"
  printf "  discord-helper doctor      # verify all dependencies\n"
  printf "  discord-helper run         # start the bot\n"
  printf "\nOptional (run as background service):\n"
  printf "  discord-helper install-service\n\n"
}

main "$@"
