#!/usr/bin/env python

# wxWidgets based GUI for MetaPath
# Output the data to running ubigraph server to visualise
from __future__ import unicode_literals

import os, sys, re, math
import wx
import wx.html2
import wx.grid
import wx.lib.agw.flatnotebook as fnb
import wx
import pydot
import urllib2
from optparse import Values
from collections import defaultdict
from wx.html import HtmlEasyPrinting

# wheezy templating engine
from wheezy.template.engine import Engine
from wheezy.template.ext.core import CoreExtension
from wheezy.template.loader import FileLoader

# MetaPath classes
import db, data, core, utils, layout

METAPATH_PRUNING_TYPE_CODE = ('c', 'u', 'd', 'm')
METAPATH_PRUNING_TYPE_TEXT = (
    'Metabolite change scores for pathway',
    'Metabolite up-regulation scores for pathway', 
    'Metabolite down-regulation scores for pathway',
    'Number metabolites with data per pathway',
)


# Generic configuration dialog handling class
class genericDialog(wx.Dialog):
    def __init__(self, parent, **kwargs):
        # Now process the parent's init to get the gridsizer populated
        wx.Dialog.__init__(self, parent, style=wx.DEFAULT_DIALOG_STYLE, **kwargs)

        self.layout = wx.BoxSizer(wx.VERTICAL)
        # Setup default button configurations etc.
        self.buttonSizer = wx.BoxSizer(wx.HORIZONTAL)
        self.buttonSizer.AddMany([
            (wx.Button(self, wx.ID_OK), 0, wx.ALL, 5),
            (wx.Button(self, wx.ID_CANCEL), 0, wx.ALL, 5),
            ])
        
        self.sizer = wx.BoxSizer(wx.VERTICAL)
        self.SetSizer(self.sizer)

        self.parent = parent


    def dialogFinalise(self):
        self.sizer.AddMany([
            (self.layout, 0, wx.ALIGN_CENTER | wx.ALL, 20),
            (self.buttonSizer, 0, wx.ALIGN_CENTER | wx.ALL, 20),
        ])
        self.Fit() 

    def setListControl(self, control, list, checked):
        # Automatically set List control checked based on current options list
        items = control.GetItems()
        try:
            idxs = [items.index(e) for e in list]
            for idx in idxs:
                if checked:
                    control.Select(idx)
                else:
                    control.Deselect(idx)
        except:
            pass

      
class dialogDefineExperiment(genericDialog):
    
    def filter_classes_by_timecourse_regexp(self, e):
        try:
            rx = re.compile('(?P<timecourse>%s)' % self.timecourseRegExp.GetValue())                
        except:
            return
        
        filtered_classes = list( set(  [rx.sub('',c) for c in self.classes] ) )
        self.classctrlChoice.SetItems( filtered_classes )
        self.classtestChoice.SetItems( filtered_classes )
        

    def __init__(self, parent, **kwargs):
        genericDialog.__init__(self, parent, **kwargs)
        
        self.classes = sorted( parent.data.classes )
        self.SetTitle("Define Experiment")
        

        fgs = wx.FlexGridSizer(2,2)
        #fgs.AddGrowableCol(0)

        self.timecourseRegExp = wx.TextCtrl(self, wx.ID_ANY, size=(100,-1), value=parent.experiment['timecourse'] if 'timecourse' in parent.experiment else '' )
        self.Bind(wx.EVT_TEXT, self.filter_classes_by_timecourse_regexp, self.timecourseRegExp)

        self.classctrlChoice = wx.Choice(self, wx.ID_ANY, choices = self.classes, style=wx.CB_SORT, size=(100,-1) )
        self.classtestChoice =  wx.Choice(self, wx.ID_ANY, choices = self.classes, style=wx.CB_SORT, size=(100,-1) )

        fgs.AddMany([
            ( wx.StaticText(self, wx.ID_ANY, "Control:"), 0 ),
            ( wx.StaticText(self, wx.ID_ANY, "Test:"), 0 ),
            ( self.classctrlChoice, 0 ),
            ( self.classtestChoice, 0 ),
            ])
        
        # Pre-select already selected options in the list (using regexp here, fugly)
        # current_pathways = parent.config.Read('/Pathways/Show')
        # self.setListControl( self.pathwayListBox, current_pathways.split('$|^'), checked=True )
        
        # finally, put the notebook in a sizer for the panel to manage
        # the layout
        self.layout.AddMany([
          #  ( wx.StaticText(self, wx.ID_ANY, "Select pathways to display:") ), 
          #  ( self.pathwayListBox, 1, wx.EXPAND ),
          #  ( wx.StaticText(self, wx.ID_ANY, "Add/remove pathways matching (regexp):")),
             ( fgs, 0, wx.ALL | wx.EXPAND ),
            ( wx.StaticLine(self, size=(-1,20) ), ),
            ( wx.StaticText(self, wx.ID_ANY, "Timecourse filter (regexp):"), 0 ),
            ( self.timecourseRegExp, 0, wx.ALL | wx.EXPAND, 5),
        ])

        # Stack it all up, with extra buttons
        self.dialogFinalise()


