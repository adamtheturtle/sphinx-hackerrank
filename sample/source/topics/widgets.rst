Widgets
=======

Part 1
------

.. _widget-prompt:

Prompt
~~~~~~

Print a widget's name.

.. jinja:: snippets

   {% for variant in variants %}

   .. collapse:: {{ variant.name }}

      .. code-block:: {{ variant.lexer }}

         {{ variant.prompt }}

   {% endfor %}

.. collapse:: Alternate inputs

   .. code-block:: text

      widget = ""

.. tip:: Ask the participant to explain their choice.

Follow up questions
^^^^^^^^^^^^^^^^^^^

How would you handle an empty widget name?

FAQ
~~~

The widget's name is always a string.
