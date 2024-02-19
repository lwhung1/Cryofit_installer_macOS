from __future__ import division
from __future__ import print_function

import os
import wx
import wxGUI2

from iotbx import data_plots
from libtbx.utils import Sorry
from wxGUI2 import Base, Buttons, PhilLayout, FileDisplay, Templates
from wxtbx.plots import iotbx_data_plot_base
from mmtbx.command_line import map_comparison

# =============================================================================
class CryoFitGUI(Templates.MultiTabFrameWithOutputDir):
  app_id = 'CryoFit'
  phenix_app_name = 'cryo_fit.run'
  frame_size = (850, 650)

  # def setup_app_local(self):
  #   self.setup_file_handlers()

# -----------------------------------------------------------------------------
class ConfigPanel(Templates.AppConfigPanel):
  text_width = 800

  def DisplayWidgets (self):
    self.phil_handler.add_window(self)

    self.start_section()
    self.draw_phil_controls('cryo_fit.job_title')
    self.end_section()

    self.start_section('Input')
    self.draw_phil_controls('cryo_fit.Input')
    self.end_section()

    ''' #not used now, but keep this so that later on partial continuation of steps
    #can go on
    self.start_section('Steps')
    self.start_grid(cols=2)
    #self.draw_phil_controls('cryo_fit.emweight_multiply_by')
    self.draw_phil_controls('cryo_fit.Steps')
    # self.draw_multiple_phil_controls(
    #   [ 'cryo_fit' ],
    #  auto_align=True)
    self.end_grid()
    self.end_section()
    '''

    self.start_section('Options')
    self.start_grid(cols=2)
    self.draw_phil_controls('cryo_fit.Options')
    self.end_grid()
    #self.create_settings_menu_button()
    #self.create_scope_dialog_button('', 'All parameters...',
    #  handler_function=self.main_window.OnSettingsMenu)
    self.start_grid(cols=1)
    self.start_box()
    self.create_scope_dialog_button("cryo_fit",
      "Additional properties",
      handler_function=self.OnEditParams0)
    self.end_box()
    self.end_grid()
    self.end_section()

    ''' Doonam commented out this (4/3/2019)
    self.start_section('Output')
    self.start_grid(cols=2)
    self.draw_phil_controls('cryo_fit.Output')
    self.end_grid()
    self.end_section()
    '''
  def OnEditParams0 (self, event) :
    self._open_dialog(title=None, phil_scope_name=None,
      custom_dlg_class=Dialog_cryo_fit0)
#  def OnEditParams (self, event) :
#    self._open_dialog(title=None, phil_scope_name=None,
#      custom_dlg_class=Dialog_ligand_identification)
    
class Dialog_cryo_fit0 (PhilLayout.PhilDialogTemplate) :
  title = "Additional Settings"
  def DisplayWidgets (self) :
    #self.phil_handler.add_window(self)
    self.start_section("Step control")
    self.start_box()
    self.set_text("""Optional inputs to customize cryo_fit steps for the run if resarting a previous run.""", width=800)
    self.end_box()
    self.start_grid(cols=2)
    self.draw_phil_controls('cryo_fit.Steps', auto_align=False)
    self.end_grid()
    self.end_section()

    self.start_section("Addition parameters")
    self.set_text("""Additional cryo_fit parameters. Default values are usually sufficient.""", width=800)
    self.start_grid(cols=3)
    cf=["cryo_fit.force_field","cryo_fit.ns_type","cryo_fit.nproc",
        "cryo_fit.perturb_xyz_by","cryo_fit.lincs_order","cryo_fit.max_emweight_multiply_by",
        "cryo_fit.many_step_____n__dot_pdb","cryo_fit.devel",
        "cryo_fit.initial_cc_wo_min","cryo_fit.initial_cc_w_min",
        "cryo_fit.kill_mdrun_mpirun_in_linux","cryo_fit.missing",
        "cryo_fit.ignh","cryo_fit.remove_metals"] 
    self.draw_multiple_phil_controls(cf,auto_align=False)
    self.end_grid()
    self.end_section()
'''
class Dialog_ligand_identification (PhilLayout.PhilDialogTemplate) :
  title = "Ligand search settings"
  def DisplayWidgets (self) :
    self.start_grid(cols=2)
    self.draw_multiple_phil_controls([
       "ligand_identification.low_resolution",
       "ligand_identification.n_indiv_tries_min",
       "ligand_identification.n_indiv_tries_max",
       "ligand_identification.n_group_search",
       "ligand_identification.search_dist",
       "ligand_identification.delta_phi_lig",
       "ligand_identification.fit_phi_inc",
       "ligand_identification.local_search",
       "ligand_identification.nproc",
       "ligand_identification.verbose",
       "ligand_identification.debug",
      ], auto_align=True)
    self.end_grid()
'''
  