class dialogpanelShowPathwaysShowHide(wx.Panel):
    def __init__(self, context, parent ):
        wx.Panel.__init__(self, parent)
        self.context = context
        self.layout = wx.BoxSizer(wx.VERTICAL)
        
        fgs = wx.FlexGridSizer(1,3)
        fgs.AddGrowableCol(0)
        
        self.regexpText = wx.TextCtrl(self, wx.ID_ANY )
        regexpRemove = wx.Button(self, wx.ID_ANY, "-", style=wx.BU_EXACTFIT)
        regexpRemove.Bind(wx.EVT_BUTTON, self.OnRegexpRemove)
        regexpAdd = wx.Button(self, wx.ID_ANY, "+", style=wx.BU_EXACTFIT)
        regexpAdd.Bind(wx.EVT_BUTTON, self.OnRegexpAdd)

        fgs.AddMany([
            ( self.regexpText, 1, wx.EXPAND ),
            ( regexpRemove, 1),
            ( regexpAdd, 1),
            ])
        
        self.pathwayListBox = wx.ListBox(self, wx.ID_ANY, choices = [], style=wx.LB_EXTENDED | wx.LB_SORT, size=(400,200) )

        # finally, put the notebook in a sizer for the panel to manage
        # the layout
        self.layout.AddMany([
            ( wx.StaticText(self, wx.ID_ANY, "Select pathways to display:") ), 
            ( self.pathwayListBox, 1, wx.EXPAND ),
            #( wx.StaticLine(self, size=(-1,20) ), ),
            ( wx.StaticText(self, wx.ID_ANY, "Add/remove pathways matching (regexp):")),
            ( fgs, 0, wx.ALL | wx.EXPAND ),
        ])  
        
        self.SetSizer(self.layout)
        
    def OnRegexpAdd(self,e):
        pathway_re = re.compile( self.regexpText.GetValue(), flags=re.IGNORECASE)
        # Match the regexp against the list of pathways in the table
        matches = filter(lambda x:pathway_re.search(x), self.pathwayListBox.GetItems())
        self.context.setListControl( self.pathwayListBox, matches, checked=True )
    
    def OnRegexpRemove(self,e):
        pathway_re = re.compile( self.regexpText.GetValue(), flags=re.IGNORECASE)
        # Match the regexp against the list of pathways in the table
        matches = filter(lambda x:pathway_re.search(x), self.pathwayListBox.GetItems())
        self.context.setListControl( self.pathwayListBox, matches, checked=False )


            
          
        
class dialogPathwaysShow(genericDialog):
    def __init__(self, parent, **kwargs):
        genericDialog.__init__(self, parent, **kwargs)
        
        self.SetTitle("Select Pathways to Display")
        
        nb = wx.Notebook(self)
        # create the page windows as children of the notebook
        # add the pages to the notebook with the label to show on the tab
        self.dlgpShow = dialogpanelShowPathwaysShowHide(self, nb)
        self.dlgpHide = dialogpanelShowPathwaysShowHide(self, nb)
        nb.AddPage(self.dlgpShow, "Show")
        nb.AddPage(self.dlgpHide, "Hide")

        #all_pathways = parent.db.pathways.keys()
        all_pathways = [p.name for p in parent.db.pathways.values()]
        # Populate the list boxes
        self.dlgpShow.pathwayListBox.AppendItems( all_pathways )
        self.dlgpHide.pathwayListBox.AppendItems( all_pathways )
        #Get current items from settings, a list of pathway IDs
        show_pathways = parent.config.Read('/Pathways/Show').split(',')
        hide_pathways = parent.config.Read('/Pathways/Hide').split(',')
        
        # Pre-select already selected options in the list (using regexp here, fugly)
        self.setListControl( self.dlgpShow.pathwayListBox, [parent.db.pathways[x].name for x in show_pathways if x in parent.db.pathways], checked=True )
        self.setListControl( self.dlgpHide.pathwayListBox, [parent.db.pathways[x].name for x in hide_pathways if x in parent.db.pathways], checked=True )

        # Add checklists to add/remove key pathways by established groups
        keypathways = {
            'Central metabolism':{
                'Glycolysis':[],
                'Citric acid cycle':[],
                'Ketogenesis':[],
                },
            'Amino acid':{
                'Amino acid biosynthesis':[],
                'Amino acid degradation':[],
                },
            'Miscellaneous':{
                'Urea cycle':[],
                },
            }        
        
        self.layout.Add(nb)
        # Stack it all up, with extra buttons
        self.dialogFinalise()



