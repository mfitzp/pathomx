.. role:: python(code)
   :language: python


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

``.pathomx-plugin`` indicates that this folder is a Pathomx plugin folder. It also holds some
metadata about the plugin in the `Wheezy`_ plugin format. However, you don't need to know about 
that to use it just make your changes to the example provided.

``__init__.py`` is an empty file required by Python to import the folder as a module. Leave empty.

``loader.py`` contains the code required to initialise the plugin and start up. You can also
define config panels, dialogs and custom views (figure plots, etc.) in this file. 

``stub.py`` contains the actual code for the tool that will run on the IPython kernel. 
``stub.md`` contains the descriptive text in `Markdown`_ format.

``icon.png`` is the default icon for all tools in this plugin. You can add other icons and define them
specifically on a per-tool basis if you require.

You can have more than one tool per plugin using the same loader to initialise them all. 
This is useful when you have a number of tools that are conceptually related. This is 
seen in the standard 'Spectra' toolkit that offers a number of tools for dealing with frequency data.

Customising the stub
--------------------

To create your custom tool start with the stub file and customise from there. For this demo we'll
create a custom tool that randomly reorders and drops data on each iteration. We'll call
it 'Gremlin'.

Open up the ``.pathomx-plugin`` file and edit the metadata. The only line 
you have to edit is ``Name`` but feel free to edit the other data to match.
Do not change the ``Module`` line as this is needed to load the tool. Next 
rename ``stub.md`` and ``stub.py`` to `gremlin.md` and ``gremlin.py`` 
respectively. Then open up ``loader.py`` in a suitable text editor. We're
going to add some features to the Gremlin tool to show how it is done.

In the ``loader.py`` file you will find the following:

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


There are two parts to the tool. The ``StubTool`` class that defines the tool
and configures set up, etc. and the ``Stub`` loader which handles 
registration of the launcher for creating new instances of the tool. You
can define as many tools in this file as you want (give them unique names)
and register them in the same Stub class __init__.

The name of the tool is defined by the ``name`` parameter to the tool definition.
If none is supplied the tool will take the name of the plugin by default.
The ``shortname`` defines the name of the files that source code and information
text are loaded from e.g. ``stub.py`` and ``stub.md``. So change the ``shortname`` value
to *gremlin* and the ``name`` to *Gremlin*.

Below is this is the default config definition. Here you can set default
values for any configuration parameters using standard Python dictionary syntax. 
We'll add a parameter ``evilness`` that defines how much damage the gremlin
does to your data, and ``gremlin_type`` that defines what it does. Edit the :python:`self.config` definition to:

.. code-block:: python

            self.config.set_defaults({
            'gremlin_type': 1,
            'evilness': 1,
            })

We've defined the parameters and given them both a default value of 1. These will
now be available from within the run kernel as :python:`config['evilness']` and 
:python:`config['gremlin_type']`.

Below the config definition there are two lines defining the input and output ports
of the tool respectively. You can name them anything you like as long as 
you follow standard Python variable naming conventions. Data will be passed
into the run kernel using these names. They are defined as :python:`input_data` and 
:python:`output_data` by default and that is enough for our gremlin tool. 

How to train your Gremlin
-------------------------

The runnable source code for tools is stored in a file named `<shortname>.py` in
standard Python script style. We've already renamed `stub.py` to `gremlin.py`
so you can open that now. In it you'll find:

.. code-block:: python

    import pandas as pd
    import numpy as np
    import scipy as sp

    # This is your stub source file. Add your code here!

That does not a lot. The first three lines simply import a set of standard
libraries for working with data: `Pandas`_, `NumPy`_ and `SciPy`_. You might
not need them all but it's worth keeping them available for now. To start
our custom tool we need to add some code to mess up the data. First we need
a copy of the input_data to output, then we want to mess it up. Add the 
following code to the file:

