import mmap
import re
from hashlib import sha256
from pathlib import Path

from domain_objects import IgnoreConfig

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
    # CC number
    rb"^(?:4[0-9]{12}(?:[0-9]{3})?|[25][1-7][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|(?:2131|1800|35\d{3})\d{11})$",
    # phone number
    rb"^[+]{1}(?:[0-9\-\(\)\/\.]\s?){6, 15}[0-9]{1}$",
    # email
    # rb"(^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+$)"
]


def scan(file_path: Path, ignored: IgnoreConfig) -> list[str]:
    matches = []
    with open(file_path, "r+") as f:
        try:
            data = mmap.mmap(f.fileno(), 0)
        except ValueError as e:
            if e.args[0] == "cannot mmap an empty file":
                return []
        for regex in regexes:
            if mo := re.search(regex, data):
                match_bytes = mo.group()
                match_str = match_bytes.decode("utf-8")
                match_hash = sha256(match_bytes).hexdigest()
                if match_str in ignored.strings or match_hash in ignored.strings:
                    continue
                matches.append(match_str)
    return matches
