from __future__ import absolute_import
from __future__ import division
from __future__ import print_function

from elbow.utilities.phil_utils import master_phil
import glob, iotbx.pdb.hierarchy, os, platform, subprocess, sys, time, shutil 
from iotbx import file_reader
from libtbx import phil
import libtbx.phil.command_line
from libtbx.utils import Sorry
from libtbx.utils import multi_out
import mmtbx.utils
from subprocess import check_output, Popen, PIPE
from common_functions import *

def run(args, log=sys.stdout):
  #args=sys.argv[1:]
  command_path = args[0]

  common_functions_path = os.path.join(command_path,'common_functions')
  sys.path.insert(0, common_functions_path)
  #from common_functions import *

  number_of_available_cores = int(args[1])
  nproc = args[2] # for mpi -> cores, for threads -> threads
  target_map_with_pathways = args[3]
  starting_dir = args[4]
  this_is_test = args[5]
  restart_w_longer_steps = args[6]
  cryo_fit_path = args[7]

#if (__name__ == "__main__") :
  cur_dir=os.getcwd()
  cp_command_string = ''
  updir=os.path.dirname(cur_dir)
  up2dir=os.path.dirname(os.path.dirname(cur_dir))
  if (str(this_is_test) == "False"):
    cp_command_string = os.path.join(updir,'7_make_tpr_with_disre2','for_cryo_fit.tpr')
    cplist=[cp_command_string]
    #"cp ../7_make_tpr_with_disre2/for_cryo_fit.tpr . "
  else:
    cp_command_string =os.path.join(up2dir,'data','input_for_step_8','*')
    cplist=glob.glob(cp_command_string)
    #"cp ../../data/input_for_step_8/* ."
  #libtbx.easy_run.fully_buffered(command=cp_command_string).raise_if_errors()
  for i in cplist:
    shutil.copy2(i,cur_dir)
  
  write_this_input_command = first_prepare_cryo_fit(number_of_available_cores, \
                                                         nproc, \
                                                         target_map_with_pathways, restart_w_longer_steps, cryo_fit_path)
  
  f_out = open('log.step_8_cryo_fit_used_command', 'wt')
  f_out.write(write_this_input_command)
  f_out.close()

#end of if (__name__ == "__main__")
########## end of run()########
if (__name__ == "__main__") :
  run(sys.argv[1:])  
        
