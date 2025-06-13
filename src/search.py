import mmap
import re
from hashlib import sha256
from pathlib import Path
from typing import Sequence

import click

from domain_objects import Match, IgnoreConfig

regexes = [
    rb"[1-9][0-9]+-[0-9a-zA-Z]{40}",
    rb"EAACEdEose0cBA[0-9A-Za-z]+",
    rb"AIza[0-9A-Za-z\-_]{35}",
    rb"[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com",
    rb"sk_live_[0-9a-z]{32}",
    rb"sk_live_[0-9a-zA-Z]{24}",
    rb"rk_live_[0-9a-zA-Z]{24}",
    rb"sq0atp-[0-9A-Za-z\-_]{22}",
    rb"sq0csp-[0-9A-Za-z\-_]{43}",
    rb"access_token\$production\$[0-9a-z]{16}\$[0-9a-f]{32}",
    rb"amzn\.mws\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    rb"SK[0-9a-fA-F]{32}",
    rb"key-[0-9a-zA-Z]{32}",
    rb"[0-9a-f]{32}-us[0-9]{1,2}",
    rb"AKIA[0-9A-Z]{16}",
    # rb"[\w\-\.]+@([\w-]+\.)+[\w-]{2,}"
]


def should_scan(file: Path, ignored: IgnoreConfig) -> bool:
    if file.suffix in ignored.suffixes:
        return False
    if file.name in ignored.files:
        return False
    for dir in ignored.dirs:
        if dir in file.parts:
            return False
    return True


def scan(file_path: Path, ignored: IgnoreConfig) -> list[Match]:
    matches = []
    with open(file_path, "r+") as f:
        try:
            data = mmap.mmap(f.fileno(), 0)
        except ValueError as e:
            if e.args[0] == 'cannot mmap an empty file':
                return []
        for regex in regexes:
            if mo := re.search(regex, data):
                match_bytes = mo.group()
                match_hash = sha256(match_bytes).hexdigest()
                if match_hash in ignored.hashes:
                    continue
                matches.append(Match(file_path, match_bytes))
    return matches


def scan_files(paths: Sequence[str], ignored: IgnoreConfig) -> list[Match]:
    files = [Path(f) for f in paths]
    matches = []
    hide_bar = len(paths) <= 1
    with click.progressbar(files, label="Scanning files", hidden=hide_bar) as bar:
        for file in bar:
            if not should_scan(file, ignored):
                continue
            try:
                matches.extend(scan(file, ignored))
            except Exception as e:
                print(f"Failed to scan {file}")
                raise
    return matches
