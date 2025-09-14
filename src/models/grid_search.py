import pickle
import time
from itertools import combinations_with_replacement

import pandas as pd
from sklearn.metrics import confusion_matrix
from sklearn.model_selection import GridSearchCV, train_test_split
import xgboost as xgb

from models.features import get_features

alphabet = list("abcdefghijklmnopqrstuvwxyz")
short_words = alphabet + ["".join(x) for x in combinations_with_replacement(alphabet, 2)]

snippet_words_df = list(pd.read_csv("data/context_words.csv"))


def run_grid_search():
    samples = 10_000
    param_grid = {
        "eta": [0.01, 0.1, 0.2, 0.3, 0.4, 0.5],
        "max_depth": [5, 10, 15, 20, 25],
        "n_estimators": [100, 500, 1000, 2000],
    }

    df = pd.read_csv(
        "/Users/danylewin/thingies/university/CS Workshop/Finney/data/PassFInder_Password_Dataset/password_test.csv",
        header=None,
        names=["text", "label"],
    ).sample(samples)
    texts = df["text"].astype(str).tolist() + short_words + snippet_words_df
    labels = df["label"].astype(int).tolist() + [0 for _ in short_words] + [0 for _ in snippet_words_df]
    # labels = [y > 0 for y in labels]

    texts = pd.DataFrame(texts, columns=["text"])
    word_features = get_features(texts)

    texts_train, texts_test, X_train, X_test, y_train, y_test = train_test_split(
        texts, word_features, labels, test_size=0.2)

    clf = xgb.XGBClassifier(random_state=42)

    # def confusion_matrix_scorer(clf, X, y):
    #     y_pred = clf.predict(X)
    #     cm = confusion_matrix(y, y_pred)
    #     return {'tn1': cm[0, 0], 'fp1': cm[0, 1], 'fp2': cm[0,2],
    #             'fn1': cm[1, 0], 'tp1': cm[1, 1], 'tp2': cm[1,2],
    #             'fn2': cm[2, 0], 'tp3': cm[2, 1], 'tp4': cm[2,2]}

    grid_search = GridSearchCV(estimator=clf, param_grid=param_grid, cv=3, n_jobs=-1, verbose=2,
                                         scoring="f1", return_train_score=True).fit(X_train, y_train)
    # grid_search_recall = GridSearchCV(estimator=clf, param_grid=param_grid, cv=3, n_jobs=-1, verbose=2,
    #                                   scoring=confusion_matrix_scorer, return_train_score=True).fit(X_train, y_train)

    with open("src/models/grid_search.pkl", "wb") as f:
        pickle.dump(grid_search, f)
    time.sleep(0.5)

    print("done?")

if __name__ == "__main__":
    run_grid_search()
