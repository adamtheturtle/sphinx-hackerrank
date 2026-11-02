"""Install the wheel and build an independent project without checkout
imports.
"""

import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> None:
    """Install and exercise the wheel in a temporary consumer project."""
    root = Path(__file__).resolve().parents[1]
    (wheel,) = root.joinpath("dist").glob(pattern="*.whl")
    with tempfile.TemporaryDirectory() as directory:
        temp = Path(directory)
        _ = subprocess.run(
            args=[
                "uv",
                "venv",
                "--python",
                sys.executable,
                str(object=temp / "venv"),
            ],
            check=True,
        )
        python = (
            temp
            / "venv"
            / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
        )
        _ = subprocess.run(
            args=[
                "uv",
                "pip",
                "install",
                "--python",
                str(object=python),
                str(object=wheel),
                "--requirement",
                str(object=root / "sample/requirements.txt"),
            ],
            check=True,
        )
        _ = shutil.copytree(src=root / "sample/source", dst=temp / "manual")
        _ = (temp / "manual/topics/wheel-image.svg").write_text(
            data=(
                '<svg xmlns="http://www.w3.org/2000/svg" '
                'width="16" height="16"><rect width="16" height="16"/></svg>'
            ),
            encoding="utf-8",
        )
        review = temp / "manual/topics/widgets-interviewer-guideline.rst"
        _ = review.write_text(
            data=review.read_text(encoding="utf-8")
            + "\n   .. image:: wheel-image.svg\n",
            encoding="utf-8",
        )
        _ = subprocess.run(
            args=[
                str(object=python),
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
            env={
                key: value
                for key, value in os.environ.items()
                if key != "PYTHONPATH"
            },
        )
        assert (temp / "output/interviewer-guidelines/index.html").is_file()
        for output in ("guide.html",):
            fragment = (
                temp / "output/interviewer-guidelines/topics/widgets" / output
            )
            assert fragment.is_file()
            assert "data:image/svg+xml;base64," in fragment.read_text(
                encoding="utf-8"
            )
        print("Installed-wheel build passed outside the checkout.")


if __name__ == "__main__":
    main()
