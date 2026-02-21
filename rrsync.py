#!/usr/bin/env python3
"""
rrsync.py — Restrict rsync to a specific directory via SSH forced command.

Usage in authorized_keys:

    command="rrsync.py [-ro] [--log-file /path/to/log] topdir" ssh-rsa AAAA...

Examples:

    command="rrsync.py logs/client" ssh-rsa ...
    command="rrsync.py -ro results" ssh-rsa ...

Environment variables provided by sshd:

    SSH_ORIGINAL_COMMAND
    SSH_CLIENT

By Tyler Bletsch (Tyler.Bletsch@gmail.com)
Last revised 2026-02-21
"""

import argparse
import os
import re
import shlex
import socket
import sys
from datetime import datetime
from pathlib import Path
from typing import Tuple # needed on python < 3.9 to do proper type hinting with tuples


# ---------------------------------------------------------------------
# SSH command parsing
# ---------------------------------------------------------------------

def get_original_command() -> str:
    cmd = os.environ.get("SSH_ORIGINAL_COMMAND")
    if not cmd:
        sys.exit("Not invoked via sshd")
    return cmd


def split_rsync_command(command: str) -> Tuple[str, str]:
    """
    Split into:
        cmd_prefix: 'rsync --server ... .'
        requested_target: destination path
    """

    match = re.match(r"(.* \.) ?(.*)", command)
    if not match:
        sys.exit(f"SSH_ORIGINAL_COMMAND='{command}' is not rsync")

    cmd_prefix, target = match.groups()

    if not cmd_prefix.startswith("rsync "):
        sys.exit(f"SSH_ORIGINAL_COMMAND='{command}' is not rsync")

    return cmd_prefix, target


# ---------------------------------------------------------------------
# Target sanitization and restriction
# ---------------------------------------------------------------------

def resolve_target(top: Path, requested: str) -> Path:
    top = top.resolve(strict=True)
    requested_path = Path(requested)

    if requested_path.is_absolute():
        candidate = requested_path.resolve(strict=False)
    else:
        candidate = (top / requested_path).resolve(strict=False)
    
    candidate.relative_to(top)  # raises ValueError if outside!

    return candidate


# ---------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------

def write_log(log_file: Path, command: str, message: str):

    if not log_file:
        return

    host = os.environ.get("SSH_CLIENT", "unknown").split()[0]
    timetamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    line = f"[{timetamp}] {host:<13} [{command}] {message}\n"

    with log_file.open("a") as f:
        f.write(line)


# ---------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------

def main():
    # command line args
    parser = argparse.ArgumentParser(description="Restrict rsync to a specific directory")
    parser.add_argument("-ro", "--read-only", action="store_true", help="Allow read-only access only")
    parser.add_argument("--log-file", type=Path, default=None, help="Optional log file path")
    parser.add_argument("topdir", type=Path, help="Top-level allowed directory")
    args = parser.parse_args()

    original_command = get_original_command()
    cmd_prefix, requested_target = split_rsync_command(original_command)

    if args.read_only and not cmd_prefix.startswith("rsync --server --sender "):
        write_log(args.log_file, original_command, "Read-only violation")
        sys.exit(f"Read-only mode: sending to directory '{requested_target}' not allowed")

    try:
        target = resolve_target(args.topdir, requested_target)
    except ValueError: # attempt to escape top dir
        write_log(args.log_file, original_command, "Top dir violation")
        sys.exit(f"Attempt to access content outside of '{args.topdir}' not allowed")

    write_log(args.log_file, original_command, "OK")

    final_cmd = f"{cmd_prefix} {shlex.quote(str(target))}"

    os.execvp("rsync", shlex.split(final_cmd))


if __name__ == "__main__":
    main()