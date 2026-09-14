from copy import deepcopy


class JobProgress:
    """Completed work by equally weighted phases, never an estimate of remaining time."""

    def __init__(self, job: dict, phases: list[tuple[str, str]]):
        self.job = job
        self.steps: list[dict] = [
            {"key": key, "label": label, "status": "pending", "fraction": 0.0}
            for key, label in phases
        ]
        self.current: dict | None = None
        self.detail = "Preparando el trabajo"
        self.completed = 0.0
        self.total: float | None = None
        self.publish()

    def start(self, key: str, total: float | None = None, detail: str = ""):
        self.current = next(step for step in self.steps if step["key"] == key)
        self.current["status"] = "running"
        self.completed, self.total, self.detail = 0.0, total, detail
        self.job["stage"] = self.current["label"]
        self.publish()

    def update(self, completed: float, total: float | None = None, detail: str = ""):
        if total is not None:
            self.total = total
        self.completed, self.detail = completed, detail
        if self.current is not None and self.total:
            self.current["fraction"] = max(
                self.current["fraction"], min(1.0, max(0.0, completed / self.total))
            )
        self.publish()

    def end(self, warning: str = ""):
        if self.current is not None:
            self.current.update(status="warning" if warning else "complete", fraction=1.0)
        self.detail = warning or self.detail
        self.publish()

    def fail(self, detail: str):
        if self.current is not None:
            self.current["status"] = "failed"
        self.detail = detail
        self.publish()

    def publish(self):
        done = sum(step["fraction"] for step in self.steps)
        # 100% is reserved for terminal phases, including explicitly reported warnings.
        terminal = all(step["status"] in {"complete", "warning"} for step in self.steps)
        percent = min(100 if terminal else 99.9, 100 * done / max(1, len(self.steps)))
        self.job["progress"] = {
            "percent": round(percent, 1),
            "stage": self.current["label"] if self.current else "Preparando",
            "detail": self.detail,
            "completed": self.completed,
            "total": self.total,
            "indeterminate": self.current is not None
            and self.current["status"] == "running"
            and self.total is None,
            "steps": deepcopy(self.steps),
        }
