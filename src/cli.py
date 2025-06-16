import os
import pickle
from enum import Enum
from hashlib import sha256
from typing import Sequence

import click
import yaml

import search
from domain_objects import Match, IgnoreConfig

config_path = ".secrets/config"
last_matches_path = ".secrets/log"


class IGNORE_TYPES(Enum):
    HASHES = "HASHES"
    FILES = "FILES"
    DIRS = "DIRS"
    SUFFIXES = "SUFFIXES"


class EDIT_MODE(Enum):
    ADD = "ADD"
    SUBTRACT = "SUBTRACT"


def _load_ignore_config() -> IgnoreConfig:
    if not os.path.exists(config_path):
        return IgnoreConfig(dirs=[], files=[], suffixes=[], hashes=[])

    with open(config_path, "r") as f:
        config = yaml.safe_load(f) or {}

    config = config.get("ignore", {})
    return IgnoreConfig(
        dirs=config.get("dirs") or [],
        files=config.get("files") or [],
        suffixes=config.get("suffixes") or [],
        hashes=config.get("hashes") or [],
    )


def _add_ignore_entries(mode: IGNORE_TYPES, values: Sequence[str]) -> None:
    prev_config = _load_ignore_config()
    added_config = IgnoreConfig(
        dirs=values if mode == IGNORE_TYPES.DIRS else [],
        files=values if mode == IGNORE_TYPES.FILES else [],
        suffixes=values if mode == IGNORE_TYPES.SUFFIXES else [],
        hashes=values if mode == IGNORE_TYPES.HASHES else [],
    )
    combined = prev_config + added_config
    with open(config_path, "w+") as f:
        yaml.safe_dump(
            {"ignore": combined.to_dict()},
            f,
            indent=4,
            default_flow_style=False,
            sort_keys=False,
        )


def _save_last_matches(matches: Sequence[Match]) -> None:
    with open(last_matches_path, "wb+") as f:
        pickle.dump(matches, f)


@click.group()
def cli():
    pass


@cli.command()
@click.argument('paths', nargs=-1)
def run(paths):
    ignored = _load_ignore_config()
    matches: Sequence[Match] = search.scan_files(paths, ignored)
    if matches:
        for i, match in enumerate(matches, start=1):
            print(f"{i:>2} | {match}")
        _save_last_matches(matches)
        exit(1)


@cli.command("ignore")
@click.option('-f', 'files', is_flag=True, help='Add files to ignore list (default)')
@click.option('-d', 'dirs', is_flag=True, help='Add directories to ignore list')
@click.option('-s', 'suffixes', is_flag=True, help='Add file suffixes to ignore list')
@click.option('-h', 'string_hashes', is_flag=True, help='Add specific string hashes to ignore list')
@click.option('-i', 'interactive', is_flag=True, help='Interactive mode')
@click.argument('values', nargs=-1)
def ignore(files, dirs, suffixes, string_hashes, interactive, values):
    if sum([files, dirs, suffixes, string_hashes, interactive]) > 1:
        raise click.UsageError("Options -f, -d, -s, -h and -i are mutually exclusive")

    if interactive:
        if values:
            raise click.UsageError("You cannot pass values when using -i")
        raise NotImplementedError

    elif suffixes:
        mode = IGNORE_TYPES.SUFFIXES

    elif string_hashes:
        mode = IGNORE_TYPES.HASHES
        byte_values = [val.encode("utf-8") for val in values]
        values = [sha256(val).hexdigest() for val in byte_values]

    elif dirs:
        mode = IGNORE_TYPES.DIRS

    else:
        mode = IGNORE_TYPES.FILES

    _add_ignore_entries(mode, list(values))


@cli.command("reset")
@click.option('-f', 'files', is_flag=True, help='Add files to ignore list (default)')
@click.option('-d', 'dirs', is_flag=True, help='Add directories to ignore list')
@click.option('-s', 'suffixes', is_flag=True, help='Add file suffixes to ignore list')
@click.option('-h', 'string_hashes', is_flag=True, help='Add specific string hashes to ignore list')
@click.option('-i', 'interactive', is_flag=True, help='Interactive mode')
@click.argument('values', nargs=-1)
def reset(files, dirs, suffixes, string_hashes, interactive, values):
    raise NotImplementedError


if __name__ == '__main__':
    cli()
