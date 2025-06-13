import pickle
from typing import Sequence

import click
import yaml

import search
from domain_objects import Match, IgnoreConfig

config_path = ".secretsignore"
last_matches_path = ".secretslog"


def load_ignore_config() -> IgnoreConfig:
    with open(config_path, "rb") as f:
        config = yaml.safe_load(f)

    return IgnoreConfig(
        dirs=config["dirs"],
        files=config["files"],
        suffixes=config["suffixes"],
        hashes=config["hashes"],
    )


def save_last_matches(matches: Sequence[Match]) -> None:
    with open(last_matches_path, "wb+") as f:
        pickle.dump(matches, f)


@click.command
@click.argument("paths", nargs=-1)
def cli(paths):
    ignored = load_ignore_config()
    matches: Sequence[Match] = search.scan_files(paths, ignored)
    if matches:
        for match in matches:
            print(match)
        save_last_matches(matches)
        exit(1)


if __name__ == '__main__':
    cli()
