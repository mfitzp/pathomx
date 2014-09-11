Text/CSV
========

Import data from flat-file text/CSV. By [Martin A. Fitzpatrick][]

Introduction
------------

This plugin supports loading in data from CSV in a standardised format, with support for labels, classes, scales and data points. You can use this plugin to import data from any source not supported by other plugins by rearranging the data in Excel to fit the template and saving the file as CSV. Loading is semi-intelligent and will attempt to determine how you’ve laid out the data from headers, etc.

File Format
-----------

The format for import is as follows:

<table>
<tbody>
<tr class="odd">
<td align="left">Sample/Experiment ID</td>
<td>Classification</td>
<td>Glucose</td>
<td>Citrate</td>
<td>Oxaloacetate</td>
<td>Pyruvate</td>
<td>…N</td></tr><tr>
<td align="left">1</td>
<td>A</td>
<td>0.4324</td>
<td>0.2343</td>
<td>1.2323</td>
<td>0.9393</td>
<td>0.8823</td></tr><tr>
<td align="left">2</td>
<td>B</td>
<td>0.4030</td>
<td>0.2675</td>
<td>0.5055</td>
<td>0.9342</td>
<td>0.8393</td></tr><tr>
<td align="left">3</td>
<td>B</td>
<td>0.4342</td>
<td>0.3565</td>
<td>0.5552</td>
<td>0.9787</td>
<td>0.8454</td></tr><tr>
<td align="left">…</td>
<td>…</td>
<td>…</td>
<td>…</td>
<td>…</td>
<td>…</td>
<td>…</td>
</tr>
</tbody>
</table>

Note: This layout can be transposed (i.e. with rows as columns and vice versa) if required to fit within the limits of Excel. The correct orientation will be detected and imported data transposed back if neccessary.

Quick start
-----------

Arrange data in the correct layout format within Excel and export as CSV. Load the file using this plugin and the data will be displayed on the ‘Table’ tab. If your data appears to have a continuous scale (e.g. a spectra) a visualisation of this will be shown. If the data cannot be loaded/interpreted correctly an error message will be displayed to try and help.

  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/