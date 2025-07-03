from pathlib import Path
from typing import Sequence

import click

from domain_objects import Match, IgnoreConfig
from models import intrinsic, decision_tree


def should_scan(file: Path, ignored: IgnoreConfig) -> bool:
    if file.suffix in ignored.types:
        return False
    if file.name in ignored.files:
        return False
    for dir in ignored.dirs:
        if dir in file.parts:
            return False
    return True


def scan_files(paths: Sequence[str], ignored: IgnoreConfig) -> list[Match]:
    files = [Path(f) for f in paths]
    matches = []
    hide_bar = len(paths) < 10
    with click.progressbar(files, label="Scanning files", hidden=hide_bar) as bar:
        for file in files:
            if not should_scan(file, ignored):
                continue
            try:
                res = intrinsic.scan(file, ignored)
                # res = decision_tree.scan(file)
                matches.extend([Match(file, s) for s in res])
            except Exception as e:
                print(f"Failed to scan {file}")
                raise
    return matches
