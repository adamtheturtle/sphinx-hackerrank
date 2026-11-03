|Build Status| |PyPI|

sphinx-hackerrank
=================

Export Sphinx documentation as self-contained HTML for HackerRank Interviewer Guidelines, with styles and images.
Local previews add **Copy code** buttons.
Build and preview locally without HackerRank credentials.

Quick start
-----------

In an existing Sphinx project:

.. code-block:: console

   pip install sphinx-hackerrank

Add this to ``docs/conf.py`` (replace ``docs`` with your Sphinx source directory):

.. code-block:: python

   """Sphinx configuration."""

   from sphinx_hackerrank import GuidelineExport

   extensions = ["sphinx_hackerrank"]
   hackerrank_exports = [
       GuidelineExport(
           docname="review",
           selector=".hr-interviewer-guideline",
           output_path="interviewer-guidelines/review.html",
           name="Widget review",
       ),
   ]

Create ``docs/review.rst`` and add ``review`` to your existing toctree:

.. code-block:: rst

   Widget review
   =============

   .. container:: hr-interviewer-guideline

      Interviewer instructions go here.

      .. code-block:: text

         example input

Build:

.. code-block:: console

   sphinx-build -W -b hackerrank docs build/hackerrank

Open ``build/hackerrank/interviewer-guidelines/index.html`` to preview the exports.
Upload ``build/hackerrank/interviewer-guidelines/review.html`` using your own publishing tool.

Choosing content
----------------

Each ``GuidelineExport`` specifies:

* ``docname``: the RST path relative to your source directory, without ``.rst``.
* ``selector``: a CSS selector matching exactly one container in that page.
* ``output_path``: a unique HTML path relative to the build directory.
* ``name``: the label shown in the preview index.

Use the ``hr-interviewer-guideline`` container class for bundled styles and preview copy buttons.
Upload the configured ``output_path`` fragment.
The adjacent ``.preview.html`` page adds copy controls for local use.
The builder also produces ordinary themed documentation pages.

For collapsible sections, enable `sphinx-toolbox.collapse <https://sphinx-toolbox.readthedocs.io/en/stable/extensions/collapse.html>`_.
To reuse guide sections, enable `sphinx-section-include <https://github.com/adamtheturtle/sphinx-section-include>`_.
See the `sample project <https://github.com/adamtheturtle/sphinx-hackerrank/tree/main/sample>`_ for both.

Uploaded fragments contain no scripts because HackerRank strips script tags.
Copy buttons are available in the adjacent local preview pages.

Source links
------------

Links to other pages point to the local build by default.
To link to hosted documentation, set ``hackerrank_source_url = "https://example.org/guides/"`` in ``conf.py``.
For source files, set ``hackerrank_source_suffix = ".rst"`` too.
Set ``hackerrank_source_anchors = False`` if the destination does not support anchors.

Contributing
------------

See `CONTRIBUTING.rst <https://github.com/adamtheturtle/sphinx-hackerrank/blob/main/CONTRIBUTING.rst>`_ for checks and releases.
MIT licensed.

.. |Build Status| image:: https://github.com/adamtheturtle/sphinx-hackerrank/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/sphinx-hackerrank/actions
.. |PyPI| image:: https://badge.fury.io/py/sphinx-hackerrank.svg
   :target: https://badge.fury.io/py/sphinx-hackerrank
