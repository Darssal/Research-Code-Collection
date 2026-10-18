from __future__ import annotations

import contextlib
import io
import json
import tempfile
import time
import unittest
import urllib.error
from pathlib import Path
from unittest.mock import patch

from job_text_classification import LABELS
from job_text_classification.baseline import RandomForestBaseline, classification_metrics
from job_text_classification.cli import main, parser
from job_text_classification.data import Record, load_records, public_prediction, stratified_split, write_jsonl
from job_text_classification.http_adapter import HttpServiceAdapter


def training_records():
    return [
        Record("env-1", "污水治理环保设备", "环保"), Record("env-2", "废气污染环保监测", "环保"),
        Record("ai-1", "人工智能模型训练", "人工智能"), Record("ai-2", "机器学习人工智能", "人工智能"),
        Record("other-1", "门店商品收银记录", "否"), Record("other-2", "酒店住客办理入住", "否"),
    ]


class DataTests(unittest.TestCase):
    def test_csv_schema_and_missing_optional_label(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.csv"
            path.write_text("record_id,text,label\nfirst,虚构门店岗位,否\nsecond,虚构研究岗位,\n", encoding="utf-8")
            records = load_records(path)
            self.assertEqual([record.record_id for record in records], ["first", "second"])
            self.assertIsNone(records[1].label)
            with self.assertRaises(ValueError):
                load_records(path, require_labels=True)

    def test_duplicate_ids_and_unknown_labels_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "input.jsonl"
            for rows in [
                [{"record_id": "same", "text": "一"}, {"record_id": "same", "text": "二"}],
                [{"text": "虚构描述", "label": "unknown"}],
            ]:
                write_jsonl(path, rows)
                with self.assertRaises(ValueError):
                    load_records(path)

    def test_split_is_seeded_and_text_disjoint(self):
        records = training_records()
        train, validation = stratified_split(records, seed=17)
        self.assertEqual((train, validation), stratified_split(records, seed=17))
        self.assertEqual(set(record.label for record in train), set(LABELS))
        self.assertFalse({record.text for record in train} & {record.text for record in validation})
        with self.assertRaises(ValueError):
            stratified_split(records + [Record("duplicate", records[0].text, records[0].label)])

    def test_saved_predictions_exclude_source_text(self):
        source = Record("row-1", "这是一段只供本地输入使用的虚构文本", "环保")
        row = public_prediction(source, "环保", status="ok")
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "prediction.jsonl"
            write_jsonl(path, [row])
            result = path.read_text(encoding="utf-8")
            self.assertNotIn(source.text, result)
            self.assertNotIn('"text"', result)


class BaselineTests(unittest.TestCase):
    def test_validation_text_never_changes_training_vocabulary(self):
        model = RandomForestBaseline(n_estimators=10).fit(training_records())
        vocabulary = model.pipeline.named_steps["tfidf"].vocabulary_.copy()
        model.predict([Record("validation", "龘龘龘龘独有验证词", "否")])
        self.assertNotIn("龘龘", vocabulary)
        self.assertEqual(vocabulary, model.pipeline.named_steps["tfidf"].vocabulary_)

    def test_probability_columns_follow_estimator_classes(self):
        # Deliberately train only two classes: the public result still has all three keys.
        records = training_records()[:4]
        model = RandomForestBaseline(n_estimators=10).fit(records)
        raw = model.pipeline.predict_proba([records[0].text])[0]
        classes = model.pipeline.named_steps["classifier"].classes_
        row = model.predict([records[0]])[0]
        self.assertEqual(list(row["probabilities"]), list(LABELS))
        for label, probability in zip(classes, raw):
            self.assertAlmostEqual(row["probabilities"][label], probability)
        self.assertEqual(row["probabilities"]["否"], 0.0)

    def test_fixed_metric_order_and_row_alignment(self):
        records = training_records()
        rows = [public_prediction(record, record.label, status="ok") for record in records]
        metrics = classification_metrics(records, rows)
        self.assertEqual(metrics["label_order"], list(LABELS))
        self.assertEqual(metrics["confusion_matrix"], [[2, 0, 0], [0, 2, 0], [0, 0, 2]])
        with self.assertRaises(ValueError):
            classification_metrics(records, list(reversed(rows)))

    def test_local_model_round_trip(self):
        model = RandomForestBaseline(n_estimators=10).fit(training_records())
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "model.joblib"
            model.save(path)
            loaded = RandomForestBaseline.load(path)
            self.assertEqual(model.predict(training_records()), loaded.predict(training_records()))


class HttpTests(unittest.TestCase):
    def adapter(self, **kwargs):
        return HttpServiceAdapter("https://service.invalid/classify", "fixture", retry_delay=0, **kwargs)

    def test_repeated_failure_terminates_without_text_or_secret(self):
        adapter = self.adapter(attempts=3)
        source = Record("row", "只供测试的虚构文本", "否")
        with patch.object(adapter, "_request", side_effect=TimeoutError) as request:
            rows = adapter.predict([source], workers=1)
        self.assertEqual(request.call_count, 3)
        self.assertEqual(rows[0]["status"], "error")
        self.assertEqual(rows[0]["attempts"], 3)
        self.assertNotIn(source.text, json.dumps(rows, ensure_ascii=False))
        self.assertNotIn("fixture", json.dumps(rows))

    def test_parallel_results_preserve_input_order_even_when_completion_does_not(self):
        adapter = self.adapter()
        def fake_request(text):
            time.sleep(0.02 if text == "slow" else 0)
            return "否"
        with patch.object(adapter, "_request", side_effect=fake_request):
            rows = adapter.predict([Record("first", "slow"), Record("second", "fast")], workers=2)
        self.assertEqual([row["record_id"] for row in rows], ["first", "second"])

    def test_bad_json_and_out_of_set_reply_are_bounded(self):
        for payload in [b"not-json", b'{"textResponse":"unknown"}', b'{"other":"value"}']:
            adapter = self.adapter(attempts=2)
            response = unittest.mock.MagicMock()
            response.__enter__.return_value.read.return_value = payload
            with patch("urllib.request.urlopen", return_value=response) as request:
                row = adapter.classify(Record("row", "虚构文本"))
            self.assertEqual(request.call_count, 2)
            self.assertEqual(row["error"], "invalid_response")

    def test_401_is_not_retried_and_error_does_not_include_body(self):
        adapter = self.adapter(attempts=3)
        error = urllib.error.HTTPError("https://service.invalid", 401, "private-body", {}, None)
        with patch.object(adapter, "_request", side_effect=error) as request:
            row = adapter.classify(Record("row", "虚构文本"))
        self.assertEqual(request.call_count, 1)
        self.assertEqual(row["error"], "http_401")
        self.assertNotIn("private-body", json.dumps(row))

    def test_protocol_cleans_think_and_passes_configured_timeout(self):
        adapter = self.adapter(timeout=1.5)
        response = unittest.mock.MagicMock()
        response.__enter__.return_value.read.return_value = json.dumps({"textResponse": "<think>reason</think>环保"}).encode()
        with patch("urllib.request.urlopen", return_value=response) as request:
            row = adapter.classify(Record("row", "虚构文本"))
        self.assertEqual(row["prediction"], "环保")
        self.assertEqual(request.call_args.kwargs["timeout"], 1.5)
        sent_request = request.call_args.args[0]
        self.assertIn("Authorization", sent_request.unredirected_hdrs)
        self.assertNotIn("Authorization", sent_request.headers)

    def test_missing_environment_and_unbounded_options_rejected(self):
        with patch.dict("os.environ", {}, clear=True):
            with self.assertRaises(ValueError):
                HttpServiceAdapter.from_environment()
        for options in [{"attempts": 0}, {"attempts": 11}, {"timeout": 0}, {"timeout": 301}]:
            with self.assertRaises(ValueError):
                self.adapter(**options)


class CliTests(unittest.TestCase):
    def test_default_demo_is_offline_and_marks_synthetic_scope(self):
        output = io.StringIO()
        with patch("urllib.request.urlopen", side_effect=AssertionError("network must not run")), contextlib.redirect_stdout(output):
            code = main([])
        summary = json.loads(output.getvalue())
        self.assertEqual(code, 0)
        self.assertEqual(summary["data_scope"], "synthetic_fixture")
        self.assertEqual(summary["evaluation_scope"], "held_out_validation")
        self.assertFalse(summary["paper_metrics"])

    def test_bert_download_requires_explicit_opt_in(self):
        args = parser().parse_args(["bert-train", "--input", "input.jsonl", "--model-output", "outputs/model"])
        self.assertFalse(args.allow_model_download)
        self.assertEqual(args.device, "cpu")


if __name__ == "__main__":
    unittest.main()
