import mmap
import re
import sys
import time
from pathlib import Path

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

ignored_names = [".DS_Store", "noise.txt"]
ignored_suffixes = [".pyc", ".pack", ".pkl"]
ignored_dirs = [".git", ".idea", ".venv"]


def should_scan(file):
    if file.suffix in ignored_suffixes:
        return False
    if file.name in ignored_names:
        return False
    for dir in ignored_dirs:
        if dir in file.parts:
            return False
    return True


def scan(file_path):
    file_name = Path(file_path).name
    matches = []
    with open(file_path, "r+") as f:
        try:
            data = mmap.mmap(f.fileno(), 0)
        except ValueError as e:
            if e.args[0] == 'cannot mmap an empty file':
                return False
        for regex in regexes:
            if mo := re.search(regex, data):
                matches.append(mo.group().decode("utf-8"))
    if matches:
        print(f"{file_name}: {len(matches)} {'matches' if len(matches) > 1 else 'match'}")
        for match in matches:
            print(f"  - {match}")

    return bool(matches)


def main():
    start = time.time()
    files = [Path(f) for f in sys.argv[1:]]
    match = False
    for file in files:
        if not should_scan(file):
            continue
        try:
            if scan(file):
                match = True
        except Exception as e:
            print(f"Failed to scan {file}")
            raise
    print(f"ran for {time.time() - start} seconds")
    if match:
        print("Found at least one suspected secret!")
        exit(1)


if __name__ == '__main__':
    x = main()
