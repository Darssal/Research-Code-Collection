"""Optional BERT baseline. Loading remote weights requires explicit opt-in."""

from __future__ import annotations

from pathlib import Path

from . import LABELS
from .data import Record, public_prediction


class BertBaseline:
    def __init__(self, tokenizer, model, *, device: str = "cpu", max_length: int = 128):
        if not 8 <= max_length <= 512:
            raise ValueError("max_length must be between 8 and 512")
        self.tokenizer, self.model = tokenizer, model
        self.device, self.max_length = device, max_length
        self.model.to(device)

    @classmethod
    def for_training(
        cls, model_name: str = "bert-base-chinese", *, allow_download: bool = False,
        device: str = "cpu", max_length: int = 128, seed: int = 42,
    ) -> "BertBaseline":
        import torch
        from transformers import BertForSequenceClassification, BertTokenizer

        torch.manual_seed(seed)
        tokenizer = BertTokenizer.from_pretrained(model_name, local_files_only=not allow_download)
        model = BertForSequenceClassification.from_pretrained(
            model_name, local_files_only=not allow_download, num_labels=len(LABELS),
            id2label=dict(enumerate(LABELS)), label2id={label: index for index, label in enumerate(LABELS)},
        )
        return cls(tokenizer, model, device=device, max_length=max_length)

    @classmethod
    def load(cls, model_dir: str | Path, *, device: str = "cpu", max_length: int = 128) -> "BertBaseline":
        from transformers import BertForSequenceClassification, BertTokenizer

        if not Path(model_dir).is_dir():
            raise ValueError("Prediction requires an existing local model directory")
        tokenizer = BertTokenizer.from_pretrained(model_dir, local_files_only=True)
        model = BertForSequenceClassification.from_pretrained(model_dir, local_files_only=True)
        actual = tuple(model.config.id2label.get(index) for index in range(len(LABELS)))
        if actual != LABELS or model.config.num_labels != len(LABELS):
            raise ValueError("Local checkpoint does not have this project's fixed label order")
        return cls(tokenizer, model, device=device, max_length=max_length)

    def fit(self, records: list[Record], *, epochs: int = 1, batch_size: int = 8, learning_rate: float = 2e-5, seed: int = 42) -> None:
        import torch
        from torch.utils.data import DataLoader, TensorDataset

        if not records or any(record.label not in LABELS for record in records):
            raise ValueError("BERT training requires labelled records")
        if not 1 <= epochs <= 20 or not 1 <= batch_size <= 256 or learning_rate <= 0:
            raise ValueError("Use epochs in [1, 20], batch_size in [1, 256], and positive learning_rate")
        encoded = self.tokenizer(
            [record.text for record in records], padding=True, truncation=True,
            max_length=self.max_length, return_tensors="pt",
        )
        labels = torch.tensor([LABELS.index(record.label) for record in records], dtype=torch.long)
        dataset = TensorDataset(encoded["input_ids"], encoded["attention_mask"], labels)
        loader = DataLoader(dataset, batch_size=batch_size, shuffle=True, generator=torch.Generator().manual_seed(seed))
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=learning_rate)
        for _ in range(epochs):
            self.model.train()
            for input_ids, attention_mask, targets in loader:
                optimizer.zero_grad()
                output = self.model(
                    input_ids=input_ids.to(self.device), attention_mask=attention_mask.to(self.device),
                    labels=targets.to(self.device),
                )
                output.loss.backward()
                optimizer.step()

    def predict(self, records: list[Record], *, batch_size: int = 8) -> list[dict]:
        import torch

        if not 1 <= batch_size <= 256:
            raise ValueError("batch_size must be between 1 and 256")
        rows = []
        self.model.eval()
        with torch.no_grad():
            for start in range(0, len(records), batch_size):
                batch = records[start:start + batch_size]
                encoded = self.tokenizer(
                    [record.text for record in batch], padding=True, truncation=True,
                    max_length=self.max_length, return_tensors="pt",
                )
                output = self.model(**{key: value.to(self.device) for key, value in encoded.items()})
                values = torch.softmax(output.logits, dim=-1).cpu().tolist()
                for record, probabilities in zip(batch, values):
                    prediction = LABELS[max(range(len(LABELS)), key=lambda index: probabilities[index])]
                    rows.append(public_prediction(
                        record, prediction, status="ok",
                        probabilities={label: float(probabilities[index]) for index, label in enumerate(LABELS)},
                    ))
        return rows

    def save(self, model_dir: str | Path) -> None:
        destination = Path(model_dir)
        destination.mkdir(parents=True, exist_ok=True)
        self.model.save_pretrained(destination)
        self.tokenizer.save_pretrained(destination)