class dialogDataPruning(genericDialog):
    def __init__(self, parent, **kwargs):
        genericDialog.__init__(self, parent, **kwargs)
        self.parent = parent
        
        self.SetTitle("Setup for Data-based Pathway Pruning")

        #pruning_types, pruning_text = METAPATH_PRUNING_TYPES.keys(), METAPATH_PRUNING_TYPES.values()
        self.pruningChoice = wx.Choice( self, wx.ID_ANY, choices = METAPATH_PRUNING_TYPE_TEXT, size=(200,-1)) 
        
        # Pre-select already selected options in the list (using regexp here, fugly)
        current_pruning = parent.config.Read('/Data/PruningType')

        self.pruningChoice.SetSelection( METAPATH_PRUNING_TYPE_CODE.index( current_pruning ) )
        self.pruningRelative = wx.CheckBox( self, wx.ID_ANY, label='Relative score to pathway size') 
        self.pruningRelative.SetValue( parent.config.ReadBool('/Data/PruningRelative') )
        self.pruningDepth = wx.SpinCtrl( self, wx.ID_ANY)#, label='Pathways to retain when pruning')
        self.pruningDepth.SetRange(0,999)
        self.pruningDepth.SetValue( parent.config.ReadInt('/Data/PruningDepth') )
        
        # finally, put the notebook in a sizer for the panel to manage
        # the layout
        self.layout.AddMany([
            ( wx.StaticText(self, wx.ID_ANY, "Select scoring method:") ), 
            ( self.pruningChoice, 1, wx.EXPAND ),
            ( self.pruningRelative, 1, wx.EXPAND, wx.TOP, 5),
            ( wx.StaticText(self, wx.ID_ANY, "Number of pathways to retain:"), 1, wx.TOP, 15 ), 
            ( self.pruningDepth, 1, wx.EXPAND ),
        ])
        
        # Stack it all up, with extra buttons
        self.dialogFinalise()
        
    def OnRegexpAdd(self,e):
        pathway_re = re.compile( self.regexpText.GetValue(), flags=re.IGNORECASE)
        # Match the regexp against the list of pathways in the table
        matches = filter(lambda x:pathway_re.match(x), self.pathwayListBox.GetItems())
        self.setListControl( self.pathwayListBox, matches, checked=True )
    
    def OnRegexpRemove(self,e):
        pathway_re = re.compile( self.regexpText.GetValue(), flags=re.IGNORECASE)
        # Match the regexp against the list of pathways in the table
        matches = filter(lambda x:pathway_re.match(x), self.pathwayListBox.GetItems())
        self.setListControl( self.pathwayListBox, matches, checked=False )
        







