Widget Interviewer Guideline
============================

.. jinja:: snippets

   {% for variant in variants %}

   .. container:: hr-interviewer-guideline interviewer-guideline-{{ variant.lexer }}

      .. rubric:: Widgets: {{ variant.name }}

      See the :doc:`full guide <widgets>`.

      .. collapse:: Part 1

         .. collapse:: Prompt

            .. interviewer-guideline-section:: widgets.rst
               :section: #widget-prompt
               :language: {{ variant.lexer }}
               :exclude-sections: Follow up questions

         .. collapse:: Follow up questions

            .. interviewer-guideline-section:: widgets.rst
               :section: Part 1 / Prompt / Follow up questions
               :language: {{ variant.lexer }}

         .. collapse:: FAQ

            .. interviewer-guideline-section:: widgets.rst
               :section: Part 1 / FAQ
               :language: {{ variant.lexer }}

   {% endfor %}
