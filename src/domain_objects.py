from dataclasses import dataclass
from hashlib import sha256
from pathlib import Path
from typing import List


def _sub(l1, l2):
    return [x for x in l1 if x not in l2]


@dataclass
class Match:
    path: Path
    match: bytes

    def __str__(self):
        return f"{self.path}: '{self.match.decode("utf-8")}'"

    @property
    def sha(self):
        return sha256(self.match).hexdigest()

    @property
    def file(self):
        return self.path.name


@dataclass
class IgnoreConfig:
    dirs: List[Path]
    files: List[Path]
    suffixes: List[str]
    hashes: List[bytes]

    def __add__(self, other):
        if not isinstance(other, IgnoreConfig):
            raise TypeError
        return IgnoreConfig(
            self.dirs + other.dirs,
            self.files + other.files,
            self.suffixes + other.suffixes,
            self.hashes + other.hashes
        )

    def __sub__(self, other):
        if not isinstance(other, IgnoreConfig):
            raise TypeError
        return IgnoreConfig(
            _sub(self.dirs, other.dirs),
            _sub(self.files, other.files),
            _sub(self.suffixes, other.suffixes),
            _sub(self.hashes, other.hashes),
        )

    def to_dict(self):
        return self.__dict__
