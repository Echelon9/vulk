VULK - Vulkan 3d engine
=======================

Project status
--------------

|Build Status| |Code Climate| |Test Coverage| |Issue Count|

`API documentation <https://realitix.github.io/vulk-api/vulk/>`__

`Example of use <https://realitix.github.io/vulk-demo/>`__

What is it ?
------------

Vulk is a 3D engine aimed to provide the best graphical experience with
Vulkan API. It is written fully in Python. It depends on C modules for
the communication with Vulkan.

What is the project goal ?
--------------------------

-  Easy to use: you don't need to understand Vulkan to use VULK.
-  Modular: every single part of the api must be modular.
-  Full: you shouldn't need to customize core code, it should suits
   everyone needs.

Documentation
-------------

API
~~~

The API documentation is generated after each commit by Travis CI
servers into the dedicated repo vulk-api. You can check it here: `API
documentation <https://realitix.github.io/vulk-api/vulk/>`__

To build the API (in vulk-api folder), execute the following commands:

.. code:: bash

    pip install -r requirements.txt
    python setup.py api

API convention
^^^^^^^^^^^^^^

To make a beautiful API documentation, we must respect conventions. The
documentation must be in markdown and respect the following syntax:

.. code:: markdown

    '''
    Description of the function

    *Parameters:*

    - `parameter 1`: Parameters is a list and must be quoted with ` `
    - `parameter 2`: The description should be precise and can be on
                     several lines (keep the indentation)

    *Returns:*

    Here we describe the return value

    *Exemple:*

    [3 backticks]
    Here you can put your code
    [3 backticks]

    **Note: You can add informations at the end of the docstring,
            The name must be inside the following values:
            [Note|Seealso|Warning|Todo]
    '''

Unit tests
----------

To run the unit tests, execute the following command:

.. code:: bash

    python setup.py test

Dependancies
------------

-  `CVulkan <https://realitix.github.io/cvulkan/>`__: C module to
   communicate with Vulkan SDK
-  `VulkBare <https://realitix.github.io/vulk-bare/>`__: C module
   providing helper functions

Stay in touch
-------------

You can contact me by opening issue (bug or interesting discussion about
the project). If you want a fast and pleasant talk, join the irc
channel: ``#vulk``. I'm connected from 9AM to 6PM (France).

.. |Build Status| image:: https://travis-ci.org/realitix/vulk.svg?branch=master
   :target: https://travis-ci.org/realitix/vulk
.. |Code Climate| image:: https://codeclimate.com/github/realitix/vulk/badges/gpa.svg
   :target: https://codeclimate.com/github/realitix/vulk
.. |Test Coverage| image:: https://codeclimate.com/github/realitix/vulk/badges/coverage.svg
   :target: https://codeclimate.com/github/realitix/vulk/coverage
.. |Issue Count| image:: https://codeclimate.com/github/realitix/vulk/badges/issue_count.svg
   :target: https://codeclimate.com/github/realitix/vulk
