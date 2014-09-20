Getting Started
===============

This is quick start-up guide for new users of `Pathomx`_. In here you should find everything
you need to know to start using Pathomx right away. Once you've been through the basics
you might like to see some of the `demo workflows`_ to see what Pathomx is capable of.

Pathomx aims to offer a powerful, extensible analysis and processing platform while being
as simple to use as possible to the casual user. It should be possible to pick up Pathomx,
use the built-in - or bioinformatician provided - tools and perform a complete analysis
in a matter of minutes. Saved workflows should be simple to use, reliable and reproducible.
Outputs should be beautiful.

If Pathomx fails for you on any of those points, please do `file a bug report`_ and it'll 
be sorted out as soon as humanly possible.

First steps
-----------

Before you can start you'll need to `install the software`_. There are a few different ways
to install Pathomx but they make no difference to how you'll use it.

Nomenclature
------------

In Pathomx nomenclature *toolkits* provide *tools* with which you can construct
*workflows*. 

Your currently available tools are shown in the *Toolbox* within the application and can
be dragged into the workspace to use. Once in the workflow tools can be dragged and rearranged
as you like, the position of the tool has no effect on function. 

Each tool has a number (0-infinity) of *ports* for *input* and *output*. Data is taken in
via an input port, processed by the tool in some way, and passed out of the output port.

The output of one tool can be connected to the input of another by *connectors*.




.. _Pathomx: http://pathomx.org
.. _file a bug report: http://github.com/pathomx/pathomx/issues/
.. _install the software: install.html