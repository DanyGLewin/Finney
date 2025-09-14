import re
from collections import defaultdict

import numpy as np
import pandas as pd

english_words = set()
with open("data/words.txt", "r") as f:
    for line in f.readlines():
        english_words.add(line.strip().casefold())
temp = "|".join(map(re.escape, english_words))
english_pattern = re.compile(rf"\b(?:{temp})\b")

keywords = set()
with open("data/keywords.txt", "r") as f:  # taken from https://github.com/e3b0c442/keywords?tab=readme-ov-file
    for line in f.readlines():  # and from https://www.ibm.com/docs/en/i/7.6.0?topic=extensions-standard-c-library-functions-table-by-name
        keywords.add(line.strip().casefold())
temp = "|".join(map(re.escape, keywords))
keyword_pattern = re.compile(rf"\b(?:{temp})\b")

extensions = set()  # taken from https://gist.github.com/securifera/e7eed730cbe1ce43d0c29d7cd2d582f4
with open("data/extensions.txt", "r") as f:
    for line in f.readlines():
        extensions.add(line.strip().casefold())
temp = "|".join(map(re.escape, extensions))
file_type_pattern = re.compile(rf"(?:{temp})$")

domains = set()  # taken from https://github.com/datasets/top-level-domain-names/blob/main/data/top-level-domain-names.csv?plain=1
with open("data/domains.txt", "r") as f:
    for line in f.readlines():
        domains.add(line.strip().casefold())
temp = "|".join(map(re.escape, domains))
url_pattern = re.compile(rf"(?:{temp})\b")

key_distances = pd.read_csv("data/bigrams.csv", index_col=0).to_numpy()
key_index = {ch: i for i, ch in enumerate("!@#$%^&*()_+1234567890-=qwertyuiop[]{}asdfghjkl;'\\:\"|~zxcvbnm,./<>?)}")}

character_type_map = defaultdict(int)
for c in "abcdefghijklmnopqrstuvwxyz":
    character_type_map[c] = 1
for c in "0123456789":
    character_type_map[c] = 2


def extract_bigrams(word: str) -> list[tuple[str, str]]:
    if len(word) < 2:
        return []
    word = word.lower().strip()
    return list(zip(word, word[1:]))


def avg_key_distance(bigrams: list[tuple[str, str]]) -> np.float32:
    total_distance = np.float32(0)
    if not bigrams:
        return total_distance
    for bigram in bigrams:
        c1, c2 = bigram
        if c1 not in key_index or c2 not in key_index:
            continue
        total_distance += key_distances[key_index[c1]][key_index[c2]]  # type: ignore
    return total_distance / len(bigrams)


def count_type_switches(bigrams: list[tuple[str, str]]) -> int:
    switch_count = 0
    for bigram in bigrams:
        c1, c2 = bigram
        switch_count += character_type_map[c1] != character_type_map[c2]
    return switch_count


def extract_trigrams(word: str) -> list[tuple[str, str, str]]:
    if len(word) < 3:
        return []
    word = word.lower().strip()
    return list(zip(word, word[1:], word[2:]))


def has_consecutive_sequence(trigrams: list[tuple[str, str, str]]) -> bool:
    for trigram in trigrams:
        c1, c2, c3 = trigram
        if abs(ord(c1) - ord(c2)) == 1 and ord(c1) - ord(c2) == ord(c2) - ord(c3):
            return True
    return False


