#!/usr/bin/env bash
set -euo pipefail

APP_NAME="discord-helper"
REPO_URL="https://github.com/JoseISC/Discord-Helper.git"
BRANCH="instalador"
INSTALL_DIR="$HOME/.local/share/$APP_NAME/source"

printf "\nDiscord Helper Installer\n"
printf "========================\n\n"

OS="$(uname -s)"

command_exists() {
  command -v "$1" >/dev/null 2>&1
}

ensure_python() {
  if ! command_exists python3; then
    echo "Python 3 is required but was not found."
    echo "Install Python 3.10+ and run this installer again."
    exit 1
  fi
}

ensure_git() {
  if ! command_exists git; then
    echo "git is required but was not found."
    echo "Install git and run this installer again."
    exit 1
  fi
}

ensure_pipx() {
  if command_exists pipx; then
    return
  fi

  echo "pipx was not found. Trying to install it with python -m pip."
  python3 -m pip install --user pipx
  python3 -m pipx ensurepath || true
}

install_ffmpeg_hint() {
  if command_exists ffmpeg; then
    echo "FFmpeg: OK"
    return
  fi

  echo "FFmpeg was not found."

  if [ "$OS" = "Linux" ]; then
    echo "Install it with your distro package manager, for example:"
    echo "  sudo apt install ffmpeg"
  elif [ "$OS" = "Darwin" ]; then
    echo "Install it with Homebrew:"
    echo "  brew install ffmpeg"
  fi
}

install_source() {
  mkdir -p "$(dirname "$INSTALL_DIR")"

  if [ -d "$INSTALL_DIR/.git" ]; then
    echo "Updating existing source at $INSTALL_DIR"
    git -C "$INSTALL_DIR" fetch origin "$BRANCH"
    git -C "$INSTALL_DIR" checkout "$BRANCH"
    git -C "$INSTALL_DIR" pull origin "$BRANCH"
  else
    echo "Cloning $REPO_URL into $INSTALL_DIR"
    git clone --branch "$BRANCH" "$REPO_URL" "$INSTALL_DIR"
  fi
}

install_package() {
  echo "Installing Discord Helper with pipx"
  pipx install --force "$INSTALL_DIR"
}

main() {
  ensure_python
  ensure_git
  ensure_pipx
  install_source
  install_package
  install_ffmpeg_hint

  printf "\nInstallation complete.\n"
  printf "Next steps:\n"
  printf "  discord-helper setup\n"
  printf "  discord-helper doctor\n"
  printf "  discord-helper run\n\n"
}

main "$@"
