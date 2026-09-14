import hashlib
import importlib.metadata
import platform
from pathlib import Path


def provenance() -> dict:
    root = Path(__file__).resolve().parents[1]
    paths = sorted(
        [
            *root.joinpath("learning").glob("*.py"),
            *root.joinpath("models").rglob("*.py"),
            root / "services/features.py",
        ]
    )
    digest = hashlib.sha256()
    for path in paths:
        digest.update(path.relative_to(root).as_posix().encode())
        digest.update(path.read_text(encoding="utf-8").encode())
    versions: dict[str, str | None] = {}
    for name in ("numpy", "scipy", "scikit-learn", "catboost", "lightgbm", "xgboost", "torch"):
        try:
            versions[name] = importlib.metadata.version(name)
        except importlib.metadata.PackageNotFoundError:
            versions[name] = None
    return {
        "python": platform.python_version(),
        "platform": platform.system(),
        "packages": versions,
        "code_sha256": digest.hexdigest(),
    }
