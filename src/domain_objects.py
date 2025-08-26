from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import List


def _sub(l1, l2):
    return [x for x in l1 if x not in l2]


@dataclass
class Match:
    path: Path
    match: str
    line: int = 0

    def __str__(self):
        return f"{self.path}:{self.line:0>3}: '{self.match}'"

    @property
    def sha(self):
        return sha256(self.match.encode("utf-8")).hexdigest()

    @property
    def file(self):
        return self.path.name

    def __len__(self):
        return len(self.match) + 4

    def render(self, length):
        return "." * (length - len(str(self.match))) + " '" + self.match + "'"

    def __eq__(self, other):
        return self.path == other.path and self.match == other.match

    def __hash__(self):
        return hash(self.path.name + self.match)


@dataclass
class IgnoreConfig:
    dirs: List[Path]
    files: List[Path]
    types: List[str]
    strings: List[bytes]

    def __add__(self, other):
        if not isinstance(other, IgnoreConfig):
            raise TypeError
        return IgnoreConfig(
            self.dirs + other.dirs,
            self.files + other.files,
            self.types + other.types,
            self.strings + other.strings,
        )

    def __sub__(self, other):
        if not isinstance(other, IgnoreConfig):
            raise TypeError
        return IgnoreConfig(
            _sub(self.dirs, other.dirs),
            _sub(self.files, other.files),
            _sub(self.types, other.types),
            _sub(self.strings, other.strings),
        )

    def to_dict(self):
        return self.__dict__
