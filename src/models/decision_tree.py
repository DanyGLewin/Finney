import dataclasses
import pickle
import re
import time
from datetime import datetime
from itertools import combinations_with_replacement
from typing import Self

import numpy as np
import pandas as pd
import xgboost as xgb
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
)
from sklearn.model_selection import train_test_split

from models.features import get_features

candidate_pattern = r"""(["'`])[a-zA-Z0-9&*!?.\-_#%@^&$"'`{} ()\[\]]{6,30}\1"""


def extract_candidates_from_file(path) -> pd.DataFrame:
    with open(path, "r") as f:
        candidates = []
        for line in f.readlines():
            if match := re.search(candidate_pattern, line):
                candidates.append(match.group()[1:-1])
    return pd.DataFrame(candidates, columns=["text"])


alphabet = list("abcdefghijklmnopqrstuvwxyz")
short_words = alphabet + ["".join(x) for x in combinations_with_replacement(alphabet, 2)]

snippet_words_df = list(pd.read_csv("data/context_words.csv"))


@dataclasses.dataclass
class Score:
    eta: float
    n_estimators: int
    max_depth: int
    samples: int
    accuracy: float
    precision: float
    recall: float
    f1: float

    @staticmethod
    def avg(scores: list['Self']):
        return Score(
            eta=scores[0].eta,
            n_estimators=scores[0].n_estimators,
            max_depth=scores[0].max_depth,
            samples=scores[0].samples,
            accuracy=sum([sc.accuracy for sc in scores]) / len(scores),
            precision=sum([sc.precision for sc in scores]) / len(scores),
            recall=sum([sc.recall for sc in scores]) / len(scores),
            f1=sum([sc.f1 for sc in scores]) / len(scores),
        )

    def __str__(self):
        return f"{self.eta},{self.n_estimators},{self.max_depth},{self.samples},{self.accuracy},{self.precision},{self.recall},{self.f1}"


def make_tree(samples: int, eta: float, max_depth: int, n_estimators: int, save: bool = True):
    df = pd.read_csv(
        "/Users/danylewin/thingies/university/CS Workshop/Finney/data/PassFInder_Password_Dataset/password_test.csv",
        header=None,
        names=["text", "label"],
    ).sample(samples)
    texts = df["text"].astype(str).tolist() + short_words + snippet_words_df
    labels = df["label"].astype(int).tolist() + [0 for _ in short_words] + [0 for _ in snippet_words_df]
    labels = [y > 0 for y in labels]

    texts = pd.DataFrame(texts, columns=["text"])
    word_features = get_features(texts)

    texts_train, texts_test, X_train, X_test, y_train, y_test = train_test_split(
        texts, word_features, labels, test_size=0.2
    )

    clf = xgb.XGBClassifier(max_depth=max_depth, n_estimators=n_estimators, eta=eta)

    clf = clf.fit(np.array(X_train), np.array(y_train))  # train the model

    y_test = np.array(y_test)
    preds = clf.predict(X_test)
    accuracy = accuracy_score(y_test > 0, preds > 0)
    precision = precision_score(y_test > 0, preds > 0, average="macro")
    recall = recall_score(y_test > 0, preds > 0, average="macro")
    f1 = f1_score(y_test > 0, preds > 0, average="macro")

    score = Score(
        eta=eta,
        max_depth=max_depth,
        n_estimators=n_estimators,
        samples=samples,
        accuracy=accuracy,
        precision=precision,
        recall=recall,
        f1=f1,
    )
    # print("Performance metrics:")
    # print(f"  {accuracy}")
    # print(f"  {precision}")
    # print(f"  {recall}")
    # print(f"  {f1}")

    if save:
        with open("src/models/tree.pkl", "wb") as f:
            pickle.dump(clf, f)
            time.sleep(0.5)

    df = pd.DataFrame(texts_test)
    df["y_true"] = y_test
    df["y_pred"] = preds.astype(bool)
    errors = df[df["y_true"] != df["y_pred"]]

    return score


def predict(words):
    with open("src/models/tree.pkl", "rb") as f:
        tree = pickle.load(f)
    words = pd.DataFrame(words)
    word_features = get_features(words)
    res = tree.predict_proba(word_features)
    return res


def clean_results(pred_weights, threshold):
    cond1 = pred_weights[:, 0] < threshold
    cond2 = pred_weights[:, 0] != pred_weights.max(axis=1)
    mask = cond1 & cond2
    indices = np.where(mask)[0].tolist()
    return indices


def scan(path, threshold=0.2):
    # try:
    candidates = extract_candidates_from_file(path)
    # except:
    # return []
    if not len(candidates.index):
        return []
    pred_weights = predict(candidates)
    results = clean_results(pred_weights, threshold)

    return [candidates.loc[i].text for i, guess in enumerate(results) if guess]


if __name__ == "__main__":
    with open("scores.csv", "a") as f:
        f.write("eta,n_estimators,max_depth,samples,accuracy,precision,recall,f1\n")
    for eta in [0.02]:
        for max_depth in [15]:
            for n_estimators in [1000]:
                scores = []
                samples = 1_000_000
                print(f"Running for {n_estimators=} {max_depth=} {eta=} {samples=}", end=" ")
                start = datetime.now()
                for i in range(1):
                    print(i + 1, end=" ")
                    scores.append(make_tree(
                        eta=eta,
                        max_depth=max_depth,
                        n_estimators=n_estimators,
                        samples=samples,
                    ))
                    avg = Score.avg(scores)
                    with open("scores.csv", "a") as f:
                        f.write(str(avg) + "\n")
                print(f"took: {datetime.now() - start}")
