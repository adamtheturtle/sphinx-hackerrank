|Build Status| |PyPI|

sphinx-hackerrank
=================

Build portable Interviewer Guidelines from maintained Sphinx guides.

* Reuse Sphinx's HTML renderer.
* Export one standalone HTML fragment per question and language, plus a local preview index.
* Build and preview without a HackerRank login or API token.

.. contents::

Installation
------------

* Requires Python 3.12+ and Sphinx 9.1.1+.
* Installed packages need no ``sys.path`` changes.

Install from PyPI:

.. code-block:: console

   pip install sphinx-hackerrank

Or install a wheel from the GitHub release assets:

.. code-block:: console

   pip install https://github.com/adamtheturtle/sphinx-hackerrank/releases/download/2026.10.30.2/sphinx_hackerrank-2026.10.30.2-py3-none-any.whl

Enable the extension in ``conf.py``:

.. code-block:: python

   """Sphinx configuration."""

   extensions = ["sphinx_hackerrank"]

Authoring
---------

Keep the full guide and its Interviewer Guideline RST beside each other.
Declare the composition in the Interviewer Guideline RST:

.. code-block:: rst

   .. interviewer-guideline:: guide.rst
      :parts: Stage 1
              Stage 2

      .. guideline-introduction::

         See the `source guide <{source_url}>`_.

      .. guideline-before:: Shared brief

      .. guideline-group:: Work

         .. guideline-select:: Brief
            :alternatives: Briefs

      .. guideline-group:: Examples
         :required-for: Stage 1

         .. guideline-select:: Cases
            :optional:
            :include-heading:

      .. guideline-after:: Review

The package has no built-in section names, grouping rules, or introductory wording.
``conf.py`` configures the extension, languages, and site-wide settings.
Each guideline's RST owns its selections, presentation, and completeness rules.
The full guide owns the selected content, and the adjacent YAML mapping owns question identities and languages.

``:parts:`` lists exact source headings, one per line.
Every listed part must exist once, independently of its selected contents.
Parts retain the full guide's order, and punctuation in headings is literal.
Each ``guideline-group`` combines its selections under the supplied display title.
Groups and selections appear in declaration order.
A ``guideline-select`` is required by default and must retain content after filtering.
Add ``:optional:`` for a section which may be absent or empty, and ``:include-heading:`` to retain its source heading.
``:alternatives:`` lists other accepted heading spellings, one per line.
Exactly one spelling must match.
Use ``guideline-select:: .`` for a part whose instructions are its own body.
Separately selected descendants appear once in their own group.

A group's ``:required-for:`` lists exact part headings which must contain nonempty content, even when its selections are optional elsewhere.
Every heading in that list must identify a selected part.
For example, coding stages can require examples while discussion stages omit them.
``guideline-before`` and ``guideline-after`` select shared content before or after all parts.
They accept the same options as ``guideline-select`` and cannot overlap a part.

An optional ``guideline-introduction`` contains introductory RST, with ``{source_url}`` replaced by the configured guide URL.
Other prose belongs in the full guide.
Native ``include`` directives can share recipe declarations or selections, with dependencies tracked for incremental builds.
Recipe declarations are validated and consumed before rendering.
Misplaced declarations, invalid nesting, and unsupported recipe content fail the build.

The directive derives its page title from the guide and its languages from the adjacent question mapping.
Source selections can be nested beneath other selections without requiring parent paths in the recipe.
Optional empty groups are omitted after admonitions are removed.
Missing mappings, incomplete parts, missing required content, and ambiguous selected headings fail the build.
Changing the guide, mapping, recipe, or an included recipe file refreshes the view.

Pattern selectors use ``:part-pattern:`` and ``:required-for-pattern:`` options.
``:minimum-parts:`` is only accepted with a pattern selector.
Recipes using regex values in ``:parts:`` or ``:required-for:`` must migrate to those pattern options or list their exact headings.

Programmatic consumers can still configure ``GuidelineLayout``, ``SectionGroup``, ``SectionSelection``, and ``GroupRequirement`` from ``sphinx_hackerrank.layout``.
Their ``part_headings`` field selects exact names, while ``part_pattern`` retains pattern matching.
``hackerrank_guideline_layout`` supplies a default Python layout, and ``hackerrank_guideline_layouts`` maps names to layouts selected with ``:layout:``.
An inline recipe cannot be combined with ``:layout:``.

For other layouts, include native sections by exact heading path or an existing RST section label:

.. code-block:: rst

   .. container:: hr-interviewer-guideline interviewer-guideline-python

      .. collapse:: Prompt

         .. interviewer-guideline-section:: widgets.rst
            :section: Part 1 / Prompt
            :language: python

* Use ``:section: #widget-prompt`` to select a labelled section.
* Add ``:include-heading:`` to retain the selected section's heading.
* Nested headings become rubrics inside disclosures.
* Build with ``-W`` to reject missing or ambiguous selections as directive errors.
* Sections come from the full guide without extraction markers or duplicated content.
* Native includes, substitutions, and the guide's existing Jinja templates are supported.
* Variants are cached within each Interviewer Guideline read and discarded before Sphinx persists the document tree.
* Guide and included-file dependencies are tracked for incremental builds.

