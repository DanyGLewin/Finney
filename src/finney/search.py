from pathlib import Path
from typing import Sequence

import click

from finney.domain_objects import Match, IgnoreConfig
from finney.models import intrinsic, decision_tree


def should_scan(file: Path, ignored: IgnoreConfig) -> bool:
    if file.suffix in ignored.types:
        return False
    if file.name in ignored.files:
        return False
    for dir in ignored.dirs:
        if dir in file.parts:
            return False
    return True


def find_lines(matches: list[Match]) -> list[Match]:
    out = []
    for match in matches:
        with open(match.path, "r") as f:
            for i, line in enumerate(f.readlines(), start=1):
                if match.match in line:
                    if "finney: ignore" not in line.casefold():
                        out.append(Match(match.path, match.match, i))
                    break
            else:
                raise ValueError(f"Expected to find suspected secret '{match.match}' in file '{match.path}'")
    return out


keywords = set()
with open("src/finney/data/keywords.txt", "r") as f:  # taken from https://github.com/e3b0c442/keywords?tab=readme-ov-file
    for line in f.readlines():
        keywords.add(line.strip().casefold())


def clean_matches(matches: list[Match]) -> list[Match]:
    matches = [m for m in matches if m.match.casefold() not in keywords]
    return list(set(matches))


def make_paths_relative(paths: list[Path]) -> list[Path]:
    out = []
    for p in paths:
        p = p.expanduser()
        if not p.is_absolute():
            p = Path.cwd() / p
        out.append(p.resolve(strict=False))
    return out

def scan_files(paths: Sequence[str], ignored: IgnoreConfig) -> list[Match]:
    files = [Path(f) for f in paths]
    matches = []
    hide_bar = len(paths) < 10
    with click.progressbar(files, label="Scanning files", hidden=hide_bar, show_pos=True) as bar:
        for file in bar:
            if not should_scan(file, ignored):
                continue
            try:
                res = intrinsic.scan(file, ignored)
                matches.extend([Match(file, s) for s in res])

                res = decision_tree.scan(file)
                matches.extend([Match(file, s) for s in res])
            except Exception as e:
                print(f"Failed to scan {file}")
                raise e
    if len(matches) > 1000:
        print("Collecting Results...")
    matches = find_lines(clean_matches(matches))
    return matches
