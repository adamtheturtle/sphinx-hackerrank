Contributing
============

Contributions to this repository must pass tests and linting.

CI is the canonical source of truth.

Install contribution dependencies
---------------------------------

Install Python dependencies in a virtual environment.

.. code-block:: shell

   uv sync --group=dev

Spell checking requires ``enchant``.
This can be installed on macOS, for example, with `Homebrew`_:

.. code-block:: shell

   brew install enchant

and on Ubuntu with ``apt``:

.. code-block:: shell

   apt-get install -y enchant

Install ``pre-commit`` hooks:

.. code-block:: shell

   uv run --group=dev prek install

Linting
-------

Run lint tools either by committing, or with:

.. code-block:: shell

   uv run --group=dev prek run --all-files --hook-stage pre-commit --verbose
   uv run --group=dev prek run --all-files --hook-stage pre-push --verbose
   uv run --group=dev prek run --all-files --hook-stage manual --verbose

.. _Homebrew: https://brew.sh

Running tests
-------------

Run ``pytest``:

.. code-block:: shell

   uv run --group=dev pytest --cov --cov-config=pyproject.toml

Continuous integration
----------------------

Tests are run on GitHub Actions.
The configuration is in ``.github/workflows/``.
CI builds the sample with serial and parallel Sphinx readers, runs tests with 100% branch coverage, and builds distributions.
It also installs the wheel and builds the sample outside the checkout.
The test matrix covers Python 3.12 through 3.15 on Ubuntu and Windows with highest and lowest direct dependencies.
A separate Chromium job checks code-copy buttons, exact clipboard contents, keyboard activation, and clipboard failures.

Run the sample and packaging checks locally:

.. code-block:: shell

   uv run --group=dev sphinx-build -W -b hackerrank sample/source sample/build
   uv build
   uv run --group=release check-wheel-contents dist/*.whl
   uv run --group=dev python tests/wheel_smoke.py
   uv run --group=dev playwright install chromium
   uv run --group=dev python tests/browser_smoke.py

Release Process
---------------

Outcomes
~~~~~~~~

* A new ``git`` tag available to install.
* A new package on PyPI.

Perform a Release
~~~~~~~~~~~~~~~~~

Versions come from Git tags through ``setuptools-scm``.
The release workflow uses ``GITHUB_TOKEN`` to commit release notes and PyPI trusted publishing with the ``release`` environment.
Configure the trusted publisher and set ``PYPI_PUBLISH_ENABLED`` to ``true`` before dispatching a release.

#. `Install GitHub CLI`_.

#. Perform a release:

   .. code-block:: shell

      gh workflow run release.yml --repo adamtheturtle/sphinx-hackerrank

.. _Install GitHub CLI: https://cli.github.com/manual/installation


Release notes
-------------

Write user-facing changes as Markdown in ``newsfragments/<issue>.change.md``.
Towncrier writes one Markdown file per version, used directly for GitHub release notes.
Invalid fragment names fail release assembly.