.. code-block:: python

    import pandas as pd
    import numpy as np
    import scipy as sp

    # This is your stub source file. Add your code here!

    from random import randint, choice

    # Define the gremlin types, these must be matched in the
    # loader config definition
    GREMLIN_RANDOM = 1
    GREMLIN_DELETE_ROW = 2
    GREMLIN_DELETE_COLUMN = 3
    GREMLIN_RANDOM_ROWS = 4
    GREMLIN_RANDOM_COLUMNS = 5

    output_data = input_data

    # Repeat the gremlin action 'evilness' times
    for n in range( config['evilness'] ):

        if config['gremlin_type'] == 1:
            gremlin_type = randint(1,5)
        else:
            gremlin_type = config['gremlin_type']
    
        if gremlin_type == GREMLIN_DELETE_ROW:
            # Delete random row(s) in the pandas dataframe
            output_data.drop( choice( output_data.columns ), axis=1, inplace=True )
        
        elif gremlin_type == GREMLIN_DELETE_COLUMN:
            # Delete random column(s) in the pandas dataframe
            output_data.drop( choice( output_data.index ), inplace=True )
        
        elif gremlin_type == GREMLIN_RANDOM_ROWS:
            # Randomly switch two rows' data
            if output_data.shape[0] < 2:
                raise Exception('Need at least 2 rows of data to switch')
            
            i1 = randint(0, output_data.shape[0]-1)
            i2 = randint(0, output_data.shape[0]-1)

            output_data.iloc[i1,:], output_data.iloc[i2,:] = output_data.iloc[i2,:], output_data.iloc[i1,:]
        

        elif gremlin_type == GREMLIN_RANDOM_COLUMNS:
            # Randomly switch two columns' data
            if output_data.shape[0] < 2:
                raise Exception('Need at least 2 columns of data to switch')

            i1 = randint(0, output_data.shape[0]-1)
            i2 = randint(0, output_data.shape[1]-1)
    
            output_data.iloc[:,i1], output_data.iloc[:,i2] = output_data.iloc[:,i2], output_data.iloc[:,i1]
    

    # Generate simple result figure (using pathomx libs)
    from pathomx.figures import spectra

    View = spectra(output_data, styles=styles);


This is the main guts of our gremlin. A copy of the :python:`input_data` is made to :python:`output_data`
and then a simple loop iterates `evilness` times while performing 
some or other task on the :python:`output_data`. The choice of actions are: delete row,
delete column, switch two rows, switch two columns. An option is available to make a 
random selection from these transformations. Setting `evilness` to 10 and `gremlin_type` 
to 1 will perform 100 random operations on the data. Enough to drive anyone quite mad.

Finally, we use built in standard figure plotting tools to output a view of the transformed data.

Initial test
------------

To see what damage the gremlin can do we need a set of data to work with. Download the
`sample dataset`_, a set of processed 2D JRES NMR data with class assignments already applied.

Start up Pathomx as normal. Before we can use our Gremlin tool we'll need to tell Pathomx
where to find it so it can be loaded. On the main toolbar select "Plugins" then "Manage plugins..."
to get to the plugin management view. Here you can activate and deactivate different plugins
and add/remove them from the Toolkit view. To find the Gremlin tool we'll need to tell Pathomx
about the folder it is in. 

Add the folder containing the Gremlin tool, or alternatively a parent folder if you want to create
more tools in the same place. Pathomx will automatically search through the entire tree
to find plugins so it's probably best not to add an entire drive. 

Once added the plugin list will refresh and be listed (and automatically activated) in the plugin list.
You can now close the plugin management list and see that your new tool is ready and waiting in 
the Toolkit viewer. It will be there every time you run Pathomx.

Drag it into the workspace and click on it. You'll notice that there isn't much to see: there is
no configuration UI defined and we haven't updated the about text. But it's still a fully-operational
gremlin. So let's see it in action.

Drag an *Import Text/CSV* tool into the workspace and select it. Using the open file widget
select the file you downloaded earlier containing the demo dataset. Have a look at the Spectra 
view output to see how it *should* look.

Now drag from the *Import Text/CSV* ``output_data` port to the Gremlin ``input_data`` port.
The gremlin tool will automatically calculate using the new data and display a modified plot
called 'View'. If you can't see the different between this and the earlier plot try pressing
the green *play* button a few times to re-run the tool. You should see the data change each
time.


















.. _tool stub: http://download.pathomx.org/tool_stub_3.0.0.zip
.. _Markdown: 
.. 


