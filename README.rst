|Build Status| |PyPI|

sphinx-hackerrank
=================

Export selected Sphinx HTML as portable HackerRank Interviewer Guidelines.
Fragments include scoped styles and code-copy controls, with no external assets.

Install and configure
---------------------

.. code-block:: console

   pip install sphinx-hackerrank

Add to ``conf.py``:

.. code-block:: python

   """Sphinx configuration."""

   from sphinx_hackerrank import GuidelineExport

   extensions = ["sphinx_hackerrank"]
   hackerrank_exports = [
       GuidelineExport(
           docname="review",
           selector=".hr-interviewer-guideline",
           output_path="interviewer-guidelines/widgets/review.html",
           name="Widget review",
       ),
   ]

Write ``review.rst`` using ordinary RST and your chosen Sphinx extensions:

.. code-block:: rst

   Widget review
   =============

   .. container:: hr-interviewer-guideline

      Interviewer instructions go here.

      .. code-block:: text

         example input

For collapsible sections, use `sphinx-toolbox.collapse <https://sphinx-toolbox.readthedocs.io/en/stable/extensions/collapse.html>`_.
For excerpts from maintained guides, use `sphinx-section-include <https://github.com/adamtheturtle/sphinx-section-include>`_.
Consumers install and enable their own authoring and template extensions.
See the `sample <./sample/source>`_ and its `dependencies <./sample/requirements.txt>`_.

Build
-----

.. code-block:: console

   sphinx-build -W -b hackerrank docs build/hackerrank

Open ``build/hackerrank/interviewer-guidelines/index.html`` to preview the exports.
Each request selects exactly one container and writes a unique HTML destination inside the build directory.
Use the ``hr-interviewer-guideline`` class for the bundled styles and code-copy controls.
The builder also produces ordinary themed pages.
Use an extension such as ``sphinx-copybutton`` for copy buttons on those pages.
The exporter's script is embedded only in standalone fragments.
Native disclosures and code remain usable without JavaScript.
Hosts must allow the embedded script for copy buttons to appear.

The exporter preserves the selected content, including admonitions and headings.
Consumers own composition, language contexts, filtering, question mappings, and publishing.
Sphinx's ``only`` directive supports ``builder_hackerrank``, ``builder_html``, or their shared ``html`` format tag.

Source links
------------

Relative HTML links are rewritten for the export's destination.
To target a hosted guide or source site, configure:

.. code-block:: python

   """Sphinx configuration."""

   hackerrank_source_url = "https://example.org/guides/"
   hackerrank_source_suffix = ".html"
   hackerrank_source_anchors = True

Use ``.rst`` for source files, and disable anchors when the destination does not support them.
External URLs and links within a fragment are retained.

Publishing
----------

Use a separate tool to manage credentials, question identities, and HackerRank API calls.
``sphinx_hackerrank.html.html_equivalent(left, right)`` compares generated and saved HTML while tolerating serialization differences and preserving code whitespace and spaces between inline elements.
``normalize_html(html=...)`` exposes that normalized representation.
The comparison can serve as the HackerRank SDK's ``notes_equal`` callback.

Contributing
------------

See `CONTRIBUTING.rst <./CONTRIBUTING.rst>`_ for checks and releases.
Licensed under the MIT license.
See ``LICENSE``.

.. |Build Status| image:: https://github.com/adamtheturtle/sphinx-hackerrank/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/sphinx-hackerrank/actions
.. |PyPI| image:: https://badge.fury.io/py/sphinx-hackerrank.svg
   :target: https://badge.fury.io/py/sphinx-hackerrank
