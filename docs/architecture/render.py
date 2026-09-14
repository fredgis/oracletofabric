"""Render every architecture view with a locally installed Graphviz binary."""

import os
import runpy
import sys
from pathlib import Path


ARCHITECTURE_DIR = Path(__file__).resolve().parent
DIAGRAMS_DIR = ARCHITECTURE_DIR / "diagrams"
DEFAULT_SOURCES = (
    "01_context.py",
    "02_network_topology.py",
    "03_security_flows.py",
    "04_data_flows.py",
)


def ensure_graphviz_on_path() -> None:
    candidates = (
        Path(r"C:\Program Files\Graphviz\bin"),
        Path(r"C:\Program Files (x86)\Graphviz\bin"),
        Path(os.environ.get("LOCALAPPDATA", "")) / "Programs" / "Graphviz" / "bin",
    )
    for directory in candidates:
        if (directory / "dot.exe").is_file():
            os.environ["PATH"] = f"{directory}{os.pathsep}{os.environ.get('PATH', '')}"
            return


def render(source: Path) -> None:
    if not source.is_file():
        raise FileNotFoundError(f"Diagram source not found: {source}")
    print(f"Rendering {source.name}")
    sys.argv = [str(source)]
    runpy.run_path(str(source), run_name="__main__")


def main() -> int:
    ensure_graphviz_on_path()
    source_names = tuple(sys.argv[1:]) or DEFAULT_SOURCES
    for source_name in source_names:
        render(DIAGRAMS_DIR / source_name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
