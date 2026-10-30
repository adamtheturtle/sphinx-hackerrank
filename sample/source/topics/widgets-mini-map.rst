Widget mini-map
===============

.. jinja:: snippets

   {% for variant in variants %}

   .. container:: hr-mini-map mini-map-{{ variant.lexer }}

      .. rubric:: Widgets: {{ variant.name }}

      See the :doc:`full guide <widgets>`.

      .. collapse:: Part 1

         .. collapse:: Prompt

            .. mini-map-section:: widgets.rst
               :section: #widget-prompt
               :language: {{ variant.lexer }}

         .. collapse:: FAQ

            .. mini-map-section:: widgets.rst
               :section: Part 1 / FAQ
               :language: {{ variant.lexer }}

   {% endfor %}