# -----------------------------------------------------------------------------
class RunNotebook(Templates.ProcessNotebookSimple):

  def view_results_in_coot (self, pdb_file) :
    self.launch_coot()
    self.coot_server.update_model(pdb_file)

# -----------------------------------------------------------------------------
class ResultPanel(Templates.ResultPanelBase):

  def add_graph(self, mc_data, title, labels, formats, columns):
    """
    Helper function for generating graphs specific to this program
    """
    table = data_plots.table_data(
      title=title,
      column_labels=labels,
      column_formats=formats,
      graph_names=[title],
      graph_labels=[labels],
      graph_columns=[columns])
    for i in range(len(mc_data)):
      row = [None for j in range(len(columns))]
      for j in range(len(columns)):
        row[j] = mc_data[i][j]
      table.add_row(row)
    graph = iotbx_data_plot_base(parent=self,tables=[table],
                                 title_alignment='center')
    graph.set_plot(title)
    self.add_expanding_widget(graph)

  def DisplayWidgets(self):

    self.start_section('Cryo Fit')

    self.start_box()
    self.add_log_and_config()
    self.set_bold_text('Directory:')
    self.set_mono_text(self.get_output_dir())
    if (wxGUI2.DESKTOP_TYPE in ['mac', 'kde', 'gnome']):
      view_btn = FileDisplay.DirViewButton(
        parent=self,dir_name=self.get_output_dir())
      self.add_centered_widget(view_btn)
    self.end_box()

    self.file_list = Base.ListCtrl(
      parent=self, size=(-1, 300), style=wx.LC_SINGLE_SEL)
    self.file_list.SetColumns(['Filename', 'Directory'])
    self.file_list.SetColumnWidths([300,400])
    self.Bind(wx.EVT_LIST_ITEM_SELECTED, self.OnSelect, self.file_list)
    self.Bind(wx.EVT_LIST_ITEM_DESELECTED, self.OnDeSelect, self.file_list)
    self.current_sizer.Add(self.file_list, 1, wx.ALL|wx.EXPAND, 5)

    self.start_box()
    self.coot_btn = Buttons.CootButtonSmall(
      parent=self, handler_function=self.OnViewStructure)
    self.coot_btn.Enable(False)
    self.current_sizer.Add(self.coot_btn, 0, wx.ALL|wx.RIGHT, 5)
    self.end_box()

    self.end_section()

    self.main_sizer.Fit(self)
    self.main_sizer.Layout()
    self.SetAutoLayout(True)

    # populate file list
    result_directory = os.path.join(self.get_output_dir(), 'output')
    for filename in os.listdir(result_directory):
      if (filename.endswith('.pdb')):
        self.file_list.AddRow([os.path.basename(filename),
                               result_directory])

    self.start_section('Correlation Coefficients')

    cc_record = ''
    try:
      cc_record = self._result['cc_record'] # for Yong Chen, "TypeError: string indices must be integers, not str"
    except:
      print("cc_record is not retrieved, possibly TypeError: string indices must be integers, not str")
      print("please contact doonam@lanl.gov for this error")
      exit(1)

    title = 'Steps vs CC'
    labels = ['Steps', 'CC']
    formats = ['%1.2f', '%1.4f']
    columns = [0, 1]
    self.add_graph(cc_record, title, labels, formats, columns)
    self.end_section()

  def OnSelect(self, event=None):
    # for btn in self.graphics_btns:
    #   btn.Enable(True)
    self.coot_btn.Enable(True)

  def OnDeSelect(self, event=None):
    # for btn in self.graphics_btns:
    #   btn.Enable(False)
    self.coot_btn.Enable(False)

  def OnViewStructure(self, event=None):
    # btn = event.GetEventObject()
    # program = btn.user_data.lower()
    i = self.file_list.GetFirstSelected()
    pdb_file = os.path.join(self.file_list.GetItemText(i,col=1),
                            self.file_list.GetItemText(i,col=0))
    self.parent.view_results_in_coot(pdb_file)

    # try:
    #   method = getattr(self.parent, 'view_results_in_%s' % program)
    #   method(pdb_file, map_file)
    # except Exception:
    #   raise Sorry('Could not open structure in viewer.')

# =============================================================================
# end
