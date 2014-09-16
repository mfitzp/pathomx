Creating Custom Tools
*********************

This is a brief guide to creating custom tools within Pathomx. This aspect of the software
is under heavy development and will become considerably easier in the future. However, if 
you need to create a custom tool *now* this is the way to do it.

## Do I need a custom tool?

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

## What do I need to get started?

Any standard installation of Pathomx will be OK. If you are using Python packages not 
in the standard installation you may need to use either the `developer installation`_ or 
add custom Python path definitions to Pathomx. But to learn the basics it's best to stick
to exploring with NumPy, SciPy and Pandas.

## The tool stub

All tools follow a basic structure we're going to call the *tool stub*. To get started on 
custom tool, simply download the `tool stub`_ to your local machine. Unzip the file
somewhere convenient, preferably in a specific folder for custom Pathomx tools. You should
end up with the following folder structure:

\<root>
   - __init__.py
   - stub.pathomx-plugin
   - stub.py
   - stub.md
   - stub_loader.py
   - icon.png







.. _tool stub: http://download.pathomx.org/tool_stub_3.0.0.zip

