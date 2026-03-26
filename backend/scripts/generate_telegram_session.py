#!/usr/bin/env python3
"""
One-time helper script to generate a Telethon StringSession.

Run this LOCALLY (not in Docker) — it requires interactive input
to authenticate with Telegram (phone number, verification code, and
optionally 2FA password).

Usage:
    pip install telethon
    python backend/scripts/generate_telegram_session.py

The script auto-reads TELEGRAM_API_ID and TELEGRAM_API_HASH from the
.env file in the project root. If not found, it falls back to prompting.

You will be prompted for:
    1. Your phone number (with country code, e.g. +1234567890)
    2. The verification code Telegram sends you
    3. Your 2FA password (if enabled)

The script prints a session string and offers to save it directly
to your .env file as the TELEGRAM_SESSION value.

Get your API ID and API Hash at https://my.telegram.org
"""

import sys
from pathlib import Path
from typing import Dict, Optional


def _find_env_file() -> Optional[Path]:
    """Walk up from script location to find .env in the project root."""
    current = Path(__file__).resolve().parent
    for _ in range(5):  # max 5 levels up
        env_path = current / ".env"
        if env_path.exists():
            return env_path
        current = current.parent
    return None


def _read_env_vars(env_path: Path) -> Dict[str, str]:
    """Parse key=value pairs from a .env file."""
    env_vars = {}  # type: Dict[str, str]
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, _, value = line.partition("=")
            env_vars[key.strip()] = value.strip()
    return env_vars


def _save_session_to_env(env_path: Path, session_string: str) -> None:
    """Write the session string into the .env file."""
    lines = env_path.read_text().splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith("TELEGRAM_SESSION"):
            lines[i] = f"TELEGRAM_SESSION={session_string}"
            found = True
            break
    if not found:
        lines.append(f"TELEGRAM_SESSION={session_string}")
    env_path.write_text("\n".join(lines) + "\n")


def main():
    try:
        from telethon.sync import TelegramClient
        from telethon.sessions import StringSession
    except ImportError:
        print("Telethon is not installed. Run: pip install telethon")
        sys.exit(1)

    print("=" * 60)
    print("  Telegram Session Generator")
    print("=" * 60)
    print()

    # Try to load from .env
    env_path = _find_env_file()
    env_vars = {}  # type: Dict[str, str]
    if env_path:
        env_vars = _read_env_vars(env_path)
        print(f"  Found .env at {env_path}")
    else:
        print("  No .env file found — will prompt for credentials.")

    # API ID
    api_id = None  # type: Optional[int]
    raw_id = env_vars.get("TELEGRAM_API_ID", "")
    if raw_id:
        try:
            api_id = int(raw_id)
            print(f"  Using TELEGRAM_API_ID={api_id} from .env")
        except ValueError:
            pass

    if api_id is None:
        print()
        print("Get your API credentials at https://my.telegram.org")
        try:
            api_id = int(input("Enter your API ID: ").strip())
        except (ValueError, EOFError):
            print("Error: API ID must be an integer.")
            sys.exit(1)

    # API Hash
    api_hash = env_vars.get("TELEGRAM_API_HASH", "")
    if api_hash:
        print(f"  Using TELEGRAM_API_HASH={api_hash[:8]}... from .env")
    else:
        api_hash = input("Enter your API Hash: ").strip()
        if not api_hash:
            print("Error: API Hash cannot be empty.")
            sys.exit(1)

    print()
    print("Connecting to Telegram...")
    print("You will be asked for your phone number and verification code.")
    print()

    with TelegramClient(StringSession(), api_id, api_hash) as client:
        session_string = client.session.save()
        print()
        print("=" * 60)
        print("  SUCCESS!")
        print("=" * 60)
        print()

        # Offer to save directly to .env
        if env_path:
            save = input("Save session to .env automatically? [Y/n] ").strip().lower()
            if save in ("", "y", "yes"):
                _save_session_to_env(env_path, session_string)
                print(f"  Saved to {env_path}")
                print()
                print(
                    "You're done! Run: docker compose down && docker compose up --build"
                )
                print()
                return

        # Fallback: print it
        print("  Copy the session string below into your .env file")
        print("  as TELEGRAM_SESSION. KEEP IT SECRET.")
        print("=" * 60)
        print()
        print(session_string)
        print()


if __name__ == "__main__":
    main()