########################################################################
class MainWindow(wx.Frame):
    def __init__(self, parent, title):
        wx.Frame.__init__(self, parent, title=title, size=(800,600))

        self.icon = wx.Icon( os.path.join( utils.scriptdir,'static','icon.png') , wx.BITMAP_TYPE_PNG)
        self.SetIcon(self.icon)

        statusBar = self.CreateStatusBar() # A Statusbar in the bottom of the window

        # Central variable for storing application configuration (load/save from file?
        self.config = wx.Config("MetaPath") #style=wx.CONFIG_USE_LOCAL_FILE)
        self.configIdStore = dict()
        #self.config.WriteBool('/MetaPath/Is_Setup', False)
        if not self.config.ReadBool('/MetaPath/Is_Setup', False):
            # Defaults not set, apply now and save complete config file
            self.config.Write('/Pathways/Show', '') 
            # self.config.WriteBool('/Pathways/ShowAll', False)
            self.config.WriteBool('/Pathways/ShowColors', True)
            self.config.WriteBool('/Pathways/ShowLinks', False)

            self.config.WriteBool('/Data/PruningActive', False)
            self.config.WriteInt('/Data/PruningDepth', 5)
            self.config.Write('/Data/PruningType', 'c')

            self.config.WriteBool('/View/ShowEnzymes', True)
            self.config.WriteBool('/View/Show2nd', True)
            self.config.WriteBool('/View/ShowAnalysis', True)
            
            self.config.WriteBool('/MetaPath/Is_Setup', True)
        
        self.standardPaths = wx.StandardPaths.Get() 
        
        # Create database accessor
        self.db = db.databaseManager()
        self.data = None #data.dataManager() No data loaded by default
        self.experiment = dict()
        self.layout = None # No map by default

        # Create templating engine
        self.templateEngine = Engine(
            loader=FileLoader( [os.path.join( utils.scriptdir,'html')] ),
            extensions=[CoreExtension()]
        )

        # Creating the menubar.
        menuBar = wx.MenuBar()

        # wx.ID_ABOUT and wx.ID_EXIT are standard IDs provided by wxWidgets.
        menuFile= wx.Menu()

        menuFileAbout = menuFile.Append(wx.ID_ABOUT, "&About"," Information about this program")
        self.Bind(wx.EVT_MENU, self.OnAbout, menuFileAbout)
        menuFileSave = menuFile.Append(wx.ID_SAVEAS,u'&Save As\u2026'," Save current metabolic pathway map in multiple formats")
        self.Bind(wx.EVT_MENU, self.OnSaveAs, menuFileSave)

        menuFileExit = menuFile.Append(wx.ID_EXIT,"E&xit"," Terminate the program")
        self.Bind(wx.EVT_MENU, self.OnExit, menuFileExit)

        menuBar.Append(menuFile,"&File")

        # PATHWAYS Menu
        menuPathways= wx.Menu()
        # menuPathwaysShowAll = self.setupMenuCheckBox(menuPathways, "&Show All"," Show all pathways", '/Pathways/ShowAll', True)
        menuPathwaysShow = menuPathways.Append(-1, u'&Show Selected Pathways\u2026'," Show specific pathways only")
        self.Bind(wx.EVT_MENU, self.OnPathwaysShow, menuPathwaysShow)        
        menuPathways.AppendSeparator()
        
        menuPathwaysShowLinks = self.setupMenuCheckBox(menuPathways, u'Show Links to Hidden Pathways'," Show links to pathways currently not visible", '/Pathways/ShowLinks', False)
        menuPathwaysShowColors = self.setupMenuCheckBox(menuPathways, u'Highlight Reaction Pathways'," Highlight pathway reactions by color", '/Pathways/ShowColors', True)
        menuPathways.AppendSeparator()
        menuPathwaysLayout = menuPathways.Append(-1, u'&Load predefined layout\u2026'," Load a pre-defined layout map file e.g KGML")
        self.Bind(wx.EVT_MENU, self.OnLoadLayoutFile, menuPathwaysLayout)        

        menuBar.Append(menuPathways,"&Pathways")

        # DATA Menu

        menuData= wx.Menu()
        menuDataActive = menuData.Append(-1, u'&Load Metabolite Data File\u2026'," Specify metabolite datafile in .csv format")
        self.Bind(wx.EVT_MENU, self.OnLoadDataFile, menuDataActive)
        self.menuDefineExperiment = menuData.Append(-1, u'&Define Experiment\u2026'," Define experiment for display")
        self.Bind(wx.EVT_MENU, self.OnDefineExperiment, self.menuDefineExperiment)

        #self.menuViewShowExperimentalData = self.setupMenuCheckBox(menuData, "Show &Experimental Data"," Show experimental data on map", '/View/ShowExperimentalData', True)

        menuData.AppendSeparator()
        menuDataPruningActive = self.setupMenuCheckBox(menuData, "&Enable Pathway Pruning"," Algorithmically prune pathways to key networks", '/Data/PruningActive', True)
        menuDataPruningSettings = menuData.Append(-1, u'&Pruning Settings\u2026'," Configure Data algorithm and depth")
        self.Bind(wx.EVT_MENU, self.OnPruningSettings, menuDataPruningSettings)
        #menuData.AppendSeparator()
        #menuDataMetaboliteId = menuData.Append(-1, u'&Manage Metabolite Identities\u2026'," Load a translation file for reference metabolites e.g. from ppm, or alternate naming conventions")
        menuBar.Append(menuData,"&Data")

        # VIEW Menu
        menuView= wx.Menu()
        menuViewShowEnzymes = self.setupMenuCheckBox(menuView, "Show &Enzymes"," Show reaction enzyme names", '/View/ShowEnzymes', True)
        menuViewShow2nd = self.setupMenuCheckBox(menuView, u'Show &2\u00B0 Metabolites'," Show secondary metabolites for reactions", '/View/Show2nd', False)
        menuView.AppendSeparator()
        menuViewShowAnalysis = self.setupMenuCheckBox(menuView, u'Show Network Analysis'," Show metabolite connectivity analysis  ", '/View/ShowAnalysis', True)
        menuView.AppendSeparator()

        menuViewRefresh = menuView.Append(wx.ID_REFRESH, "&Refresh"," Refresh pathway map")
        self.Bind(wx.EVT_MENU, self.OnRefresh, menuViewRefresh)

        menuBar.Append(menuView,"&View")

        # DATABASE Menu

        menuDatabase= wx.Menu()
        menuDatabaseLoadIdentities = menuDatabase.Append(-1, u"&Load Metabolite Identities\u2026"," Load additional metabolite identities, e.g. NMR ppm peak identities, or HMDB translations")
        self.Bind(wx.EVT_MENU, self.OnLoadIdentities, menuDatabaseLoadIdentities)
        menuDatabase.AppendSeparator()

        #menuDatabaseReload = menuDatabase.Append(-1, u'&Select Organism\u2026'," Select organism database")
        #menuDatabaseReload = menuDatabase.Append(-1, u'&Import Pathway/Reaction\u2026'," Select organism database")
        #menuDatabase.AppendSeparator()
        menuDatabaseReload = menuDatabase.Append(-1, "&Reload Database"," Reload the pathway database")
        self.Bind(wx.EVT_MENU, self.OnReloadDB, menuDatabaseReload)


        menuBar.Append(menuDatabase,"&Database") # Adding the "filemenu" to the MenuBar

        self.SetMenuBar(menuBar)  # Adding the MenuBar to the Frame content.

        tb = self.CreateToolBar( wx.TB_HORIZONTAL | wx.TB_TEXT)

        self.Bind(wx.EVT_MENU, self.OnSaveAs,  tb.AddLabelTool(wx.ID_ANY, 'Save As', wx.ArtProvider.GetBitmap(wx.ART_FILE_SAVE, wx.ART_TOOLBAR, (24,24)) ) )   
        self.Bind(wx.EVT_MENU, self.OnPrint,  tb.AddLabelTool(wx.ID_ANY, 'Print', wx.ArtProvider.GetBitmap(wx.ART_PRINT, wx.ART_TOOLBAR, (24,24)) ) )   
        self.Bind(wx.EVT_MENU, self.OnRefresh,  tb.AddLabelTool(wx.ID_ANY, 'Refresh', wx.ArtProvider.GetBitmap(wx.ART_REDO, wx.ART_TOOLBAR, (24,24)) ) )
        #self.Bind(wx.EVT_MENU, self.OnZoomOut,  tb.AddLabelTool(wx.ID_ANY, 'Zoom Out', wx.ArtProvider.GetBitmap(wx.ART_TIP, wx.ART_TOOLBAR, (24,24)) ) )
        #self.Bind(wx.EVT_MENU, self.OnZoomIn,  tb.AddLabelTool(wx.ID_ANY, 'Zoom In', wx.ArtProvider.GetBitmap(wx.ART_TIP, wx.ART_TOOLBAR, (24,24)) ) )

        #tb.AddControl( self.experimentDefinition )
        tb.AddStretchableSpace()  

        # Experiment
        self.Bind(wx.EVT_MENU, self.OnLoadDataFile,  tb.AddLabelTool(wx.ID_ANY, 'Load Data', wx.ArtProvider.GetBitmap(wx.ART_FILE_OPEN, wx.ART_TOOLBAR, (24,24)) ) )

        self.Bind(wx.EVT_MENU, self.OnDefineExperiment, tb.AddLabelTool(wx.ID_ANY, 'Experiment', wx.ArtProvider.GetBitmap(wx.ART_QUESTION, wx.ART_TOOLBAR, (24,24)) ) )
    
        self.cb_control = wx.Choice( tb, wx.ID_ANY, choices = [ ], style=wx.CB_SORT, size=(100,-1)) 
        self.cb_test = wx.Choice( tb, wx.ID_ANY, choices = [ ], style=wx.CB_SORT, size=(100,-1)) 
        self.Bind(wx.EVT_CHOICE, self.OnModifyExperiment, self.cb_control)
        self.Bind(wx.EVT_CHOICE, self.OnModifyExperiment, self.cb_test)
        
        tb_control = tb.AddControl(self.cb_control)  
        tb_test = tb.AddControl(self.cb_test)  
        
        tb_control.SetLabel('Control')
        tb_test.SetLabel('Test')
        
        # Pruning
        self.Bind(wx.EVT_MENU, self.OnPruningSettings, tb.AddLabelTool(wx.ID_ANY, 'Pruning', wx.ArtProvider.GetBitmap(wx.ART_CUT, wx.ART_TOOLBAR, (24,24)) ) )
        self.cb_prune = wx.SpinCtrl(tb, wx.ID_ANY)
        self.cb_prune.SetRange(0,999)
        self.cb_prune.SetValue( self.config.ReadInt('/Data/PruningDepth') )
        self.Bind(wx.EVT_SPINCTRL, self.OnModifyPruneDepth, tb.AddControl( self.cb_prune  ) )

        self.tb =tb
        tb.Realize()
        # Don't need this, using default toolbar setup
        #vbox.Add(self.toolbar, 0, wx.EXPAND)


        # SET UP MAIN WINDOW AREA
        # Split-window layout, right sidebar for info, log, other data etc.
        # Main window holds pathway overview

        vbox = wx.BoxSizer(wx.VERTICAL)
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        
        self.browser = wx.html2.WebView.New(self) 
        self.Bind(wx.html2.EVT_WEB_VIEW_NAVIGATING, self.OnBrowserNav, self.browser )
        self.Bind(wx.html2.EVT_WEB_VIEW_LOADED, self.OnBrowserNavDone, self.browser )
        hbox.Add(self.browser, 1, wx.EXPAND)
        
        # Display a introductory helpfile 
        template = self.templateEngine.get_template('welcome.html')
        self.browser.SetPage(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html')} ),"~") 

        self.sidebar = wx.html2.WebView.New(self, size=(300,-1)) 
        self.Bind(wx.html2.EVT_WEB_VIEW_NAVIGATING, self.OnBrowserNav, self.sidebar )
        hbox.Add(self.sidebar, 0, wx.EXPAND)

        # Display a sponsors
        template = self.templateEngine.get_template('sponsors.html')
        self.sidebar.SetPage(template.render( {'htmlbase': os.path.join( utils.scriptdir,'html')} ),"~") 
        
        
        vbox.Add(hbox, 1, wx.EXPAND)
        
        self.SetSizer(vbox)





    
    def setupMenuCheckBox(self, menu, menu_text, help_text, config_key, default_state):
        menuobj = menu.AppendCheckItem(-1, menu_text, help_text )
        self.configIdStore[menuobj.Id]=config_key
        self.Bind(wx.EVT_MENU, self.toggleCheck, menuobj)
        menuobj.Check( self.config.ReadBool(config_key, default_state) )
        return menuobj
        
    def toggleCheck(self, e):
        self.config.WriteBool( self.configIdStore[e.Id], e.IsChecked())
        # TODO: Regenerate the figure!
        self.generateGraphView()
               
    # UI Events           

    def OnPrint(self,e):
        self.browser.Print()
        
    def OnZoomOut(self,e):
        self.browser.SetZoom( self.browser.GetZoom()-1 )

    def OnZoomIn(self,e):
        self.browser.SetZoom( self.browser.GetZoom()+1 )

    def OnPathwaysShow(self,e):
        dlg = dialogPathwaysShow(self)
        if dlg.ShowModal() == wx.ID_OK:
            pathwayslist = dlg.dlgpShow.pathwayListBox.GetItems()
            # Show
            idx = dlg.dlgpShow.pathwayListBox.GetSelections()
            pathways = [self.db.synrev[ pathwayslist[x] ].id for x in idx]
            self.config.Write('/Pathways/Show', ','.join(pathways) )
            # Hide
            idx = dlg.dlgpHide.pathwayListBox.GetSelections()
            pathways = [self.db.synrev[ pathwayslist[x] ].id for x in idx]
            self.config.Write('/Pathways/Hide', ','.join(pathways) )
            # Generate
            self.generateGraphView()
        dlg.Destroy()

    def OnBrowserNav(self,e):
        # Interpret the (fake) URL to display Metabolite, Reaction, Pathway data in the sidebar interface
        # then block the continued loading
        url = e.GetURL()

        if url.startswith('metapath://'):
            self.browser.Stop()
            self.sidebar.Stop()
            # Take string from metapath:// onwards, split on /
            type, id, action = url[11:].split('/') # FIXME: Can use split here once stop using pathwaynames           

            
            # Add an object to the current view
            if action == 'add':
    
                # FIXME: Hacky test of an idea
                if type == 'pathway':
                    # Add the pathway and regenerate
                    pathways = self.config.Read('/Pathways/Show').split(',')
                    pathways.append( urllib2.unquote(id) )
                    self.config.Write('/Pathways/Show', ','.join(pathways) )
                    self.generateGraphView()   

            # Remove an object to the current view
            if action == 'remove':
    
                # FIXME: Hacky test of an idea
                if type == 'pathway':
                    # Add the pathway and regenerate
                    pathways = self.config.Read('/Pathways/Show').split(',')
                    pathways.remove( urllib2.unquote(id) )
                    self.config.Write('/Pathways/Show', ','.join(pathways) )
                    self.generateGraphView()

            # View an object
            if action == 'view':
                if type == 'pathway':
                    pathway = self.db.pathways[id]
                    self.generateSidebarView(template='pathway.html', data={
                        'title': pathway.name,
                        'object': pathway,
                        })
                elif type == 'reaction':
                    reaction = self.db.reactions[id]
                    self.generateSidebarView(template='reaction.html', data={
                        'title': reaction.name,
                        'object': reaction,
                        })
                elif type == 'metabolite':
                    metabolite = self.db.metabolites[id]
                    self.generateSidebarView(template='metabolite.html', data={
                        'title': metabolite.name,
                        'object': metabolite,
                        })
                        
                # Store URL so we can reload the sidebar later
                self.sidebar.CurrentURL = url
        
                        
        elif not url.startswith('file://'):
            # It's an URL open in default browser
            wx.LaunchDefaultBrowser(url)
            self.browser.Stop()
            self.sidebar.Stop()

             
    def OnBrowserNavDone(self,e):
        # Reload the sidebar on main window refresh: this is only bound to the main window so no need to check for action
        if hasattr(self.sidebar, 'CurrentURL'): # We've previously loaded a sidebar, stored the URL here
            self.sidebar.LoadURL( self.sidebar.CurrentURL )


    def OnLoadIdentities(self,e):
        """ Open a data file"""
        self.dirname = ''
        dlg = wx.FileDialog(self, "Load metabolite identities file", self.dirname, "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetFilename()
            dirname = dlg.GetDirectory()
            fn = os.path.join(dirname, filename)
            self.db.load_synonyms(fn)
            # Re-translate the datafile
            self.data.translate(self.db)
            self.generateGraphView()                
                    
        dlg.Destroy()

               
    def OnLoadDataFile(self,e):
        """ Open a data file"""
        self.dirname = ''
        dlg = wx.FileDialog(self, "Open experimental metabolite data file", self.dirname, "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetFilename()
            dirname = dlg.GetDirectory()
            fn = os.path.join(dirname, filename)
            self.data = data.dataManager(fn)
            # Re-translate the datafile
            self.data.translate(self.db)
            self.SetTitle('MetaPath: %s' % self.data.filename)
            self.cb_control.Set( sorted(self.data.classes) )
            self.cb_test.Set( sorted(self.data.classes) )

            self.OnDefineExperiment(e)
                    
        dlg.Destroy()
        
    def OnLoadLayoutFile(self,e):
        """ Open a map (layout) file"""
        self.dirname = ''
        dlg = wx.FileDialog(self, "Open layout file", self.dirname, "", "*.*", wx.OPEN)
        if dlg.ShowModal() == wx.ID_OK:
            filename = dlg.GetFilename()
            dirname = dlg.GetDirectory()
            fn = os.path.join(dirname, filename)
            self.layout = layout.layoutManager(fn)
            # Re-translate the datafile
            self.layout.translate(self.db)
            # Regenerate the graph view
            self.generateGraphView()            
                    
        dlg.Destroy()
        
    def OnDefineExperiment(self,e):
        """ Open the experimental setup dialog to define conditions, ranges, class-comparisons, etc. """
        dlg = dialogDefineExperiment(self)
        if dlg.ShowModal() == wx.ID_OK:

            self.cb_control.SetItems( dlg.classctrlChoice.GetItems() )
            self.cb_test.SetItems( dlg.classtestChoice.GetItems() )
            self.experiment['timecourse'] = dlg.timecourseRegExp.GetValue()
        
            classes = dlg.classctrlChoice.GetItems()
            self.experiment['control'] = [ classes[dlg.classctrlChoice.GetSelection() ] ]
            self.experiment['test'] = [ classes[dlg.classtestChoice.GetSelection() ] ]               
            self.generateGraphView()
            # Update the toolbar dropdown to match
            self.cb_control.SetSelection( dlg.classctrlChoice.GetSelection() )
            self.cb_test.SetSelection( dlg.classtestChoice.GetSelection() )
            # Regenerate the graph view
            self.generateGraphView()            
        dlg.Destroy()
        
    def OnModifyExperiment(self,e):
        """ Change control or test settings from toolbar interaction """
        # Cheat a bit, simply change both - only one will be incorrect
        classes = self.cb_control.GetItems()
        self.experiment['control'] = [ classes[ self.cb_control.GetSelection() ] ]
        self.experiment['test'] = [ classes[ self.cb_test.GetSelection() ] ]
        self.generateGraphView()

    def OnPruningSettings(self,e):
        """ Open the pruning setup dialog to define conditions, ranges, class-comparisons, etc. """
        dlg = dialogDataPruning(self)
        if dlg.ShowModal() == wx.ID_OK:
            
            self.config.WriteInt('/Data/PruningDepth', dlg.pruningDepth.GetValue())
            self.config.Write('/Data/PruningType', METAPATH_PRUNING_TYPE_CODE[ dlg.pruningChoice.GetSelection() ])
            self.config.WriteBool('/Data/PruningRelative', dlg.pruningRelative.GetValue())

            # Update the toolbar dropdown to match
            self.cb_prune.SetValue( dlg.pruningDepth.GetValue() )        
            self.generateGraphView()
            
        dlg.Destroy()

    def OnModifyPruneDepth(self,e):
        """ Change prune depth via spinner """    
        self.config.WriteInt('/Data/PruningDepth', self.cb_prune.GetValue())
        self.generateGraphView()
    
    def OnSaveAs(self,e):
        """ Save a copy of the graph as one of the supported formats"""
        # Note this will regenerate the graph with the current settings, with output type specified appropriately
        self.dirname = ''
        dlg = wx.FileDialog(self, "Save current pathway as image file", self.dirname, "", "*.*", wx.SAVE)
        if dlg.ShowModal() == wx.ID_OK:
            filename = os.path.join( dlg.GetDirectory(), dlg.GetFilename())
            fn, ext = os.path.splitext(filename)
            format = ext.replace('.','')
            # Check format is supported
            if format in ['bmp', 'canon', 'dot', 'xdot', 'cmap', 'eps', 'fig', 'gd', 'gd2', 'gif', 'gtk', 'ico', 'imap', 'cmapx', 'imap_np', 'cmapx_np', 'ismap', 'jpg', 'jpeg', 'jpe', 'pdf', 'plain', 'plain-ext', 'png', 'ps', 'ps2', 'svg', 'svgz', 'tif', 'tiff', 'vml', 'vmlz', 'vrml', 'wbmp', 'webp', 'xlib']:
                self.generateGraph( filename, format)
            else:
                # Unsupported format error
                pass
            
        dlg.Destroy()

    def OnAbout(self,e):
        # A message dialog box with an OK button. wx.OK is a standard ID in wxWidgets.
        dlg = wx.MessageDialog( self, "A visualisation and analysis tool for metabolomics data in the context of metabolic pathways.", "About MetaPath", wx.OK)
        dlg.ShowModal() # Show it
        dlg.Destroy() # finally destroy it when finished.

    def OnExit(self,e):
        self.Close(True)  # Close the frame.

    def OnReloadDB(self,e):
        self.db=db.databaseManager()
        self.generateGraphView()

    def OnRefresh(self,e):
        self.generateGraphView()
        
        
    def get_filename_with_counter(self, filename):
        fn, ext = os.path.splitext(filename)
        return fn + "-%s" + ext

    def generateGraph(self, filename, format='svg'):
        # Build options-like structure for generation of graph
        # (compatibility with command line version, we need to fake it)
        options = Values()

        options._update_loose({
            'file':None,
            #'pathways': self.config.Read('/Pathways/Show'),
            'not_pathways':'',
            'show_all': False, #self.config.ReadBool('/Pathways/ShowAll'),
            'control':'',
            'test':'',
            'search':'',
            'show_enzymes': self.config.ReadBool('/View/ShowEnzymes'),
            'show_secondary': self.config.ReadBool('/View/Show2nd'),
            'prune': self.config.ReadBool('/Data/PruningActive'),
            'prune_depth': self.config.ReadInt('/Data/PruningDepth'),
            'prune_type': '%s%s' % ( self.config.Read('/Data/PruningType'), 'r' if self.config.ReadBool('/Data/PruningRelative') else ''),
            'splines': True,
            'colorcode': self.config.ReadBool('/Pathways/ShowColors'),
            'show_network_analysis': self.config.ReadBool('/View/ShowAnalysis'),
            'focus':False,
            'show_pathway_links': self.config.ReadBool('/Pathways/ShowLinks'),
            # Always except when saving the file
            'output':format,

        })
        
        pathway_ids = self.config.Read('/Pathways/Show').split(',')

        if self.data:
            if self.experiment['timecourse']:
                self.data.analyse_timecourse(self.experiment['control'], self.experiment['test'], self.experiment['timecourse'])
            else:
                self.data.analyse(self.experiment['control'], self.experiment['test'])           


        pathways = [self.db.pathways[pid] for pid in pathway_ids if pid in self.db.pathways.keys()]        
            
        if self.data and options.prune:
            suggested_pathways = self.data.suggest( self.db, prune_type=options.prune_type, prune_depth=options.prune_depth)
            pathways += suggested_pathways
            
        if self.data:
            if self.data.analysis_timecourse:
                # Generate the multiple views
                tps = sorted( self.data.analysis_timecourse.keys(), key=int )
                # Insert counter variable into the filename
                filename = self.get_filename_with_counter(filename) 
                for tp in tps:
                    graph = core.generator( pathways, options, self.db, analysis=self.data.analysis_timecourse[ tp ], layout=self.layout) 
                    graph.write(filename % tp, format=options.output, prog='neato')
                    print '%s.dot' % filename % tp
                    graph.write('%s.dot' % filename % tp, format='dot', prog='neato')
                return tps
            else:
                graph = core.generator( pathways, options, self.db, analysis=self.data.analysis, layout=self.layout) 
                graph.write(filename, format=options.output, prog='neato')
                return None
        else:
            graph = core.generator( pathways, options, self.db, layout=self.layout) 
            graph.write(filename, format=options.output, prog='neato')
            return None
        
    def generateGraphView(self):

        # By default use the generated metapath file to view
        filename = os.path.join( self.standardPaths.GetTempDir(),'metapath-generated-pathway.svg')
        tps = self.generateGraph(filename=filename, format='svg')

        if tps == None:
            svg_source = [ open(filename).read().decode('utf8') ]
            tps = [0]
        else:
            filename = self.get_filename_with_counter(filename) 
            svg_source = [ 
                open( os.path.join( self.standardPaths.GetTempDir(),filename % tp) ).read().decode('utf8')
                for tp in tps
                ]

        scale = ''
        if self.data:
            scalet, scaleb = u'', u''
            for n,s in enumerate(self.data.scale):
                scalet = scalet + '<td><div class="datasq rdbu9-%d"></div></td>' % (n+1)
                scaleb = scaleb + '<td>%d</td>' % (s)
            scale = '<table><tr><td></td>' + scalet + '</tr><tr><td class="scale-type">%s</td>' % self.data.scale_type + scaleb + '</tr></table>'
        else:
            n = 1

        html_source = '''<html>
        <script>
            current_svg = 1;
            previous_svg = 2;
        
            function init(){
                increment_view();
                window.setInterval('increment_view();',2000);
            }
        
            function increment_view(){
                if (current_svg > %d ){ current_svg = 1; return; }
                            
                document.getElementById('svg' + current_svg).classList.add('visible');
                document.getElementById('svg' + current_svg).classList.remove('hidden');
                
                document.getElementById('svg' + previous_svg).classList.add('hidden');
                document.getElementById('svg' + previous_svg).classList.remove('visible');
                
                previous_svg = current_svg
                current_svg += 1;
            }
        </script>
        <link rel="stylesheet" href="file://%s/css/base.css">''' % (n, str( os.path.join( utils.scriptdir,'html') ) ) + '''
        <body onload="init();">
            <div class="scalebar scalebar-inset">''' + scale + '''</div>'''
        
        for n, svg in enumerate( svg_source ):   
            html_source += '''<div id="svg%d" class="svg"><div class="svgno"><span data-icon="&#xe000;" aria-hidden="true"></span> %s''' % (n+1, tps[n])  + '''</div>''' + svg + '''</div>'''

        html_source += '''</body></html>'''
        
        self.browser.SetPage(html_source,"~") 
        
    def generateSidebarView(self, template='base.html', data={'title':'', 'object':{}, 'data':{} }):
        
        metadata = {
            'htmlbase': os.path.join( utils.scriptdir,'html'),
            # Current state data
            'current_pathways': self.config.Read('/Pathways/Show').split(','),
            'data': self.data,
            # Color schemes
            # 'rdbu9':['b2182b', 'd6604d', 'f4a582', '33a02c', 'fddbc7', 'f7f7f7', 'd1e5f0', '92c5de', '4393c3', '2166ac']
        }
            
        template = self.templateEngine.get_template(template)
        self.sidebar.SetPage(template.render( dict( data.items() + metadata.items() ) ),"~") 
        
        
app = wx.App(False, "MetaPath")  # Create a new app, don't redirect stdout/stderr to a window.

frame = MainWindow(None, "MetaPath: Metabolic pathway visualisation and analysis") # A Frame is a top-level window.
frame.Maximize(True)
frame.Show(True)     # Show the frame.

app.MainLoop()

