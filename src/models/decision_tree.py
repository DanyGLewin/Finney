import math
import pickle
import re
import string
import time
from datetime import datetime
from itertools import combinations_with_replacement

import pandas as pd
from dateutil import parser
from sklearn import tree, ensemble
from sklearn.metrics import (
    accuracy_score,
    confusion_matrix,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.model_selection import train_test_split

candidate_pattern = r"""(["'`])[a-zA-Z0-9&*!?.\-_#%@^&$"'`{} ()\[\]]+\1"""

# Define coordinates for QWERTY keyboard keys
# Approximate positions:
# Row 1 (y=0): q to p at x=0..9
# Row 2 (y=1): a to l at x=0.5..8.5
# Row 3 (y=2): z to m at x=1.25..7.25

key_positions = {}
# Row 0
row0 = "1234567890-=_+"
for i, key in enumerate(row0):
    key_positions[key] = (i - 0.5, -1)

# Row 1
row1 = "qwertyuiop[]{}"
for i, key in enumerate(row1):
    key_positions[key] = (i, 0)

# Row 2
row2 = "asdfghjkl;'\\:\"|"
for i, key in enumerate(row2):
    key_positions[key] = (i + 0.5, 1)

# Row 3
row3 = "zxcvbnm,./<>?"
for i, key in enumerate(row3):
    key_positions[key] = (i + 1.25, 2)


def average_key_distance(input_string: str) -> float:
    coords = []
    for char in input_string.lower():
        if char in key_positions:
            coords.append(key_positions[char])

    if len(coords) < 2:
        return 0.0

    distances = []
    for (x1, y1), (x2, y2) in zip(coords, coords[1:]):
        dist = math.hypot(x2 - x1, y2 - y1)
        distances.append(dist)

    return sum(distances) / len(distances)


def has_consecutive_sequence(s: str, seq_len: int = 3) -> bool:
    s_lower = s.lower()
    n = len(s_lower)

    for i in range(n - seq_len + 1):
        substr = s_lower[i : i + seq_len]

        # all letters?
        if all(ch in string.ascii_lowercase for ch in substr):
            if all(
                ord(substr[j + 1]) - ord(substr[j]) in (1, -1) for j in range(seq_len - 1)
            ):
                return True

        # all digits?
        if all(ch.isdigit() for ch in substr):
            if all(
                int(substr[j + 1]) - int(substr[j]) in (1, -1) for j in range(seq_len - 1)
            ):
                return True

    return False


sonority = {
    "a": 10,
    "b": 4,
    "c": 3,
    "d": 4,
    "e": 10,
    "f": 5,
    "g": 4,
    "h": 9,
    "i": 10,
    "j": 4,
    "k": 3,
    "l": 8,
    "m": 7,
    "n": 7,
    "o": 10,
    "p": 3,
    "q": 3,
    "r": 8,
    "s": 5,
    "t": 3,
    "u": 10,
    "v": 6,
    "w": 9,
    "x": 3,
    "y": 10,
    "z": 6,
}

alphabet = list("abcdefghijklmnopqrstuvwxyz")
short_words = alphabet + ["".join(x) for x in combinations_with_replacement(alphabet, 2)]

snippet_words_df = list(pd.read_csv("data/context_words.csv"))

english_words = set()

with open("data/words.txt", "r") as f:
    for line in f.readlines():
        english_words.add(line.strip().casefold())

def get_vowel_indices(word: str) -> list[int]:
    indices = []
    for i, c in enumerate(word.lower()):
        if c in "aeiou":
            indices.append(i)
    return indices


def check_vowel_context(word: str, index) -> int:
    # Left context: max 2 chars, but not before start
    left_context = word[max(0, index - 2) : index]
    # Right context: up to 2 chars, slicing handles end-of-word
    right_context = word[index + 1 : index + 3]

    violations = 0

    if len(left_context) > 1:
        if left_context[0] in "aeiouy" or left_context[1] in "aeiouy":
            ...
        elif (
            index == 2 and left_context[0] == "s"
        ):  # s is allways allowed to start an onset in english
            ...
        elif (
            sonority[left_context[1]] < sonority[left_context[0]]
        ):  # "rka" is bad "kra" is good
            violations += 1

    if len(right_context) > 1:
        if right_context[0] in "aeiouy" or right_context[1] in "aeiouy":
            ...
        elif right_context in ("ch", "ph", "gh", "th"):  # digraphs are allowed too
            ...
        elif sonority[right_context[1]] > sonority[right_context[0]]:
            violations += 1
    return violations


def check_ssg(word: str) -> int:
    vowel_indices = get_vowel_indices(word)
    violations = 0
    for index in vowel_indices:
        violations += check_vowel_context(word, index)
    return violations


def follows_ssg(s: str) -> int:
    s = s.lower()
    words = re.findall(r"[a-z]+", s)
    violations = 0
    for word in words:
        word = re.sub(r"[aeiou]+", "a", word)
        violations += check_ssg(word)
    return violations


def extract_candidates_from_file(path):
    with open(path, "r") as f:
        candidates = []
        for line in f.readlines():
            if match := re.search(candidate_pattern, line):
                candidates.append(match.group()[1:-1])
    return candidates


def get_features(s: str) -> tuple[float | bool, ...]:
    features = []

    # contains special character
    for c in "!@#$%^&*()_+[]'\";/.,?><\\|{}":
        if c in s:
            features.append(True)
            break
    else:
        features.append(False)

    features.append(len(s))
    features.append(len(s) > 4)
    features.append(len(s) > 8)
    features.append(len(s) > 16)
    features.append(len(s) > 32)

    # starts with capital letter
    if s[0] in "ABCDEFGHIJKLMNOPQRSTUVWXYZ":
        features.append(True)
    else:
        features.append(False)

    # is all capslock
    if re.match("[^A-Z]", s):
        features.append(False)
    else:
        features.append(True)

    # longest capital sequence
    caps = re.findall(r"[A-Z]+", s) or [""]
    longest = max([len(x) for x in caps])
    features.append(longest)

    # longest vowel sequence
    caps = re.findall(r"[aeiou]+", s.lower()) or [""]
    longest = max([len(x) for x in caps])
    features.append(longest / len(s))

    # longest consonant sequence
    caps = re.findall(r"[bcdfghjklmnpqrstvwxyz]+", s.lower()) or [""]
    longest = max([len(x) for x in caps])
    features.append(longest / len(s))

    # ends with special character
    if s[-1].lower() not in "abcdefghijklmnopqrstuvwxyz0123456789":
        features.append(True)
    else:
        features.append(False)

    # fraction of the string that's digits
    digits = len(re.findall(r"\d", s))
    features.append(digits / len(s))

    # fraction of the string that's vowels
    vowels = len(re.findall(r"[aeiou]", s.lower()))
    features.append(vowels / len(s))

    # is entirely hexadecimal
    if re.match(r"^[0-9a-fA-F]+$", s):
        features.append(True)
    else:
        features.append(False)

    # longest hexadecimal sequence
    hexas = re.findall(r"[0-9a-fA-F]+", s) or [""]
    longest = max([len(x) for x in hexas])
    features.append(longest)

    # number of alphanumeric sequences of length divisible by 4
    segments = re.findall(r"[0-9a-zA-Z]+", s) or [""]
    number_of_fours = len([1 for x in segments if len(x) % 4 == 0])
    features.append(number_of_fours)

    # fraction of the string that's symbols
    symbols = len(re.findall(r"\W", s))
    features.append(symbols / len(s))
    # see if there's any symbols at all
    features.append(symbols > 0)

    # is made up of words split by underscores
    if re.match(r"[a-zA-Z]+(_[a-zA-Z_]+)+", s):
        features.append(True)
    else:
        features.append(False)

    # has escaped characters
    if re.match(r"\\{2}\w{3,4}(?!\w)", s):
        features.append(True)
    else:
        features.append(False)

    # has \n
    if re.match(r"\\n", s):
        features.append(True)
    else:
        features.append(False)

    # has file path characters
    if re.match(r"/\.", s) or re.match(r"\./", s):
        features.append(True)
    else:
        features.append(False)

    # has file path characters
    if re.match(r"/\.\.", s) or re.match(r"\.\./", s):
        features.append(True)
    else:
        features.append(False)

    # is of format [letters][numbers][symbol] or [letters][symbol][numbers]
    if re.match(r"[A-Za-z]+[0-9]+\W?", s):
        features.append(True)
    else:
        features.append(False)

    if re.match(r"[A-Za-z]+\W?[0-9]+", s):
        features.append(True)
    else:
        features.append(False)

    # contains a birth year
    for group in re.findall(r"\d{4}", s):
        if 1900 < int(group) < 2100:
            features.append(True)
            break
    else:
        features.append(False)

    if re.match(r"\d{4}-\d{2}-\d{2}", s):
        features.append(True)
    else:
        features.append(False)

    # contains a real word
    real_words_contained = 0
    for word in english_words:
        if word in s.casefold():
            real_words_contained += 1
    features.append(real_words_contained)

    # is a real word
    if s.casefold() in english_words:
        features.append(True)
    else:
        features.append(False)

    # check SSG
    # features.append(follows_ssg(s))

    # key distance
    features.append(average_key_distance(s))

    # consecutive letters
    features.append(has_consecutive_sequence(s))

    return tuple(features)


def make_tree():
    df = pd.read_csv(
        "/Users/danylewin/thingies/university/CS Workshop/SecretSearcher/data/PassFInder_Password_Dataset/password_test.csv",
        header=None,
        names=["text", "label"],
    ).sample(100000)
    texts = df["text"].astype(str).tolist() + short_words + snippet_words_df
    labels = df["label"].astype(int).tolist() + [0 for _ in short_words] + [0 for _ in snippet_words_df]
    # labels = [y > 0 for y in labels]

    start = datetime.now()
    print(
        f"Starting to parse features at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    features = [get_features(text) for text in texts]
    print(
        f"Finished parsing features at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )
    print(f"Took {datetime.now() - start}")

    texts_train, texts_test, X_train, X_test, y_train, y_test = train_test_split(
        texts, features, labels, test_size=0.2, random_state=42
    )

    train_start = datetime.now()
    print(f"Starting to train model at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    # clf = tree.DecisionTreeClassifier()
    clf = ensemble.RandomForestClassifier(n_estimators=200)

    clf = clf.fit(X_train, y_train)  # train the model
    print(f"Finished training model at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Took {datetime.now() - train_start}")

    preds = clf.predict(X_test)
    accuracy = accuracy_score(y_test, preds)
    precision = precision_score(y_test, preds, average="macro")
    recall = recall_score(y_test, preds, average="macro")
    f1 = f1_score(y_test, preds, average="macro")
    print("Performance metrics:")
    print(f"  Accuracy: {accuracy}")
    print(f"  Precision: {precision}")
    print(f"  Recall: {recall}")
    print(f"  F1: {f1}")

    with open("src/models/tree.pkl", "wb") as f:
        pickle.dump(clf, f)

    df = pd.DataFrame(texts_test)
    df["y_true"] = y_test
    df["y_pred"] = preds
    errors = df[df["y_true"] != df["y_pred"]]

    return errors, confusion_matrix(df["y_true"], df["y_pred"])


def predict(words):
    with open("src/models/tree.pkl", "rb") as f:
        tree = pickle.load(f)
    res = tree.predict([get_features(word) for word in words])
    return res


def scan(path):
    candidates = extract_candidates_from_file(path)
    preds = predict(candidates)
    return [candidates[i] for i, guess in enumerate(preds) if guess]


if __name__ == "__main__":
    errors, confusion_matrix = make_tree()
    print(errors)
    print(confusion_matrix)
