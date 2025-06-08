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


def get_files(root):
    return [p for p in Path(root).rglob('*') if p.is_file()]


def should_scan(file):
    if file.suffix in ignored_suffixes:
        return False
    if file.name in ignored_names:
        return False
    for dir in ignored_dirs:
        if dir in file.parts:
            return False
    return True


def scan(filename):
    lines = open(filename, "r").readlines()
    match = False
    for i, line in enumerate(lines, start=1):
        for regex in regexes:
            if re.search(regex, line):
                print(f"{filename}:{i}: {line}")
                match = True
    return match


def scan_mmap(file_path):
    file_name = Path(file_path).name
    start = time.time()
    match = False
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
                match = True
    if matches:
        print(f"{file_name}: {len(matches)} {'matches' if len(matches) > 1 else 'match'}")
        for match in matches:
            print(f"  - {match}")

    if time.time() - start > 1:
        print(f"file {file_name} took {round(time.time() - start, 4)} seconds")
    return match


def main():
    start = time.time()
    # root = sys.argv[1]
    root = "/Users/danylewin/thingies/university/CS Workshop/SecretSearcher"
    files = get_files(root)
    match = False
    for file in files:
        if not should_scan(file):
            continue
        # print(file)
        try:
            if scan_mmap(file):
                match = True
        except Exception as e:
            print(f"Failed to scan {file}")
            print(e)
    print(f"ran for {time.time() - start} seconds")
    if match:
        print("Found at least one suspected secret!")
        exit(1)
    else:
        print("Everything looks good!")
        exit(0)
    # return files


if __name__ == '__main__':
    x = main()
