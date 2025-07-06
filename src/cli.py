import math
import os
import pickle
from collections import defaultdict
from enum import Enum
from hashlib import sha256
from typing import Sequence

import click
import yaml

import search
from domain_objects import Match, IgnoreConfig

config_path = ".secrets/config"
last_matches_path = ".secrets/log"


class ENTRY_TYPE(Enum):
    STRINGS = "STRINGS"
    FILES = "FILES"
    DIRS = "DIRS"
    TYPES = "SUFFIXES"


class MODE(Enum):
    ADD = "ADD"
    SUBTRACT = "SUBTRACT"


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

    if entry_type == ENTRY_TYPE.STRINGS:
        byte_values = [val.encode("utf-8") for val in values]
        values = [sha256(val).hexdigest() for val in byte_values]

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


def _select_entry_type(
        strings: bool, files: bool, dirs: bool, types: bool, index: bool
) -> ENTRY_TYPE:
    if sum([strings, files, dirs, types]) > 1:
        raise click.UsageError("Options -s, -f, -d, -t, and -i are mutually exclusive")

    elif types:
        return ENTRY_TYPE.TYPES

    elif files:
        return ENTRY_TYPE.FILES

    elif dirs:
        return ENTRY_TYPE.DIRS

    elif index:
        return ENTRY_TYPE.STRINGS

    elif strings:
        return ENTRY_TYPE.STRINGS

    else:
        return ENTRY_TYPE.STRINGS


def _save_last_matches(matches: Sequence[Match]) -> None:
    with open(last_matches_path, "wb+") as f:
        pickle.dump(matches, f)


def _load_last_matches(indices: Sequence[int]) -> Sequence[str]:
    selected_matches = []
    with open(last_matches_path, "rb") as f:
        matches: list[Match] = pickle.load(f)
    for index in indices:
        selected_matches.append(matches[index - 1].match)
    return selected_matches


@click.group()
def cli():
    pass


def _matches_by_file(matches: Sequence[Match]) -> dict[str, list[Match]]:
    out = defaultdict(list)
    for match in matches:
        out[str(match.path)].append(match)
    return out


def _print_match_group(matches: Sequence[Match], start: int) -> None:
    click.secho(f"  {matches[0].path}:", fg="red")
    i = start
    longest = max([len(m) for m in matches])
    for match in matches:
        click.secho(f"    {i:>2}: {match.render(longest)}", fg="red")
        i += 1


def _pretty_print(matches: Sequence[Match]) -> None:
    match_groups = _matches_by_file(matches)
    matches_str = f"{len(matches)} {'secrets' if len(matches) > 1 else 'secret'}"
    files_str = f"{len(match_groups)} {'files' if len(match_groups) > 1 else 'group'}"
    click.secho(
        f"Found {matches_str} in {files_str}:",
        fg="red"
    )
    index = 1
    for path, group in match_groups.items():
        _print_match_group(group, index)
        index += len(group)
        print()


@cli.command()
@click.argument("paths", nargs=-1)
def run(paths):
    ignored = _load_ignore_config()
    matches: Sequence[Match] = search.scan_files(paths, ignored)
    if matches:
        _pretty_print(matches)
        _save_last_matches(matches)
        exit(1)


@cli.command("ignore")
@click.option("-s", "strings", is_flag=True, help="Add specific strings to ignore list (default)")
@click.option("-f", "files", is_flag=True, help="Add files to ignore list (default)")
@click.option("-d", "dirs", is_flag=True, help="Add directories to ignore list")
@click.option("-t", "types", is_flag=True, help="Add file types to ignore list")
@click.option("-i", "index", is_flag=True, help="Add word by index in previous run")
@click.argument("values", nargs=-1)
def ignore(strings, files, dirs, types, index, values):
    if index:
        indices = [int(s) for s in values]
        values = _load_last_matches(indices)
    entry_type = _select_entry_type(strings, files, dirs, types, index)
    _edit_ignore_entries(entry_type, mode=MODE.ADD, values=list(values))


@cli.command("unignore")
@click.option("-s", "strings", is_flag=True, help="Remove specific strings from ignore list (default)")
@click.option("-f", "files", is_flag=True, help="Remove files from list")
@click.option("-d", "dirs", is_flag=True, help="Remove directories from ignore list")
@click.option("-t", "types", is_flag=True, help="Remove file types from ignore list")
@click.option("-i", "index", is_flag=True, help="Remove word by index in previous run")
@click.argument("values", nargs=-1)
def unignore(strings, files, dirs, types, index, values):
    if index:
        indices = [int(s) for s in values]
        values = _load_last_matches(indices)
    entry_type = _select_entry_type(strings, files, dirs, types, index)
    _edit_ignore_entries(entry_type, mode=MODE.SUBTRACT, values=list(values))


if __name__ == "__main__":
    cli()
