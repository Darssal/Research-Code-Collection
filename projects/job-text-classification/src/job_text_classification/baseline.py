"""Character TF-IDF + random forest, fitted only on training records."""

from __future__ import annotations

from pathlib import Path

from . import LABELS
from .data import Record, public_prediction


class RandomForestBaseline:
    def __init__(self, seed: int = 42, n_estimators: int = 100):
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import Pipeline

        self.pipeline = Pipeline([
            ("tfidf", TfidfVectorizer(analyzer="char", ngram_range=(2, 4), max_features=5000)),
            ("classifier", RandomForestClassifier(n_estimators=n_estimators, random_state=seed, n_jobs=1)),
        ])

    def fit(self, records: list[Record]) -> "RandomForestBaseline":
        if not records or any(record.label not in LABELS for record in records):
            raise ValueError("Training requires non-empty, labelled records")
        self.pipeline.fit([record.text for record in records], [record.label for record in records])
        return self

    def predict(self, records: list[Record]) -> list[dict]:
        if not records:
            return []
        texts = [record.text for record in records]
        predictions = self.pipeline.predict(texts)
        probabilities = self.pipeline.predict_proba(texts)
        classes = list(self.pipeline.named_steps["classifier"].classes_)
        rows = []
        for record, prediction, values in zip(records, predictions, probabilities):
            by_label = {label: float(value) for label, value in zip(classes, values)}
            rows.append(public_prediction(
                record, str(prediction), status="ok",
                probabilities={label: by_label.get(label, 0.0) for label in LABELS},
            ))
        return rows

    def save(self, path: str | Path) -> None:
        import joblib

        destination = Path(path)
        destination.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, destination)

    @classmethod
    def load(cls, path: str | Path) -> "RandomForestBaseline":
        """Load only artifacts that you generated or otherwise trust."""
        import joblib

        model = joblib.load(path)
        if not isinstance(model, cls):
            raise ValueError("The artifact is not a RandomForestBaseline")
        return model


def classification_metrics(records: list[Record], rows: list[dict]) -> dict:
    from sklearn.metrics import accuracy_score, classification_report, confusion_matrix

    if not records or len(records) != len(rows):
        raise ValueError("Metrics require equally sized, non-empty record and prediction lists")
    if any(record.record_id != row.get("record_id") for record, row in zip(records, rows)):
        raise ValueError("Metric rows must match the input record order")
    if any(record.label not in LABELS for record in records):
        raise ValueError("Metrics require labels")
    if any(row.get("status") != "ok" or row.get("prediction") not in LABELS for row in rows):
        raise ValueError("Metrics require successful predictions")
    expected = [record.label for record in records]
    predicted = [row["prediction"] for row in rows]
    return {
        "label_order": list(LABELS),
        "records": len(records),
        "accuracy": float(accuracy_score(expected, predicted)),
        "classification_report": classification_report(
            expected, predicted, labels=list(LABELS), target_names=list(LABELS),
            output_dict=True, zero_division=0,
        ),
        "confusion_matrix": confusion_matrix(expected, predicted, labels=list(LABELS)).tolist(),
    }
