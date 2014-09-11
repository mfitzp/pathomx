MetaViz
=======

Metabolic pathway visualisation and analysis powered by GraphViz.  
[Martin A. Fitzpatrick][]

Introduction
------------

Select ‘Pathways’ to show from the config panle.

This displays the pathway selection dialog where you can opt to show any pathways currently in the local database. You can select individual pathways by clicking, or select multiple pathways with Option-click (Mac) or Ctrl-click (Windows). You can also bulk add/remove pathways using the search box beneath. This optionally supports regular expressions allowing for specific matching of complex names.

You can also opt to hide specific pathways from view. Pathways selected in this dialog will not be displayed (even if specifically requested in the show pathway box. You may find this useful if you are working on cells or organisms that do not feature particular pathways.

Back on the ‘Pathways’ menu you can also opt to ‘Highlight Reaction Pathways’ to color pathways by colour and to ‘Show Links to Hidden Pathways’ which shows links from metabolites to currently invisible pathways. This can be useful to see currently hidden links between metabolites. *Note: This can sometimes take a while to complete, particularly on large maps.* Pathway nodes can be clicked to access database metadata.

You can also simplify/further annotation the pathway map using the config panel including adding 2° metabolites, enzymes/reaction names, and pathway-analysis hints showing metabolite connectivity.

*Note: Pathomx’s choices for color-scale may be overridden if required from the data menu.*

Metabolite concentration delta (difference between control and test) is shown on the metabolic pathway map by colour scale with blue indicating down and red up. 


  [Martin A. Fitzpatrick]: http://martinfitzpatrick.name/