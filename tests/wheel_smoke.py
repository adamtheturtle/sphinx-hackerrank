"""Install the wheel and build an independent project without checkout imports."""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    (wheel,) = root.joinpath("dist").glob("*.whl")
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        subprocess.run(["uv", "venv", "--python", sys.executable, str(temp / "venv")], check=True)
        python = temp / "venv" / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        subprocess.run(["uv", "pip", "install", "--python", str(python), str(wheel)], check=True)
        shutil.copytree(root / "examples/minimal/manual", temp / "manual")
        subprocess.run(
            [
                str(python),
                "-m",
                "sphinx",
                "-W",
                "-b",
                "hackerrank",
                "manual",
                "output",
            ],
            cwd=temp,
            check=True,
            env={key: value for key, value in os.environ.items() if key != "PYTHONPATH"},
        )
        assert (temp / "output/mini-maps/index.html").is_file()
        for language in ("python", "javascript"):
            fragment = temp / f"output/mini-maps/topics/widgets/{language}.html"
            assert "hr-mini-map" in fragment.read_text(encoding="utf-8")
        print("Installed-wheel build passed outside the checkout.")


if __name__ == "__main__":
    main()
