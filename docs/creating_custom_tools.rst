Creating Custom Tools
=====================

This is a brief guide to creating custom tools within Pathomx. This aspect of the software
is under heavy development and will become considerably easier in the future. However, if 
you need to create a custom tool *now* this is the way to do it.

Do I need a custom tool?
------------------------

Custom tools allow you to access the full capabilities of the Pathomx software. The goal 
of a custom tool will be to create a reusable component that you can use, re-use and share
with other users of the software (preferably by adding it to the main repository). In particular
they give you access to - 

- Tool configuration including widgets (control panels) and defaults
- Define custom plots + plot types

You don't need to create a custom tool if you just want to -

- Do some custom scripting
- Do a one-off custom plot
- Do a one-off anything

For those type of things you're better off just using the built-in *custom script* tool.

What do I need to get started?
------------------------------

Any standard installation of Pathomx will be OK. If you are using Python packages not 
in the standard installation you may need to use either the `developer installation`_ or 
add custom Python path definitions to Pathomx. But to learn the basics it's best to stick
to exploring with NumPy, SciPy and Pandas.

The tool stub
-------------

All tools follow a basic structure we're going to call the *tool stub*. To get started on 
custom tool, simply download the `tool stub`_ to your local machine. Unzip the file
somewhere convenient, preferably in a specific folder for custom Pathomx tools. You should
end up with the following folder structure:

\<root>
   - .pathomx-plugin
   - __init__.py
   - loader.py
   - stub.py
   - stub.md
   - icon.png

A brief description of each follows - 

`.pathomx-plugin` indicates that this folder is a Pathomx plugin folder. It also holds some
metadata about the plugin in the `Wheezy`_ plugin format. However, you don't need to know about 
that to use it just make your changes to the example provided.

`__init__.py` is an empty file required by Python to import the folder as a module. Leave empty.

`loader.py` contains the code required to initialise the plugin and start up. You can also
define config panels, dialogs and custom views (figure plots, etc.) in this file. 

`stub.py` contains the actual code for the tool that will run on the IPython kernel. 
`stub.md` contains the descriptive text in `Markdown`_ format.

`icon.png` is the default icon for all tools in this plugin. You can add other icons and define them
specifically on a per-tool basis if you require.

You can have more than one tool per plugin using the same loader to initialise them all. 
This is useful when you have a number of tools that are conceptually related. This is 
seen in the standard 'Spectra' toolkit that offers a number of tools for dealing with frequency data.

Customising the stub
--------------------

To create your custom tool start with the stub file and customise from there. For this demo we'll
create a custom tool that randomly reorders and drops data on each iteration. We'll call
it 'Gremlin'.

Open up the `.pathomx-plugin` file and edit the metadata. The only line 
you have to edit is `Name` but feel free to edit the other data to match.
Do not change the `Module` line as this is needed to load the tool. Next 
rename `stub.md` and `stub.py` to `gremlin.md` and `gremlin.py` 
respectively. Then open up `loader.py` in a suitable text editor. We're
going to add some features to the Gremlin tool to show how it is done.

In the `loader.py` file you will find the following:

.. code-block:: python

    class StubTool(GenericTool):
        name = "Stub"
        shortname = 'stub'

        def __init__(self, *args, **kwargs):
            super(StubTool, self).__init__(*args, **kwargs)

            self.config.set_defaults({
            })

            self.data.add_input('input_data')  # Add input slot
            self.data.add_output('output_data')  # Add output slot

    class Stub(ProcessingPlugin):

        def __init__(self, *args, **kwargs):
            super(Stub, self).__init__(*args, **kwargs)
            self.register_tool_launcher(StubTool)


There are two parts to the tool. The `StubTool` class that defines the tool
and configures set up, etc. and the `Stub` loader which handles 
registration of the launcher for creating new instances of the tool. You
can define as many tools in this file as you want (give them unique names)
and register them in the same Stub class __init__.

The name of the tool is defined by the `name` parameter to the tool definition.
If none is supplied the tool will take the name of the plugin by default.
The `shortname` defines the name of the files that source code and information
text are loaded from e.g. `stub.py` and `stub.md`. So change the `shortname` value
to 'gremlin' and the `name` to 'Gremlin'.

Below is this is the default config definition. Here you can set default
values for any configuration parameters using standard Python dictionary syntax. 
We'll add a parameter `evilness` that defines how much damage the gremlin
does to your data. Edit the `self.config` definition to:

.. code-block:: python

            self.config.set_defaults({
            'evilness': 1,
            })

We've defined the parameter and given it a default value of 1. This will
now be available from within the run kernel as `config['evilness']`.

Below the config definition there are two lines defining the input and output ports
of the tool respectively. You can name them anything you like as long as 
you follow standard Python variable naming conventions. Data will be passed
into the run kernel using these names. They are defined as `input_data` and 
`output_data` by default and that is enough for our gremlin tool. 
















.. _tool stub: http://download.pathomx.org/tool_stub_3.0.0.zip
.. _Markdown: 
.. 
