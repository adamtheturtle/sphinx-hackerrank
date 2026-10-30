sphinx-hackerrank
=================

Build portable interviewer mini-maps from maintained Sphinx guides.
The ``hackerrank`` builder reuses Sphinx's HTML renderer and exports one
standalone HTML fragment per question and language, plus a local preview index.
No HackerRank login or API token is required to build or preview.

Installation
------------

.. code-block:: console

   pip install sphinx-hackerrank

Built wheels are also published as GitHub release assets:

.. code-block:: console

   pip install https://github.com/adamtheturtle/sphinx-hackerrank/releases/download/2026.10.30.1/sphinx_hackerrank-2026.10.30.1-py3-none-any.whl

Enable the installed extension in ``conf.py``:

.. code-block:: python

   extensions = ["sphinx_hackerrank"]

No ``sys.path`` changes are needed.

Authoring
---------

Keep the full guide and its mini-map RST beside each other. Include native
sections by exact heading path or an existing RST section label:

.. code-block:: rst

   .. container:: hr-mini-map mini-map-python

      .. collapse:: Prompt

         .. mini-map-section:: widgets.rst
            :section: Part 1 / Prompt
            :language: python

Use ``:section: #widget-prompt`` for a labelled section and
``:include-heading:`` to retain the selected section's heading.
Nested headings become rubrics inside disclosures. Missing or ambiguous
selections are reported as directive errors; build with ``-W`` to reject them.
The guide does not need extraction markers or duplicated content.

The directive uses native includes, substitutions, and the guide's existing
Jinja templates. Variants are cached within each mini-map read and discarded
before Sphinx persists the document tree. Guide and included-file dependencies
are tracked for incremental builds.

Language contexts
-----------------

Configure how each language renders the guide's Jinja context:

.. code-block:: python

   hackerrank_jinja_context = "snippets"
   hackerrank_languages = {
       "python": {
           "name": "Python",
           "context": {"variants": [{"name": "Python", "lexer": "python"}]},
       },
   }

``context`` overrides values in the named Jinja context while that variant is
parsed. The original configuration is restored afterwards.
``name`` identifies redundant language disclosures to flatten in copied content.
All other part, category, and test-alternative disclosures remain intact.

By default, admonitions are omitted within ``hr-mini-map`` containers.
Set ``hackerrank_exclude_admonitions = False`` to retain them.
The original guide's admonitions remain unchanged.

Question mappings
-----------------

Create a mapping beside each mini-map, such as ``widgets-mini-map.yml`` beside
``widgets-mini-map.rst``:

.. code-block:: yaml

   version: 1
   questions:
     - language: python
       name: Widgets - Python

The default ``hackerrank_manifest_pattern`` is ``**/*-mini-map.yml``, relative
to Sphinx's source directory. Nested directories and custom source layouts are
supported. Extra fields such as question IDs can be managed by your publishing
tool; the builder reads only the language and name.

Build and preview
-----------------

.. code-block:: console

   sphinx-build -W -b hackerrank docs build/hackerrank

Open ``build/hackerrank/mini-maps/index.html`` to select a question and language.
Each preview uses the same self-contained HTML that can be saved as HackerRank
interviewer notes. Native disclosure elements work without JavaScript.
The builder also produces ordinary themed HTML pages. The extension's directives
work in the standard ``html`` builder too.

Sphinx's native ``only`` directive can select ``builder_hackerrank``,
``builder_html``, or the shared ``html`` format tag.

Source links
------------

By default, links to full guide pages point back into the local HTML build.
To target a hosted documentation or source site, configure:

.. code-block:: python

   hackerrank_source_url = "https://example.org/guides/"
   hackerrank_source_suffix = ".html"
   hackerrank_source_anchors = True

A source repository can use a different suffix, such as ``.rst``, and disable
anchors. External URLs and links within a fragment are retained.

Publishing
----------

Publishing is separate from rendering. This package does not call the HackerRank
API or manage credentials, question identities, candidate prompts, or projects.
Your publishing tool can read the generated fragments and verify saved notes.

Development
-----------

.. code-block:: console

   uv run pytest --cov --cov-report=term-missing
   uv run ruff check .
   uv run ruff format --check .
   uv build
   uv run python tests/wheel_smoke.py

The minimal example under ``examples/minimal/manual`` uses a custom Jinja context
and nested guide files. The wheel smoke test installs the built wheel into a
fresh environment and builds that example outside the checkout.

To release, update the version in ``pyproject.toml`` and
``src/sphinx_hackerrank/__init__.py``, then publish a matching GitHub release.
The release workflow builds and checks distributions before uploading with a
PyPI trusted publisher configured for ``release.yml`` and environment ``release``.
Set the repository variable ``PYPI_PUBLISH_ENABLED`` to ``true`` after configuring
the publisher. The workflow can also be dispatched with a release ``tag``.

License
-------

MIT. See ``LICENSE``.
