import re
from pathlib import Path

from domain_objects import IgnoreConfig

regexes = [
    r"[1-9][0-9]+-[0-9a-zA-Z]{40}",
    r"EAACEdEose0cBA[0-9A-Za-z]+",
    r"AIza[0-9A-Za-z\-_]{35}",
    r"[0-9]+-[0-9A-Za-z_]{32}\.apps\.googleusercontent\.com",
    r"sk_live_[0-9a-z]{32}",
    r"sk_live_[0-9a-zA-Z]{24}",
    r"rk_live_[0-9a-zA-Z]{24}",
    r"sq0atp-[0-9A-Za-z\-_]{22}",
    r"sq0csp-[0-9A-Za-z\-_]{43}",
    r"access_token\$production\$[0-9a-z]{16}\$[0-9a-f]{32}",
    r"amzn\.mws\.[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    r"SK[0-9a-fA-F]{32}",
    r"key-[0-9a-zA-Z]{32}",
    r"[0-9a-f]{32}-us[0-9]{1,2}",
    r"AKIA[0-9A-Z]{16}",
    # CC number
    r"\b(?:4[0-9]{12}(?:[0-9]{3})?|[25][1-7][0-9]{14}|6(?:011|5[0-9][0-9])[0-9]{12}|3[47][0-9]{13}|3(?:0[0-5]|[68][0-9])[0-9]{11}|(?:2131|1800|35\d{3})\d{11})\b",
    # phone number
    r"\b\+((?:9[679]|8[035789]|6[789]|5[90]|42|3[578]|2[1-689])|9[0-58]|8[1246]|6[0-6]|5[1-8]|4[013-9]|3[0-469]|2[70]|7|1)(?:\W*\d){0,13}\d\b",
    # email
    r"(\b[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+\b)"
]


def scan(file_path: Path, ignored: IgnoreConfig) -> list[str]:
    matches = []
    with open(file_path, "r+") as f:
        try:
            data = f.read()
        except:
            return []
    for regex in regexes:
        if mo := re.search(regex, data):
            match_str = mo.group()
            if match_str in ignored.strings or "\n" in match_str:
                continue
            matches.append(match_str)
    return matches
