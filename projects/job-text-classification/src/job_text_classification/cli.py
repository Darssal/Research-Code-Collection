"""Explicit local demo, training, prediction and optional HTTP commands."""

from __future__ import annotations

import argparse
import json
import sys
from importlib.resources import as_file, files

from .data import load_records, stratified_split, write_jsonl


def parser() -> argparse.ArgumentParser:
    result = argparse.ArgumentParser(description="Data-free job text classification examples")
    commands = result.add_subparsers(dest="command")
    demo = commands.add_parser("demo", help="Offline CPU demo using only the bundled synthetic fixture")
    demo.add_argument("--output", help="Optional JSONL output, with no source text")
    train = commands.add_parser("train", help="Train TF-IDF + random forest on user-supplied labelled data")
    train.add_argument("--input", required=True)
    train.add_argument("--model-output", required=True)
    train.add_argument("--validation-fraction", type=float, default=0.25)
    train.add_argument("--seed", type=int, default=42)
    predict = commands.add_parser("predict", help="Predict with a trusted locally generated random forest artifact")
    predict.add_argument("--input", required=True)
    predict.add_argument("--model", required=True)
    predict.add_argument("--output", required=True)
    http = commands.add_parser("http", help="Explicit opt-in: transmit supplied texts to the configured HTTP service")
    http.add_argument("--input", required=True)
    http.add_argument("--output", required=True)
    http.add_argument("--workers", type=int, default=4)
    http.add_argument("--timeout", type=float, default=20)
    http.add_argument("--attempts", type=int, default=3)
    bert_train = commands.add_parser("bert-train", help="Optional BERT training; remote downloads require an explicit flag")
    bert_train.add_argument("--input", required=True)
    bert_train.add_argument("--model-output", required=True)
    bert_train.add_argument("--model-name", default="bert-base-chinese")
    bert_train.add_argument("--allow-model-download", action="store_true")
    bert_train.add_argument("--epochs", type=int, default=1)
    bert_train.add_argument("--batch-size", type=int, default=8)
    bert_train.add_argument("--learning-rate", type=float, default=2e-5)
    bert_train.add_argument("--validation-fraction", type=float, default=0.25)
    bert_train.add_argument("--seed", type=int, default=42)
    bert_train.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    bert_predict = commands.add_parser("bert-predict", help="Optional BERT prediction from an existing local model directory")
    bert_predict.add_argument("--input", required=True)
    bert_predict.add_argument("--model", required=True)
    bert_predict.add_argument("--output", required=True)
    bert_predict.add_argument("--device", choices=["cpu", "cuda"], default="cpu")
    return result


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    command = args.command or "demo"
    try:
        if command in {"demo", "train"}:
            from .baseline import RandomForestBaseline, classification_metrics

            if command == "demo":
                resource = files("job_text_classification").joinpath("examples/synthetic_jobs.jsonl")
                with as_file(resource) as path:
                    records = load_records(path, require_labels=True)
                seed, validation_fraction = 42, 0.25
            else:
                records = load_records(args.input, require_labels=True)
                seed, validation_fraction = args.seed, args.validation_fraction
            train, validation = stratified_split(records, validation_fraction, seed)
            model = RandomForestBaseline(seed=seed).fit(train)
            rows = model.predict(validation)
            if command == "train":
                model.save(args.model_output)
            elif getattr(args, "output", None):
                write_jsonl(args.output, rows)
            summary = {
                "model": "character_tfidf_random_forest", "training_records": len(train),
                "data_scope": "synthetic_fixture" if command == "demo" else "user_supplied",
                "evaluation_scope": "held_out_validation", "paper_metrics": False,
                "metrics": classification_metrics(validation, rows),
            }
        elif command == "predict":
            from .baseline import RandomForestBaseline

            records = load_records(args.input)
            rows = RandomForestBaseline.load(args.model).predict(records)
            write_jsonl(args.output, rows)
            summary = {"records": len(rows), "mode": "local_random_forest"}
        elif command == "http":
            from .http_adapter import HttpServiceAdapter

            adapter = HttpServiceAdapter.from_environment(timeout=args.timeout, attempts=args.attempts)
            records = load_records(args.input)
            rows = adapter.predict(records, workers=args.workers)
            write_jsonl(args.output, rows)
            failed = sum(row["status"] != "ok" for row in rows)
            summary = {"records": len(rows), "failed": failed, "mode": "configured_http_service"}
            print(json.dumps(summary, ensure_ascii=False, indent=2))
            return 2 if failed else 0
        elif command == "bert-train":
            from .baseline import classification_metrics
            from .bert import BertBaseline

            records = load_records(args.input, require_labels=True)
            train, validation = stratified_split(records, args.validation_fraction, args.seed)
            model = BertBaseline.for_training(
                args.model_name, allow_download=args.allow_model_download, device=args.device, seed=args.seed,
            )
            model.fit(train, epochs=args.epochs, batch_size=args.batch_size, learning_rate=args.learning_rate, seed=args.seed)
            rows = model.predict(validation)
            model.save(args.model_output)
            summary = {
                "model": "bert", "training_records": len(train), "data_scope": "user_supplied",
                "evaluation_scope": "held_out_validation", "checkpoint": "final_epoch", "paper_metrics": False,
                "metrics": classification_metrics(validation, rows),
            }
        else:
            from .bert import BertBaseline

            records = load_records(args.input)
            rows = BertBaseline.load(args.model, device=args.device).predict(records)
            write_jsonl(args.output, rows)
            summary = {"records": len(rows), "mode": "local_bert"}
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        return 0
    except (ValueError, OSError, ImportError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