Subsection exclusions
---------------------

Keep the guide's existing heading hierarchy when composing separate disclosures.
Use ``:exclude-sections:`` to omit subsections from a parent selection:

.. code-block:: rst

   .. interviewer-guideline-section:: widgets.rst
      :section: Part 1 / Prompt
      :language: python
      :exclude-sections: Follow up questions

   .. interviewer-guideline-section:: widgets.rst
      :section: Part 1 / Prompt / Follow up questions
      :language: python

* Exclusions are heading paths relative to the selected section, or section labels within it.
* List multiple exclusions on separate indented lines.
* Missing or ambiguous exclusions fail the build, as does excluding the selected section itself.
* Exclusions affect only the copied view.
  The source guide and other selections retain their content.

Language contexts
-----------------

Configure how each language renders the guide's Jinja context:

.. code-block:: python

   """Sphinx configuration."""

   hackerrank_jinja_context = "snippets"
   hackerrank_languages = {
       "python": {
           "name": "Python",
           "context": {"variants": [{"name": "Python", "lexer": "python"}]},
       },
   }

* ``context`` overrides values in the configured Jinja context while that variant is parsed.
  The original configuration is restored afterwards.
* ``name`` identifies redundant language disclosures to flatten in copied content.
* Other part, category, and test-alternative disclosures remain intact.
* Admonitions are omitted within ``hr-interviewer-guideline`` containers by default.
  Set ``hackerrank_exclude_admonitions = False`` to retain them.
  The full guide's admonitions are unaffected.

Question mappings
-----------------

Create a mapping beside each Interviewer Guideline, such as ``widgets-interviewer-guideline.yml`` beside ``widgets-interviewer-guideline.rst``:

.. code-block:: yaml

   version: 1
   questions:
     - language: python
       name: Widgets - Python

* ``hackerrank_manifest_pattern`` defaults to ``**/*-interviewer-guideline.yml``, relative to Sphinx's source directory.
* Nested directories and custom source layouts are supported.
* The builder reads the language and name.
  Your publishing tool can manage extra fields such as question IDs.

Build and preview
-----------------

.. code-block:: console

   sphinx-build -W -b hackerrank docs build/hackerrank

* Open ``build/hackerrank/interviewer-guidelines/index.html`` to select a question and language.
* Each preview uses the same self-contained HTML that can be saved as HackerRank Interviewer Guidelines.
* Each code block has a keyboard-accessible **Copy code** button that preserves whitespace.
* Copy buttons use JavaScript bundled with the output.
  Hosts must allow that script to run for the buttons to appear.
* Native disclosure elements and code remain usable without JavaScript.
* The builder also produces ordinary themed HTML pages.
  The extension's directives work in the standard ``html`` builder too.
* Sphinx's native ``only`` directive can select ``builder_hackerrank``, ``builder_html``, or the shared ``html`` format tag.

Source links
------------

By default, links to full guide pages point back into the local HTML build.
To target a hosted documentation or source site, configure:

.. code-block:: python

   """Sphinx configuration."""

   hackerrank_source_url = "https://example.org/guides/"
   hackerrank_source_suffix = ".html"
   hackerrank_source_anchors = True

* Set ``hackerrank_source_suffix`` to ``.rst`` when linking to source files.
* Set ``hackerrank_source_anchors = False`` when the destination does not support anchors.
* External URLs and links within a fragment are retained.

Publishing
----------

* Use a separate publishing tool to call the HackerRank API and manage credentials, question identities, candidate prompts, or projects.
* Your publishing tool can read the generated fragments and verify saved Interviewer Guidelines.

Use ``sphinx_hackerrank.html.html_equivalent`` to compare generated and saved HTML.
It tolerates entity encoding, block indentation, and HackerRank's column-width formatting.
Literal whitespace in code, scripts, styles, and text areas is preserved, as are spaces separating inline elements and disclosure attributes.
``normalize_html(html=...)`` exposes the normalized representation when needed.
The comparison can be passed as the ``notes_equal`` callback to the HackerRank SDK's ``questions.update_internal_notes()`` method.

Contributing
------------

See `CONTRIBUTING.rst <./CONTRIBUTING.rst>`_ for setup, linting, tests, and releases.

* The sample under ``sample/source`` uses a custom Jinja context and nested guide files.
* The wheel smoke test installs the built wheel into a fresh environment and builds that sample outside the checkout.

License
-------

MIT.
See ``LICENSE``.

.. |Build Status| image:: https://github.com/adamtheturtle/sphinx-hackerrank/actions/workflows/ci.yml/badge.svg?branch=main
   :target: https://github.com/adamtheturtle/sphinx-hackerrank/actions
.. |PyPI| image:: https://badge.fury.io/py/sphinx-hackerrank.svg
   :target: https://badge.fury.io/py/sphinx-hackerrank
