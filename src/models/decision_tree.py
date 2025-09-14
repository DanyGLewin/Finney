import dataclasses
import pickle
import re
import time
from datetime import datetime
from itertools import combinations_with_replacement
from typing import Self

import numpy as np
import pandas as pd

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
    train_accuracy: float
    train_precision: float
    train_recall: float
    train_f1: float
    test_accuracy: float
    test_precision: float
    test_recall: float
    test_f1: float

    @staticmethod
    def avg(scores: list['Self']):
        return Score(
            eta=scores[0].eta,
            n_estimators=scores[0].n_estimators,
            max_depth=scores[0].max_depth,
            samples=scores[0].samples,
            train_accuracy=sum([sc.train_accuracy for sc in scores]) / len(scores),
            train_precision=sum([sc.train_precision for sc in scores]) / len(scores),
            train_recall=sum([sc.train_recall for sc in scores]) / len(scores),
            train_f1=sum([sc.train_f1 for sc in scores]) / len(scores),
            test_accuracy=sum([sc.test_accuracy for sc in scores]) / len(scores),
            test_precision=sum([sc.test_precision for sc in scores]) / len(scores),
            test_recall=sum([sc.test_recall for sc in scores]) / len(scores),
            test_f1=sum([sc.test_f1 for sc in scores]) / len(scores),
        )

    def __str__(self):
        return f"{self.eta},{self.n_estimators},{self.max_depth},{self.samples},{self.train_accuracy},{self.test_accuracy},{self.train_precision},{self.test_precision},{self.train_recall},{self.test_recall},{self.train_f1},{self.test_f1}"


def make_tree(word_features: pd.DataFrame, samples: int, eta: float, max_depth: int, n_estimators: int,
              save: bool = True):
    import xgboost as xgb
    from sklearn.metrics import (
        accuracy_score,
        precision_score,
        recall_score,
        f1_score,
        confusion_matrix
    )
    from sklearn.model_selection import train_test_split

    texts_train, texts_test, X_train, X_test, y_train, y_test = train_test_split(
        texts, word_features, labels, test_size=0.2, random_state=42
    )

    clf = xgb.XGBClassifier(max_depth=max_depth, n_estimators=n_estimators, eta=eta)

    clf = clf.fit(np.array(X_train), np.array(y_train))  # train the model

    y_train = np.array(y_train)
    train_preds = clf.predict(X_train)
    train_accuracy = accuracy_score(y_train > 0, train_preds > 0)
    train_precision = precision_score(y_train > 0, train_preds > 0, average="macro")
    train_recall = recall_score(y_train > 0, train_preds > 0, average="macro")
    train_f1 = f1_score(y_train > 0, train_preds > 0, average="macro")

    confusion = confusion_matrix(y_train, train_preds)
    print(confusion)


    y_test = np.array(y_test)
    test_preds = clf.predict(X_test)
    test_accuracy = accuracy_score(y_test > 0, test_preds > 0)
    test_precision = precision_score(y_test > 0, test_preds > 0, average="macro")
    test_recall = recall_score(y_test > 0, test_preds > 0, average="macro")
    test_f1 = f1_score(y_test > 0, test_preds > 0, average="macro")

    confusion = confusion_matrix(y_test, test_preds)
    print(confusion)

    score = Score(
        eta=eta,
        max_depth=max_depth,
        n_estimators=n_estimators,
        samples=samples,
        train_accuracy=train_accuracy,
        train_precision=train_precision,
        train_recall=train_recall,
        train_f1=train_f1,
        test_accuracy=test_accuracy,
        test_precision=test_precision,
        test_recall=test_recall,
        test_f1=test_f1,
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

    # df = pd.DataFrame(texts_test)
    # df["y_true"] = y_test
    # df["y_pred"] = preds.astype(bool)
    # errors = df[df["y_true"] != df["y_pred"]]

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
    samples = 5_000_000

    now = datetime.now()
    print(f"[{now.hour:0>2}:{now.minute:0>2}:{now.second:0>2}] Starting to compute features")

    # df = pd.read_csv(
    #     "/Users/danylewin/thingies/university/CS Workshop/Finney/data/PassFInder_Password_Dataset/password_test.csv",
    #     header=None,
    #     names=["text", "label"],
    # ).sample(int(samples*1.01)).dropna().sample(samples)

    df = pd.read_csv(
        "/Users/danylewin/thingies/university/CS Workshop/Finney/data/PassFInder_Password_Dataset/password_test.csv",
        header=None,
        names=["text", "label"],
    ).dropna()

    texts = df["text"].astype(str).tolist() + short_words + snippet_words_df
    labels = df["label"].astype(int).tolist() + [0 for _ in short_words] + [0 for _ in snippet_words_df]
    # labels = [y > 0 for y in labels]

    texts = pd.DataFrame(texts, columns=["text"])
    word_features = get_features(texts)

    with open("src/models/features.pkl", "wb") as f:
        pickle.dump(word_features, f)
        time.sleep(0.5)

    now = datetime.now()
    print(f"[{now.hour}:{now.minute}:{now.second}] Finished computing features, starting run")

    with open("scores.csv", "a") as f:
        f.write(
            "eta,n_estimators,max_depth,samples,train_accuracy,train_precision,train_recall,train_f1,test_accuracy,test_precision,test_recall,test_f1\n")

    for eta in [0.05]:
        for max_depth in [15]:
            for n_estimators in [1000]:
                scores = []
                print(f"Running for {n_estimators=} {max_depth=} {eta=} {samples=}", end=" ")
                start = datetime.now()
                for i in range(1):
                    print(i + 1, end=" ")
                    scores.append(make_tree(
                        word_features=word_features,
                        eta=eta,
                        max_depth=max_depth,
                        n_estimators=n_estimators,
                        samples=samples,
                        save=True,
                    ))
                    avg = Score.avg(scores)
                    with open("scores.csv", "a") as f:
                        f.write(str(avg) + "\n")
                print(f"took: {datetime.now() - start}")
