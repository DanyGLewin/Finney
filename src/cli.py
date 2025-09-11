import os
import pickle
from collections import defaultdict
from enum import Enum
from hashlib import sha256
from pathlib import Path
from typing import Sequence

import click
from rich.console import Console
from rich.table import Table
from rich import box
import yaml

import search
from domain_objects import Match, IgnoreConfig

root = ".finney"
config_path = f"{root}/config"
last_matches_path = f"{root}/matches"

if not os.path.exists(root):
    os.mkdir(root)


class ENTRY_TYPE(Enum):
    STRINGS = "STRINGS"
    FILES = "FILES"
    DIRS = "DIRS"
    TYPES = "SUFFIXES"  # finney: ignore


class MODE(Enum):
    ADD = "ADD"
    SUBTRACT = "SUBTRACT"


def _get_recursive_paths(paths: list[str]) -> list[str]:
    files = []
    for dir_path in paths:
        path = Path(dir_path)
        if path.is_dir():
            files.extend(str(p) for p in path.rglob('*') if p.is_file())
    return files


def _load_ignore_config() -> IgnoreConfig:
    if not os.path.exists(config_path):
        return IgnoreConfig(dirs=[], files=[], types=[], strings=[])

    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

    config = config.get("ignore", {})
    return IgnoreConfig(
        dirs=config.get("dirs") or [],
        files=config.get("files") or [],
        types=config.get("types") or [],
        strings=config.get("strings") or [],
    )


def _edit_ignore_entries(
        entry_type: ENTRY_TYPE, mode: MODE, values: Sequence[str]
) -> None:
    prev_config = _load_ignore_config()

    if mode == MODE.ADD and entry_type == ENTRY_TYPE.STRINGS:
        last_run_hashes = _load_last_matches()
        temp = set(values)
        for value in values:
            hashed_value = sha256(value.encode("utf-8")).hexdigest()
            if hashed_value not in last_run_hashes:
                if not click.confirm(f"String {value} was not found in the last run. Are you sure you want to ignore it?", default=True, prompt_suffix="\n>>> "):
                    temp.remove(value)
        values = list(temp)


    added_config = IgnoreConfig(
        dirs=values if entry_type == ENTRY_TYPE.DIRS else [],
        files=values if entry_type == ENTRY_TYPE.FILES else [],
        types=values if entry_type == ENTRY_TYPE.TYPES else [],
        strings=values if entry_type == ENTRY_TYPE.STRINGS else [],
    )
    combined = (
        prev_config + added_config if mode == MODE.ADD else prev_config - added_config
    )
    with open(config_path, "w+") as f:
        yaml.safe_dump(
            {"ignore": combined.to_dict()},
            f,
            indent=4,
            default_flow_style=False,
            sort_keys=False,
        )
    entry_str = "entry" if len(values) == 1 else "entries"
    if mode == MODE.ADD:
        print(f"Added {len(values)} {entry_str} to ignore list")
    else:
        print(f"Removed {len(values)} {entry_str} from ignore list")


def _select_entry_type(
        strings: bool, files: bool, dirs: bool, types: bool
) -> ENTRY_TYPE:
    if sum([strings, files, dirs, types]) > 1:
        raise click.UsageError("Options -s, -f, -d, -t, and -i are mutually exclusive")

    elif types:
        return ENTRY_TYPE.TYPES

    elif files:
        return ENTRY_TYPE.FILES

    elif dirs:
        return ENTRY_TYPE.DIRS

    elif strings:
        return ENTRY_TYPE.STRINGS

    else:
        return ENTRY_TYPE.STRINGS


def _save_last_matches(matches: Sequence[Match]) -> None:
    with open(last_matches_path, "wb+") as f:
        pickle.dump(matches, f)


def _load_last_matches() -> Sequence[str]:
    if not os.path.exists(last_matches_path):
        return []
    with open(last_matches_path, "rb") as f:
        matches: list[Match] = pickle.load(f)
    return [m.sha for m in matches]


@click.group(help="Scan your code repositories for hardcoded passwords and secrets")
def cli():
    pass


def _matches_by_file(matches: Sequence[Match]) -> dict[str, list[Match]]:
    out = defaultdict(list)
    for match in matches:
        out[str(match.path)].append(match)
    return out


def _print_match_group(matches: list[Match]) -> None:
    matches.sort(key=lambda x: x.line)
    table = Table(box=box.MINIMAL)
    print(f"In file: {matches[0].path}")
    table.add_column("Line", justify="right")
    table.add_column("Suspected Secret", justify="left")

    for m in matches:
        table.add_row(str(m.line), m.match)

    console = Console()
    console.print(table)


def _pretty_print(matches: Sequence[Match]) -> None:
    match_groups = _matches_by_file(matches)
    matches_str = f"{len(matches)} {'secrets' if len(matches) > 1 else 'secret'}"
    files_str = f"{len(match_groups)} {'files' if len(match_groups) > 1 else 'group'}"
    click.secho(
        f"Found suspected {matches_str} in {files_str}:\n"
    )
    for path, group in sorted(match_groups.items(), key=lambda item: item[1][0].path):
        _print_match_group(group)
        print()
    print("""If these are real secrets, consider removing them from your code before committing.
If they aren't, you can mark them as safe in the following ways:
- Ignore specific strings explicity:
    finney ignore [STRINGS...]
    
- Ignore specific strings by ID:
    finney ignore -i [ID...]
    
- Ignore entire files:
    finney ignore -f [FILE_NAME...]""")


@cli.command(help="Run Finney on the given files")
@click.argument("paths", nargs=-1)
@click.option("-r", "recursive", is_flag=True, default=False, help="Recursively search the given paths")
def run(paths, recursive):
    ignored = _load_ignore_config()
    if recursive:
        paths = _get_recursive_paths(paths)
    matches: Sequence[Match] = search.scan_files(paths, ignored)

    if matches:
        _pretty_print(matches)
        _save_last_matches(matches)
        exit(1)
    print("Finney didn't find any suspected secrets :D")


@cli.command("ignore", help="Defined values that can be safely ignored")
@click.option("-s", "strings", is_flag=True, help="Define specific strings as safe (default)")
@click.option("-f", "files", is_flag=True, help="Define files that Finney won't scan")
@click.option("-d", "dirs", is_flag=True, help="Define directories that Finney won't scan")
@click.option("-t", "types", is_flag=True, help="Define file types (.exe, .jar, ...) that Finney won't scan")
@click.argument("values", nargs=-1)
def ignore(strings, files, dirs, types, values):
    entry_type = _select_entry_type(strings, files, dirs, types)
    _edit_ignore_entries(entry_type, mode=MODE.ADD, values=list(values))


@cli.command("unignore", help="Remove values from the ignore list.\nSee `finney ignore` for details`")
@click.option("-s", "strings", is_flag=True, help="Remove strings from the ignored list (default)")
@click.option("-f", "files", is_flag=True, help="Remove files from the ignored list")
@click.option("-d", "dirs", is_flag=True, help="Remove directories from the ignore list")
@click.option("-t", "types", is_flag=True, help="Remove file types from the ignore list")
@click.argument("values", nargs=-1)
def unignore(strings, files, dirs, types, values):
    entry_type = _select_entry_type(strings, files, dirs, types)
    _edit_ignore_entries(entry_type, mode=MODE.SUBTRACT, values=list(values))


@cli.command("list", help="Print the current ignore configuration")
def _list():
    config = _load_ignore_config()
    config.print()


if __name__ == "__main__":
    cli()
