import copy
import json
from pathlib import Path

import numpy as np
import torch
from torch import nn

from app.learning.dataset import HEADS


class FootballNetwork(nn.Module):
    def __init__(self, input_size: int, sequence_size: int, recurrent: bool = False):
        super().__init__()
        self.recurrent = recurrent
        self.static = nn.Sequential(
            nn.Linear(input_size, 96),
            nn.LayerNorm(96),
            nn.GELU(),
            nn.Dropout(0.15),
            nn.Linear(96, 48),
            nn.GELU(),
        )
        self.gru = nn.GRU(sequence_size, 48, batch_first=True) if recurrent else None
        self.trunk = nn.Sequential(
            nn.Linear(96 if recurrent else 48, 64), nn.GELU(), nn.Dropout(0.15)
        )
        self.heads = nn.ModuleDict({name: nn.Linear(64, size) for name, size in HEADS.items()})

    def forward(self, x, sequence):
        representation = self.static(x)
        if self.gru is not None:
            _, state = self.gru(sequence)
            representation = torch.cat([representation, state[-1]], dim=1)
        representation = self.trunk(representation)
        return {name: layer(representation) for name, layer in self.heads.items()}


class DeepModel:
    def __init__(self, family: str, input_size: int, sequence_size: int, config: dict):
        self.family, self.config = family, config
        torch.manual_seed(config.get("seed", 42))
        torch.set_num_threads(config.get("threads", 4))
        self.dimensions = {"input_size": input_size, "sequence_size": sequence_size}
        self.model = FootballNetwork(input_size, sequence_size, recurrent=family == "gru")
        self.epochs = 0

    @staticmethod
    def loss(outputs, y):
        losses = []
        for index, head in enumerate(HEADS):
            valid = y[:, index] >= 0
            if valid.any():
                losses.append(nn.functional.cross_entropy(outputs[head][valid], y[valid, index]))
        return torch.stack(losses).mean()

    def fit(self, x, sequence, y, xv, sv, yv, on_progress=None):
        x, sequence, y = torch.from_numpy(x), torch.from_numpy(sequence), torch.from_numpy(y)
        xv, sv, yv = torch.from_numpy(xv), torch.from_numpy(sv), torch.from_numpy(yv)
        optimizer = torch.optim.AdamW(self.model.parameters(), lr=0.001, weight_decay=0.01)
        best, patience, state = float("inf"), 0, copy.deepcopy(self.model.state_dict())
        generator = torch.Generator().manual_seed(self.config["seed"])
        batch = self.config["batch_size"]
        for epoch in range(self.config["deep_epochs"]):
            self.model.train()
            order = torch.randperm(len(x), generator=generator)
            for indices in order.split(batch):
                optimizer.zero_grad()
                loss = self.loss(self.model(x[indices], sequence[indices]), y[indices])
                loss.backward()
                nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
            self.model.eval()
            with torch.no_grad():
                validation = float(self.loss(self.model(xv, sv), yv))
            self.epochs = epoch + 1
            if on_progress:
                on_progress(
                    self.epochs,
                    self.config["deep_epochs"],
                    f"{self.family.upper()} · época {self.epochs}/{self.config['deep_epochs']} · pérdida validación {validation:.4f}",
                )
            if validation < best - 0.0001:
                best, patience, state = validation, 0, copy.deepcopy(self.model.state_dict())
            else:
                patience += 1
            if patience >= self.config["early_stopping_rounds"]:
                break
        self.model.load_state_dict(state)
        self.model.eval()
        return self

    def predict(self, x, sequence):
        self.model.eval()
        with torch.no_grad():
            outputs = self.model(torch.from_numpy(x.copy()), torch.from_numpy(sequence.copy()))
            return {
                head: torch.softmax(logits, dim=1).numpy().astype(np.float64)
                for head, logits in outputs.items()
            }

    def save(self, directory: Path):
        directory.mkdir(parents=True, exist_ok=True)
        torch.save(self.model.state_dict(), directory / "weights.pt")
        (directory / "dimensions.json").write_text(json.dumps(self.dimensions), encoding="utf-8")

    @classmethod
    def load(cls, family: str, directory: Path):
        dims = json.loads((directory / "dimensions.json").read_text(encoding="utf-8"))
        model = cls(family, **dims, config={"threads": 2})
        model.model.load_state_dict(
            torch.load(directory / "weights.pt", map_location="cpu", weights_only=True)
        )
        model.model.eval()
        return model