def get_features(df: pd.DataFrame) -> pd.DataFrame:
    out = pd.DataFrame()

    # contains special character
    out["special"] = df["text"].str.contains("[!@#\$\^\&\*\(\)_\+\[\]'\"\;\/\,\>\<\\\|\{\}\?\.]", regex=True)

    # ends with special character
    out["special_end"] = df["text"].str.contains("[^a-zA-Z0-9]$", regex=True)

    # starts with uppercase
    out["upper_start"] = df["text"].str.contains("^[A-Z]", regex=True)

    # contains a space
    # df["space"] = df["text"].str.contains(" ")

    # is entirely hexadecimal, with at least one non-digit character
    out["all_hexa"] = df["text"].str.contains("^[0-9A-Fa-f]*[A-Fa-f][0-9A-Fa-f]*$", regex=True)

    # contains escaped byte (e.g. for urls)
    out["byte"] = df["text"].str.contains(r"\\{1,2}\w{3,4}(?!\w)", regex=True)

    # starts with one of . .. ./ ../ like a relative path path
    out["path_sub"] = df["text"].str.contains(r"(?:^/\./)|(?:^\./)", regex=True)
    out["path_relative"] = df["text"].str.contains(r"(?:^/\.\./)|(?:^\.\./)", regex=True)

    # is of common password format: [letters][numbers][symbol] or [letters][symbol][number]
    out["letter_number_symbol"] = df["text"].str.contains(r"^[A-Za-z]+[0-9]+\W?$", regex=True)
    out["letter_symbol_number"] = df["text"].str.contains(r"^[A-Za-z]+\W?[0-9]+$", regex=True)

    # contains a number of a recent or upcoming year (1900-2100), or a date formatted YYYY-MM-DD
    out["year"] = df["text"].str.contains(r"\b(?:19[0-9]{2}|20[0-9]{2}|2100)\b", regex=True)
    out["date"] = df["text"].str.contains(r"\d{4}-\d{2}-\d{2}", regex=True)

    # contains an xml/html tag (e.g. <div>)
    out["xml"] = df["text"].str.contains(r"<.{1,3}>", regex=True)

    # contains specific special characters that are kinda common in code
    out["period"] = df["text"].str.contains("\.")
    out["double_colon"] = df["text"].str.contains("::")
    out["question"] = df["text"].str.contains("\?")
    out["percent"] = df["text"].str.contains("%")
    out["arrow"] = df["text"].str.contains("->")
    out["dunder"] = df["text"].str.contains("__")
    out["double_equal"] = df["text"].str.contains("==")
    out["triple_equal"] = df["text"].str.contains("===")
    out["double_slash"] = df["text"].str.contains("//")
    out["backslash"] = df["text"].str.contains("\\\\")
    out["double_backslash"] = df["text"].str.contains("\\\\\\\\")
    out["newline"] = df["text"].str.contains(r"\\n", regex=True)

    # contains an equal number of opening and closting parentheses of various types
    out["balanced_parentheses"] = (
            (df["text"].str.count(r"\(") == df["text"].str.count(r"\)")) &
            (df["text"].str.count(r"\(") > 0)
    )
    out["balanced_parentheses_square"] = (
            (df["text"].str.count(r"\[") == df["text"].str.count(r"\]")) &
            (df["text"].str.count(r"\[") > 0)
    )
    out["balanced_parentheses_curl"] = (
            (df["text"].str.count(r"\{") == df["text"].str.count(r"\}")) &
            (df["text"].str.count(r"\{") > 0)
    )

    # longest sequence of uppercase letters, vowels, consonants, and hexadecimal characters
    out["longest_upper"] = df["text"].apply(
        lambda x: max((len(m) for m in re.findall(r"[A-Z]+", str(x))), default=0)
    )
    out["longest_vowels"] = df["text"].apply(
        lambda x: max((len(m) for m in re.findall(r"[aeiouAEIOU]+", str(x))), default=0)
    )
    out["longest_cons"] = df["text"].apply(
        lambda x: max((len(m) for m in re.findall(r"[bcdfghjklmnpqrstvxzBCDFGHJKLMNPQRSTVXZ]+", str(x))), default=0)
    )
    out["longest_hexa"] = df["text"].apply(
        lambda x: max((len(m) for m in re.findall(r"[0-9A-Fa-f]*[A-Fa-f][0-9A-Fa-f]*", str(x))), default=0)
    )

    # fraction of the string that's digits, letters, and other
    out["digit_fraction"] = df["text"].apply(
        lambda x: sum(c.isdigit() for c in str(x)) / len(str(x))
    )
    out["vowel_fraction"] = df["text"].apply(
        lambda x: sum(c in set("aeiouAEIOU") for c in str(x)) / len(str(x))
    )
    out["nonword_fraction"] = df["text"].apply(
        lambda x: len(re.findall(r"\W", str(x))) / len(str(x))
    )

    # number of character sequences of length divisible by 4
    out["word_length_mod_4"] = df["text"].apply(
        lambda x: sum(1 for m in re.findall(r"\w+", str(x)) if len(m) % 4 == 0)
    )

    # whether the string is in a common programming style convention
    snake = r'^[A-Za-z]+(?:_[A-Za-z_]+)+$'
    pascal = r'^[A-Z][a-z]+(?:[A-Z][a-z]+)+$'  # UpperCamel
    camel = r'^[a-z]+(?:[A-Z][a-z]+)+$'  # lowerCamel
    kebab = r'^[A-Za-z]+(?:-[A-Za-z-]+)+$'  # kebab-like (at least one "-")
    allcaps = r'^[A-Z]+$'  # ALLCAPS

    conds = [
        df["text"].str.fullmatch(snake, na=False),
        df["text"].str.fullmatch(pascal, na=False),
        df["text"].str.fullmatch(camel, na=False),
        df["text"].str.fullmatch(kebab, na=False),
        df["text"].str.fullmatch(allcaps, na=False),
    ]
    out["format"] = np.select(conds, [1, 2, 3, 4, 5], default=0).astype(int)

    # whether the string contains an english word, and how many
    out["word"] = df["text"].astype(str).str.contains(english_pattern, na=False, regex=True)
    out["word_count"] = df["text"].astype(str).str.findall(english_pattern).str.len()

    # whether the string contains a programming keyword, and how many
    out["keyword"] = df["text"].astype(str).str.contains(keyword_pattern, na=False, regex=True)
    out["keyword_count"] = df["text"].astype(str).str.findall(keyword_pattern).str.len()

    # is a likely url
    out["likely_url"] = df["text"].astype(str).str.contains(url_pattern, na=False)

    # ends with known file suffix (e.g. .exe or .py)
    out["file_suffix"] = df["text"].astype(str).str.contains(url_pattern, na=False)

    # string length
    out["string_length"] = df["text"].astype(str).str.len()

    # split the word into bigrams (e.g. "bigram" -> [bi, ig, gr, ra, am])
    bigrams = df.text.map(lambda word: extract_bigrams(word))
    out["key_distances"] = list(map(avg_key_distance, bigrams))
    out["type_switches"] = list(map(count_type_switches, bigrams))

    # split the word into trigrams (e.g. "trigram" -> [tri, rig, igr, gra, ram])
    trigrams = df.text.map(lambda word: extract_trigrams(word))
    out["consecutive_sequence"] = list(map(has_consecutive_sequence, trigrams))

    # return tuple(features)
    return out
