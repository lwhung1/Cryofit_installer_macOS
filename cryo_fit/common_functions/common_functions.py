from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
from cctbx import maptbx
import glob, os, platform, subprocess
import iotbx.pdb
import iotbx.pdb.mmcif
from libtbx import phil
import libtbx.phil.command_line
from libtbx.utils import Sorry
from libtbx.utils import multi_out
import mmtbx.model
import mmtbx.utils
import numpy as np
from os.path import expanduser # to find home_dir
import shutil # for rmdir
from subprocess import check_output, Popen, PIPE

termcolor_installed = '' # just initial value
try:
    from termcolor import colored
    termcolor_installed = True
    #print "User's computer has termcolor, installed"
except Exception:
    termcolor_installed = False
    ''' # disable this for now, so that phenix launch will not show this message
    print "\n\tUser's computer has no termcolor"
    print "\tIf a user want to see cryo_fit installation helper's comments in color..."
    print "\t1. Download termcolor-1.1.0.tar.gz from https://pypi.python.org/pypi/termcolor"
    print "\t2. Extract termcolor-1.1.0.tar.gz (for example, tar -xvf termcolor-1.1.0.tar.gz)"
    print "\t3. Run \"python setup.py install\" at the extracted folder"
    print "Press any key to continue"
    ''' #raw_input() # disable this for now, so that Phenix GUI will work


def assign_map_name(params, starting_dir, inputs, map_file_name): # I need to assign map file first, then model file (04/23/2018)
  print("\n\tAssign map file name")
  
  params.cryo_fit.Input.map_file_name = map_file_name
  if os.path.isfile(params.cryo_fit.Input.map_file_name) != True:
    print("Please correct map file location, cryo_fit can't find " + params.cryo_fit.Input.map_file_name)
    exit(1)
  
  temp_map_file_name = params.cryo_fit.Input.map_file_name
  print("\t\tparams.cryo_fit.Input.map_file_name a user provided: ", temp_map_file_name)
  
  if (temp_map_file_name[len(temp_map_file_name)-5:len(temp_map_file_name)] == ".ccp4" or \
      temp_map_file_name[len(temp_map_file_name)-4:len(temp_map_file_name)] == ".map" or \
      temp_map_file_name[len(temp_map_file_name)-4:len(temp_map_file_name)] == ".mrc" ):
    
    params.cryo_fit.Input.map_file_name = mrc_to_sit(inputs, params.cryo_fit.Input.map_file_name, params.cryo_fit.Input.model_file_name) # shift origin of map if needed
  
  print("\t\tparams.cryo_fit.Input.map_file_name after a possible mrc_to_sit: ", params.cryo_fit.Input.map_file_name)
  map_file_with_pathways = os.path.abspath(params.cryo_fit.Input.map_file_name)
  print("\t\tmap_file_with_pathways:",map_file_with_pathways)
  
  if ((map_file_with_pathways[len(map_file_with_pathways)-4:len(map_file_with_pathways)] == ".map") or
      (map_file_with_pathways[len(map_file_with_pathways)-4:len(map_file_with_pathways)] == ".mrc")):
    map_file_with_pathways = map_file_with_pathways[:-4] + "_converted_to_sit.sit"
  elif (map_file_with_pathways[len(map_file_with_pathways)-5:len(map_file_with_pathways)] == ".ccp4"):
    map_file_with_pathways = map_file_with_pathways[:-5] + "_converted_to_sit.sit"
  
  ### assign map_file_without_pathways
  map_file_without_pathways = os.path.basename(map_file_with_pathways)
  
  if os.path.isfile(map_file_with_pathways) != True:
    print("\tcryo_fit can't find ", map_file_with_pathways)
    exit(1)
  
  os.chdir(starting_dir)
  return map_file_with_pathways, map_file_without_pathways
############## end of assign_map_name()


def assign_model_name(params, starting_dir, inputs, model_file_name):
  print("\n\tAssign a model file name.")
  params.cryo_fit.Input.model_file_name = model_file_name
  if os.path.isfile(params.cryo_fit.Input.model_file_name) != True:
    print("Please correct the model file location, cryo_fit can't find " + params.cryo_fit.Input.model_file_name)
    exit(1)
  
  ### Assign model_file_without_pathways (not final)
  model_file_without_pathways = os.path.basename(params.cryo_fit.Input.model_file_name)

  model_file_with_pathways = ''

  
  # (begin) this renaming is necessary to process a file name with a space  
  splited_model_file_without_pathways_by_space = model_file_without_pathways.split(" ")
  if (len(splited_model_file_without_pathways_by_space) != 1):
    model_file_with_pathways_replaced = params.cryo_fit.Input.model_file_name.replace(" ", "_")

    shutil.copy(params.cryo_fit.Input.model_file_name, model_file_with_pathways_replaced)
    model_file_with_pathways = model_file_with_pathways_replaced
    model_file_with_pathways = os.path.abspath(model_file_with_pathways)
  else:
    model_file_with_pathways = os.path.abspath(params.cryo_fit.Input.model_file_name)
  # (end) this renaming is necessary to process a file name with a space
  
  
  if params.cryo_fit.Input.model_file_name.endswith('.cif'): # works well, 4/23/2018
    print("\t\tSince a user provided .cif file, let's turn it into .pdb")
    cif_as_pdb(params.cryo_fit.Input.model_file_name)
    cw_dir = os.getcwd()
    params.cryo_fit.Input.model_file_name = cw_dir + "/" + model_file_without_pathways
    params.cryo_fit.Input.model_file_name = params.cryo_fit.Input.model_file_name[:-4] + ".pdb"
  elif params.cryo_fit.Input.model_file_name.endswith('.ent'):
    print("\t\tSince a user provided .ent file, let's simply change its extension into .pdb")
    params.cryo_fit.Input.model_file_name = ent_as_pdb(params.cryo_fit.Input.model_file_name)
  
  model_file_without_pathways = os.path.basename(model_file_with_pathways)
  
  os.chdir(starting_dir)
  return model_file_with_pathways, model_file_without_pathways
####################### end of assign_model_name()


def check_first_cc(cc_record):
    f_in = open(cc_record, 'r')
    cc = ''
    for line in f_in:
      splited = line.split()
      cc = splited[4]
      break
    f_in.close()
    return cc
########### end of check_first_cc


def check_whether_cc_has_been_increased(logfile, cc_record, this_is_test):
  print("\tCryo_fit will check whether cc has been increased.\n")
  
  ################## (begin) Judge whether this is the very first run of step_8
  f_in = open(cc_record)
  step_number = ''
  for line in f_in:
    splited = line.split(" ")
    step_number = splited[1]
  f_in.close()
  
  if (int(step_number) == 10000):
    write_this = "\tProbably this is the very first run of step_8.\n\tVery first run of step_8 may have cc fluctuating first few steps.\n\tTherefore, cryo_fit will run longer.\n"
    print(write_this)
    logfile.write(str(write_this))
    return "increased"
  ############### (end) Judge whether this is the very first run of step_8
  
  #min_cc_numbers_for_judging = 20
  cc_array = []
  
  f_in = open(cc_record)
  for line in f_in:
    splited = line.split(" ")
    cc = splited[4]
    if (float(cc) < 0.0001):
      print("\tcc: " + cc + " < 0.0001")
      print("\tExit now, since further cc will be 0.000 as well\n")
      exit(1)
    cc_array.append(float(cc))
  f_in.close()
  
  i = 0
  cc_1st_array = []
  cc_2nd_array = []
  f_in = open(cc_record)
  for line in f_in:
    i = i + 1
    splited = line.split(" ")
    cc = float(splited[4])
    
    if (i < (len(cc_array)/2)):
        cc_1st_array.append(cc)
    else:
        cc_2nd_array.append(cc)
  f_in.close()

  ####### commented out below since it is too often (len(cc_array) < min_cc_numbers_for_judging)
  '''
  print "\tthis_is_test:", this_is_test
  if (this_is_test == True):
    min_cc_numbers_for_judging = 3
  if (len(cc_array) < min_cc_numbers_for_judging):
    print "\t\tnumber of cc evaluations (", len(cc_array), ") < min_cc_numbers_for_judging (", min_cc_numbers_for_judging, ")"
    print "\t\tCryo_fit will re-run because usually first few evaluations of cc tend to fluctuate."
    print "\t\tTherefore, cryo_fit just hypothetically considers as if the most recent CCs have been increased for now."
    
    return "increased" # the cc values tend to be increased, so re-run with longer steps
  '''
  
  ''' Old method -> use the last 50 cc values only
  
  f_in = open(cc_record)
  former_cc = -99
  step_number_for_judging = 50
  cc_has_been_increased_array = []
  cc_array = []
  
  for line in f_in:
    splited = line.split(" ")
    cc = splited[4]
    if (float(cc) < 0.0001):
      print "\t\tcc: " + cc + " < 0.0001"
      print "\t\tExit now, since further cc will be 0.000 as well\n"
      exit(1)
    cc_array.append(cc)
    if cc > former_cc:
      cc_has_been_increased_array.append(True)
    else:
      cc_has_been_increased_array.append(False)
    former_cc = cc
  f_in.close()
  
  print "this_is_test:", this_is_test
  if (this_is_test == True):
    step_number_for_judging = 5
  if (len(cc_has_been_increased_array) < step_number_for_judging):
    print "\t\tnumber of cc evaluations (", len(cc_has_been_increased_array), ") < step_number_for_judging (", step_number_for_judging, ")"
    print "\t\tCryo_fit will re-run because usually first few evaluations of cc tend to fluctuate."
    print "\t\tTherefore, cryo_fit just hypothetically considers as if the most recent CCs have been increased for now."
    
    return True 
  
  
  the_highest_cc = -99
  cc_last = cc_array[len(cc_array)-1]
  print "\t\tlast cc:", cc_last
  
  # Only use the last step_number_for_judging cc values
  for i in xrange(len(cc_array)-1, len(cc_array)-(step_number_for_judging+1), -1):
    cc = cc_array[i]
    print "\t\t",i,"th cc:",cc
    if cc > the_highest_cc:
      the_highest_cc = cc
  print "\t\tthe_highest_cc:",the_highest_cc,"cc_last:",cc_last
  
  if the_highest_cc == cc_last:
    print "\t\tDefinitely re-run with longer cryo_fit steps since the_highest_cc = cc_last"
    return True
    
  cc_has_been_increased = 0
  cc_has_been_decreased = 0
  
  for i in xrange(len(cc_has_been_increased_array)-1, len(cc_has_been_increased_array)-(step_number_for_judging+1), -1):
    if cc_has_been_increased_array[i] == False:
      cc_has_been_decreased = cc_has_been_decreased + 1
    else:
      cc_has_been_increased = cc_has_been_increased + 1
  print "\t\tNumber of cc increase in the last ",step_number_for_judging," steps: ",cc_has_been_increased
  print "\t\tNumber of cc decrease in the last ",step_number_for_judging," steps: ",cc_has_been_decreased

  if (cc_has_been_decreased > cc_has_been_increased):
    msg=(
    '\n\tcc tends to decrease over the last ' + str(step_number_for_judging) + ' steps.'
    '\n\tRead https://github.com/cryoFIT/cryo_fit/blob/master/Cryo_fit1_FAQ.pdf'
    '\n\tHere, cryo_fit will try stronger map weight automatically.'
    )
    print (msg)
    logfile.write(msg)
    return "re_run_with_higher_map_weight"

  #multiply_by_this = 1.5 # cryo_fit will run quickly, this is for devel
  #multiply_by_this = 1.2 # with this value, L1 stalk may have lost a valuable opportunity
  multiply_by_this = 1.1 # cryo_fit will run slowly, but it may find a better fit

  if (this_is_test == True):
    #multiply_by_this = 2.2 # to finish quickly. However because of this trick, below codes may not be tested
    multiply_by_this = 2 # to finish quickly. However because of this trick, below codes may not be tested
    
  if (cc_has_been_increased > cc_has_been_decreased*multiply_by_this): # cc_has_been_increased > cc_has_been_decreased+3 confirmed to be too harsh
    cc_50th_last = cc_array[len(cc_array)-(step_number_for_judging+1)]
    cc_25th_last = cc_array[len(cc_array)-(step_number_for_judging+26)]
    
    if ((cc_last > cc_50th_last) and (cc_last > cc_25th_last)):
        write_this = "\tcc_last (" + cc_last + ") > cc_50th_last (" + cc_50th_last + ")"
        print write_this
        logfile.write(write_this)
        
        write_this = "\tcc_last (" + cc_last + ") > cc_25th_last (" + cc_25th_last + ")"
        print write_this
        logfile.write(write_this)
        
        return True # the last 30~50 cc values tend to be increased, so re-run with longer steps
    else:
        write_this = "\tcc_last (" + cc_last + ") <= cc_50th_last (" + cc_50th_last + ")"
        print write_this
        logfile.write(write_this)
        
        write_this = "\tOr cc_last (" + cc_last + ") <= cc_25th_last (" + cc_25th_last + ")"
        print write_this
        logfile.write(write_this)
        
        return False
  else:
    return False # either this is a regression or the last 30 cc values tend NOT to be increased
  '''
  
  # New and better method -> use all cc values in cc_record file
  the_highest_cc = -99
  cc_last = cc_array[len(cc_array)-1]
  
  for i in range(0, (len(cc_array)-1), 1):
    cc = cc_array[i]
    #print "\t\t",i,"th cc:",cc
    if cc > the_highest_cc:
      the_highest_cc = cc
  print("\tthe_highest_cc:",the_highest_cc, "cc_last:",cc_last)
  
  if the_highest_cc == cc_last:
    print("\tDefinitely re-run with longer cryo_fit steps since the_highest_cc = cc_last")
    return "increased" # the cc values tend to be increased, so re-run with longer steps

  if (this_is_test == True):
    #if (np.mean(cc_2nd_array) > np.mean(cc_1st_array)*1.05): # didn't re-run
    if (np.mean(cc_2nd_array) > np.mean(cc_1st_array)*1.03):  # re-ran 1~3 times all the times within 1 minute
        write_this = "\tmean of cc_2nd_array (" + str(np.mean(cc_2nd_array)) + ") > mean of cc_1st_array (" + str(np.mean(cc_1st_array)) + ")\n"
        print(('%s' %(write_this)))
        logfile.write(str(write_this))
        return "increased" # the cc values tend to be increased, so re-run with longer steps
  else:
    if (np.mean(cc_2nd_array) > np.mean(cc_1st_array)):
        write_this = "\tmean of cc_2nd_array (" + str(np.mean(cc_2nd_array)) + ") > mean of cc_1st_array (" + str(np.mean(cc_1st_array)) + ")\n"
        print(('%s' %(write_this)))
        logfile.write(str(write_this))
        return "increased" # the cc values tend to be increased, so re-run with longer steps
    elif (np.mean(cc_1st_array) > np.mean(cc_2nd_array)*1.03):
        return "re_run_with_higher_map_weight"
    # Current overall scheme of cryo_fit can't reliably fit with certainty since geometry estimation lacks (while RSR has one).
    # However, current scheme of cryo_fit safely/naively assumes that user provided atomic model has decent initial fit and reasonable geometry according to Doonam's experiences with user requests.

  ### Common for both regression/test and regular run
  write_this = "\tmean of cc_2nd_array (" + str(np.mean(cc_2nd_array)) + ") <= mean of cc_1st_array (" + str(np.mean(cc_1st_array)) + ")\n"
  print(('%s' %(write_this)))
  logfile.write(str(write_this))
    
  write_this = "\tcc values are saturated\n"
  print(('%s' %(write_this)))
  logfile.write(str(write_this))

  return "cc_saturated" # either this is a regression or the last cc values tend NOT to be increased
############################ end of check_whether_cc_has_been_increased function


def check_whether_install_is_done(check_this_file_w_path):
    print("Check whether ", check_this_file_w_path, " exists.")
    returned_file_size = ''
    succesful_installation = True
    if (os.path.isfile(check_this_file_w_path)):
      returned_file_size = file_size(check_this_file_w_path)
      if (returned_file_size > 0):
        print("Successful installation because cryo_fit can find ", check_this_file_w_path)
      else:
        print("Not successful installation, cryo_fit found ", check_this_file_w_path, " but it is empty")
        succesful_installation = False
    else:
        print("Not successful installation because cryo_fit can't find ", check_this_file_w_path)
    
    if (succesful_installation == False):
        print("For troubleshooting, step-by-step installation is recommended.")
        print("Usage: python install_cryo_fit.py <gromacs_cryo_fit.zip> <install_path> <install_at_one_queue>")
        print("Example usage: python ~/bin/phenix-1.13rc1-2961/modules/cryo_fit/steps/0_install_cryo_fit/install_cryo_fit.py ~/Downloads/gromacs_cryo_fit.zip ~/cryo_fit False")
        color_print ("exit now", 'red')
        exit(1)
######################### end of check_whether_install_is_done()


def check_whether_mdrun_is_accessible(long_message):
    try:
        path = subprocess.check_output(["which", "mdrun"])
        tp=type(path)
        if tp is str:
            path=path
        elif tp is bytes:
            path=path.decode()
        splited = path.split("/")
        if ((len(splited)) != 0):
            print("\tmdrun is accessible")
            mdrun_path = ''
            for i in range(len(splited)-1):
                mdrun_path = mdrun_path + splited[i] + "/"
            print("\tUser's mdrun executable comes from ", mdrun_path)
            return mdrun_path
        else:
            print(long_message)
            return False
    except:
        print(long_message)
        return False
######################## end of check_whether_mdrun_is_accessible()


def check_whether_the_step_was_successfully_ran(step_name, check_this_file, logfile):
    if (os.path.isfile(check_this_file)):
        returned_file_size = file_size(check_this_file)
        if (returned_file_size > 0):
            if (step_name == "Step 8"):
                
                with open("md.log") as md_log_file:
                    if "Too many LINCS warnings" in md_log_file.read():
                        md_log_file.close()
                        write_this = "\nToo many LINCS warnings. Run phenix.real_space_refine first to stabilize starting molecule\n"
                        print(write_this)
                        logfile.write(write_this)
                        return "failed"
                    
                with open(check_this_file) as cc_record_file:
                    if "nan" in cc_record_file.read():
                        cc_record_file.close()
                        return "failed_with_nan_in_cc"
                    else:
                        user_s_cc = get_users_cc(check_this_file)
                        if (float(user_s_cc) < 0.0001):
                            write_this = "\nUser's provided input pdb file has less than 0.0001 cc\n"
                            print(write_this)
                            logfile.write(write_this)
                            write_this = "\nPlease read https://www.phenix-online.org/documentation/faqs/cryo_fit_FAQ.html#i-see-user-s-provided-atomic-model-had-0-0-cc-in-my-cryo-fit-overall-log\n"
                            print(write_this)
                            logfile.write(write_this)
                            return "failed"
                        cc_record_file.close()
            if (step_name != "Step 8"):
                print(step_name, " successfully ran")
            else: # step 8 again
                print(step_name, " may have successfully ran") # "state.cpt not found, step_8 may be full of stepxb_nx.pdb."
            return "success"
        else:
            return "0_size"
    print(step_name, " didn't successfully run")
    if (step_name == "Step 4" or step_name == "Step 7" or step_name == "Step 8"):
      return "failed"
######################## end of check_whether_the_step_was_successfully_ran function


def check_whether_the_step_3_was_successfully_ran(logfile, check_this_file):
    if (os.path.isfile(check_this_file)):
        returned_file_size = file_size(check_this_file)
        if (returned_file_size > 0):
          return "success"
    msg=(
    'Step 3 didn\'t successfully run\n'
    '\n\tIf a user sees a message like\n\n'
    '\t\t"Program grompp, VERSION 4.5.5 \n'
    '\t\tSource code file: toppush.c, line: 1166\n\n'
    
    '\t\tFatal error:\n'
    '\t\tAtomtype CH3 not found\n'
    '\t\tFor more information and tips for troubleshooting, please check the GROMACS\n'
    '\t\twebsite at http://www.gromacs.org/Documentation/Errors"\n\n'
    
    '\n\t\tor ERROR 9 [file emd_6057_pdb3j7z_cleaned_for_gromacs_by_pdb2gmx.top, line 1001060]:\n'
    '\t\tNo default Proper Dih. types"\n\n'
    
    '\tIt means that user\'s input pdb file has a forcefield undefined ligand\n'
    '\tTherefore, cryo_fit recommends either of two methods\n\n'
    
    '\t\t1st method> Remove lines of the unusual ligand that brought that message from input pdb file.\n'
    '\t\tThen, run again phenix.cryo_fit. \n'
    '\t\tLigand fitting into cryo-EM map can be done later by phenix.ligandfit anyway.\n'
    '\t\tOf course, if the ligand is really unusual, cif file from phenix.elbow is required for that phenix.ligandfit\n\n'
    
    '\t\t2nd method> Add atomtypes of your ligand to amber03.ff of this cryo_fit distribution using http://davapc1.bioch.dundee.ac.uk/cgi-bin/prodrg and .../modules/cryo_fit/steps/0_prepare_cryo_fit/top2rtp/runme_top2rtp.py\n'
    '\t\tThen, email me (doonam.kim@pnnl.gov), I want to recognize your contribution publicly and distribute updated force field\n'
    )
    print (msg)
    logfile.write(msg)
    exit(1)
######################## end of check_whether_the_step_was_successfully_ran function


def cif_as_pdb(file_name):  
    try:
      assert os.path.exists(file_name)
      print("\tConverting %s to PDB format." %file_name)
      cif_input = iotbx.pdb.mmcif.cif_input(file_name=file_name)
      hierarchy = cif_input.construct_hierarchy()
      basename = os.path.splitext(os.path.basename(file_name))[0]
      iotbx.pdb.write_whole_pdb_file(
          file_name=basename+".pdb",
          output_file=None,
          processed_pdb_file=None,
          pdb_hierarchy=hierarchy,
          crystal_symmetry=cif_input.crystal_symmetry(),
          ss_annotation=cif_input.extract_secondary_structure(),
          append_end=True,
          atoms_reset_serial_first_value=None,
          link_records=None)
    except Exception as e:
      print("Error converting %s to PDB format:" %file_name)
      print(" ", str(e))
############### end of cif_as_pdb()


def color_print(text, color):
    if (termcolor_installed == True):
        print(colored (text, color))
    else:
        print(text)
############### end of color_print()


def determine_number_of_steps_for_cryo_fit(model_file_without_pathways, model_file_with_pathways, \
                                          user_entered_number_of_steps_for_cryo_fit, devel):
  if (devel == True):
    number_of_steps_for_cryo_fit = 100
    return number_of_steps_for_cryo_fit
  
  if (user_entered_number_of_steps_for_cryo_fit != None ):
    print("\tcryo_fit will use user_entered_number_of_steps_for_cryo_fit:", user_entered_number_of_steps_for_cryo_fit)
    return user_entered_number_of_steps_for_cryo_fit
  
  '''
  # now number_of_steps_for_cryo_fit is less relevant to molecule size
  number_of_atoms_in_input_pdb = know_number_of_atoms_in_input_pdb(model_file_with_pathways)
  number_of_steps_for_cryo_fit = '' # just initial declaration
  if (number_of_atoms_in_input_pdb < 2500): # pdb5khe.pdb
    number_of_steps_for_cryo_fit = 300 
  elif (number_of_atoms_in_input_pdb < 7000): # tRNA has 6k atoms (pdb and gro)
    number_of_steps_for_cryo_fit = 3000 # 15,000 seems too large
  elif (number_of_atoms_in_input_pdb < 20000): # nucleosome has 14k atoms (pdb), 25k atoms (gro)
    number_of_steps_for_cryo_fit = 4000
  elif (number_of_atoms_in_input_pdb < 50000): # beta-galactosidase has 32k atoms (pdb), 64k atoms (gro)
    number_of_steps_for_cryo_fit = 5000 # for beta-galactosidase, 30k steps was not enough to recover even starting cc
  else: # ribosome has 223k atoms (lowres_SPLICE.pdb)
    number_of_steps_for_cryo_fit = 6000
  print "\tTherefore, a new number_of_steps for cryo_fit is ", number_of_steps_for_cryo_fit
  '''
  
  #number_of_steps_for_cryo_fit = 5000 # this mere 5k is the cause of low (21~29) number of cc evaluations???
  number_of_steps_for_cryo_fit = 10000
  return number_of_steps_for_cryo_fit
############### end of determine_number_of_steps_for_cryo_fit function


def determine_number_of_steps_for_minimization(model_file_without_pathways, \
                                               model_file_with_pathways, \
                                               user_entered_number_of_steps_for_minimization, devel):
  if (devel == True):
    number_of_steps_for_minimization = 10
    return number_of_steps_for_minimization

  if (user_entered_number_of_steps_for_minimization != None ):
    print("\tcryo_fit will use user_entered_number_of_steps_for_minimization:", user_entered_number_of_steps_for_minimization)
    return user_entered_number_of_steps_for_minimization
    
  '''
  number_of_atoms_in_input_pdb = know_number_of_atoms_in_input_pdb(model_file_with_pathways)
  number_of_steps_for_minimization = '' # just initial declaration
  if (number_of_atoms_in_input_pdb < 7000): # tRNA has 6k atoms (pdb and gro)
    number_of_steps_for_minimization = 1000
  elif (number_of_atoms_in_input_pdb < 20000): # nucleosome has 14k atoms (pdb), 25k atoms (gro)
    number_of_steps_for_minimization = 5000 # w_H1/emd_3659_keep_as_Heidelberg used 5k
  elif (number_of_atoms_in_input_pdb < 50000): # beta-galactosidase has 32k atoms (pdb), 64k atoms (gro)
    number_of_steps_for_minimization = 10000
  else: # ribosome has 223k atoms (lowres_SPLICE.pdb)
    number_of_steps_for_minimization = 20000
  '''
  
  number_of_steps_for_minimization = 20000
  print("\tTherefore, a new number_of_steps for minimization is ", number_of_steps_for_minimization)
  return number_of_steps_for_minimization
############### end of determine_number_of_steps_for_minimization function


def decide_nproc(check_at_each_step):
    number_of_total_cores = know_total_number_of_cores()
    color_print ("User's computer has ", 'green')
    print(number_of_total_cores)
    color_print ("number of cores in total", 'green')
    print("\n")
    cores = 0 # temporary value
    if check_at_each_step == 1:
        color_print ("Enter how many cores a user want to use:", 'green')
        cores = input()
    else:
        if number_of_total_cores > 38:
            cores = 35
        else:
            cores = 2
    return cores
############### end of decide_nproc function


def end_regression(starting_dir, write_this):
  print("end regression (both for each step and all steps)")
  os.chdir (starting_dir)
  print(write_this)
  
  if (os.path.isfile("cc_record_full") == True):
    rm_command_string = "rm cryo_fit* cc_record_full"
  else:
    rm_command_string = "rm cryo_fit*"
  libtbx.easy_run.fully_buffered(rm_command_string)
  
  exit (1) # exit the whole program as expected
########## end of end_regression


def ent_as_pdb(file_name):
    new_file_name = file_name[:-4] + ".pdb"
    cp_command_string = "cp " + file_name + " " + new_file_name
    print("cp_command_string:", cp_command_string)
    libtbx.easy_run.fully_buffered(cp_command_string)
    return new_file_name
######## end of ent_as_pdb()


def file_size(fname):
    statinfo = os.stat(fname)
    return statinfo.st_size
######## end of file_size(fname)


def final_prepare_cryo_fit(number_of_available_cores, nproc, \
                           common_command_string, restart_w_longer_steps):
    command_used = '' #just initial value
    if (nproc == "max"):
        if (number_of_available_cores < 4):
            command_used = run_cryo_fit_itself(2, common_command_string, restart_w_longer_steps)
        elif (number_of_available_cores < 8):
            command_used = run_cryo_fit_itself(4, common_command_string, restart_w_longer_steps)
        elif (number_of_available_cores < 12):
            command_used = run_cryo_fit_itself(8, common_command_string, restart_w_longer_steps)
        elif (number_of_available_cores < 16):
            command_used = run_cryo_fit_itself(12, common_command_string, restart_w_longer_steps)
        else: # ribosome benchmark showed that maximum useful number of cores is 16
            command_used = run_cryo_fit_itself(16, common_command_string, restart_w_longer_steps)
    else:
        command_used = run_cryo_fit_itself(int(nproc), common_command_string, restart_w_longer_steps)
    return command_used
######## end of final_prepare_cryo_fit function


def final_prepare_minimization(ns_type, number_of_available_cores, nproc, common_command_string):
    command_used = '' #just initial value
    if (nproc == "max"):
        if (number_of_available_cores < 4):
            command_used = minimize(2, ns_type, common_command_string)
        elif (number_of_available_cores < 8):
            command_used = minimize(4, ns_type, common_command_string)
        elif (number_of_available_cores < 12):
            command_used = minimize(8, ns_type, common_command_string)
        elif (number_of_available_cores < 16):
            command_used = minimize(12, ns_type, common_command_string)
        else: # ribosome benchmark showed that maximum useful number of cores is 16
            command_used = minimize(16, ns_type, common_command_string)
    else:
        command_used = minimize(int(nproc), ns_type, common_command_string)
    return command_used
#################### end of final_prepare_minimization function


def first_prepare_cryo_fit(number_of_available_cores, nproc, target_map, restart_w_longer_steps, cryo_fit_path):
    
    common_command_string = cryo_fit_path + "mdrun -v -s for_cryo_fit.tpr -mmff -emf " + \
                            target_map + " -nosum  -noddcheck "
    
                            # -c       : confout.gro  Output       Structure file: gro g96 pdb etc
                            # mmff     : Merck Molecular ForceField
                            # noddcheck: When inter charge-group bonded interactions are beyond the bonded cut-off distance, \
                            #            mdrun terminates with an error message. For pair interactions and tabulated bonds \
                            #            that do not generate exclusions, this check can be turned off with the option -noddcheck.
                            #-rdd      : real   0  The maximum distance for bonded interactions with DD (nm), \
                            #           0 is determined from initial coordinates.
                            #           Option -rdd can be used to set the required maximum distance for inter charge-group bonded interactions. \
                            #           Communication for two-body bonded interactions below the non-bonded cut-off distance always comes for \
                            #           free with the non-bonded communication. Atoms beyond the non-bonded cut-off are only communicated \
                            #           when they have missing bonded interactions; this means that the extra cost is minor and nearly independent \
                            #           of the value of -rdd. With dynamic load balancing option -rdd also sets the lower limit \
                            #           for the domain decomposition cell sizes. By default -rdd is determined by mdrun based on the initial coordinates. \
                            #           The chosen value will be a balance between interaction range and communication cost.
            
    command_used = final_prepare_cryo_fit(number_of_available_cores, nproc, common_command_string, restart_w_longer_steps)
    command_used = command_used + "\n"    
    return command_used
####################### end of first_prepare_cryo_fit function


def first_prepare_minimization(ns_type, number_of_available_cores, \
                                   nproc, cryo_fit_path):
    common_command_string = cryo_fit_path + "mdrun -v -s to_minimize.tpr -c minimized.gro "    
    command_used = final_prepare_minimization(ns_type, number_of_available_cores, nproc,\
                                                               common_command_string)
        
    command_used = command_used + "\n"    
    return command_used
####################### end of first_prepare_minimization function


def get_fc(complete_set, xray_structure):
  f_calc = complete_set.structure_factors_from_scatterers(
    xray_structure=xray_structure).f_calc()
  return f_calc


def get_fft_map(map_coeffs=None):
    from cctbx import maptbx
    from cctbx.maptbx import crystal_gridding
    ccs=map_coeffs.crystal_symmetry()
    fft_map = map_coeffs.fft_map( resolution_factor = 0.25,
       symmetry_flags=maptbx.use_space_group_symmetry)
    fft_map.apply_sigma_scaling()
    return fft_map.real_map_unpadded().as_double()
########### end of get_fft_map function


def get_release_tag():
  release_tag = os.environ.get("PHENIX_RELEASE_TAG", None)
  return release_tag
########### end of def get_release_tag():


# not used for now, but will be used in future
def get_structure_factor_from_pdb_string () :
  prefix = "tmp_iotbx_map_tools"
  pdb_file = prefix + ".pdb"
  mtz_file = prefix + ".mtz"
  pdb_in = iotbx.pdb.hierarchy.input(pdb_string="""\
ATOM      1  N   GLY P  -1     -22.866  -2.627  15.217  1.00  0.00           N
ATOM      2  CA  GLY P  -1     -22.714  -3.068  16.621  1.00  0.00           C
ATOM      3  C   GLY P  -1     -21.276  -3.457  16.936  1.00  0.00           C
ATOM      4  O   GLY P  -1     -20.538  -3.887  16.047  1.00  0.00           O
ATOM      5  H1  GLY P  -1     -22.583  -3.364  14.590  1.00  0.00           H
ATOM      6  H2  GLY P  -1     -22.293  -1.817  15.040  1.00  0.00           H
ATOM      7  H3  GLY P  -1     -23.828  -2.392  15.027  1.00  0.00           H
""")
  xrs = pdb_in.input.xray_structure_simple()
# x-ray structure

#  open(pdb_file, "w").write(pdb_in.hierarchy.as_pdb_string(xrs))
  fc = xrs.structure_factors(d_min=1.5).f_calc()
  #print dir(fc).statistical_mean
############# end of get_structure_factor_from_pdb_string function


def get_users_cc(cc_record):
  #print "\tGet the first cc in this cc_record."
  f_in = open(cc_record)
  for line in f_in:
    splited = line.split(" ")
    cc = splited[4]
    f_in.close()
    print("\tThe first cc in this cc_record: ", cc)
    return cc
################ end of get_users_cc(cc_record)


def get_version():
    version = os.environ.get("PHENIX_VERSION", None)
    if (version is None):
      tag_file = libtbx.env.under_dist("libtbx", "../TAG")
      if (os.path.isfile(tag_file)):
        try: version = open(tag_file).read().strip()
        except KeyboardInterrupt: raise
        except: pass
    return version
############# end of def get_version():


def id_shell():
  from os import environ
  print("User is using ", environ['SHELL'] , " shell")
  splited = environ['SHELL'].split("/")
  shell = splited[2]
  return shell
#################### end of id_shell ()


def kill_mdrun_mpirun_in_linux():
    color_print ("\tkill any existing mdrun jobs (gromacs)", 'green')
    command_string = "top -b -d 1 | head -200 > top_200"
    libtbx.easy_run.call(command=command_string) 
    
    f = open('top_200', 'r')
    for line in f:
      splited = line.split()
      if len(splited) == 12:
        if splited[11] == "mdrun" or splited[11] == "mpirun":
          command_string = "kill " + splited[0]
          print(command_string)
          libtbx.easy_run.call(command=command_string) 
    f.close()
################# end of kill_mdrun_mpirun_in_linux function


def know_number_of_atoms_in_input_pdb(starting_pdb):
    command_string = "cat " + starting_pdb + " | grep ATOM | wc -l"
    #print "\tcommand: ", command_string
    num_ATOMs = libtbx.easy_run.fully_buffered(command=command_string).raise_if_errors().stdout_lines
    number_of_atoms_in_input_pdb = int(num_ATOMs[0])
    print("\t\tThis pdb file, ", starting_pdb, ", has ", number_of_atoms_in_input_pdb, " atoms")
    return number_of_atoms_in_input_pdb
################# end of know_number_of_atoms_in_input_pdb()


''' # no longer needed
def know_output_bool_enable_mpi_by_ls():
    # used exit early for users who didn't install cryofit yet as well
    output_bool_enable_mpi = ''
    home_dir = expanduser("~")
    home_cryo_fit_bin_dir = home_dir + "/bin/gromacs-4.5.5_cryo_fit"
    #print "\thome_cryo_fit_bin_dir:", home_cryo_fit_bin_dir
    if (os.path.exists(home_cryo_fit_bin_dir) == False):
        print "\nInstall cryo_fit first. Refer http://www.phenix-online.org/documentation/reference/cryo_fit.html"
        print "exit now"
        exit(1)
    output_bool_enable_mpi = False
    return output_bool_enable_mpi
# end of know_output_bool_enable_mpi_by_ls function
'''

def know_home_cryo_fit_bin_dir_by_ls_find(): # really used
    home_dir = expanduser("~")
    home_cryo_fit_bin_dir = ''
    command_string = "ls ~/bin | grep gromacs-4.5.5_cryo_fit"
    #print "\n\tcommand: ", command_string
    folder_of_cryo_fit = libtbx.easy_run.fully_buffered(command=command_string).raise_if_errors().stdout_lines
    
    if folder_of_cryo_fit[0].find("mpi") == -1:
        #print "\tUser's cryo_fit was installed with enable_mpi=False, so the cryo_fit will run as enable_mpi = False"
        home_cryo_fit_bin_dir = home_dir + "/bin/gromacs-4.5.5_cryo_fit/bin"
    else: # folder_of_cryo_fit[0] == "gromacs-4.5.5_cryo_fit_added_mpi":
        home_cryo_fit_bin_dir = home_dir + "/bin/gromacs-4.5.5_cryo_fit_mpi/bin"
    return home_cryo_fit_bin_dir
################# end of know_output_bool_enable_mpi_by_ls_find function


def know_total_number_of_cores():
    if ((platform.system() != "Darwin") and (platform.system() != "Linux")):
        color_print ("User's computer's operating system could be windows")
        number_of_total_cores = 1
        return number_of_total_cores
        
    number_of_total_cores = '' # just initial value
    if (platform.system() == "Darwin"):
        command_string = "sysctl -n hw.ncpu "
        number_of_total_cores = subprocess.check_output(command_string, stderr=subprocess.STDOUT,shell=True)
    elif (platform.system() == "Linux"):
        command_string = "nproc"
        number_of_total_cores = subprocess.check_output(command_string, stderr=subprocess.STDOUT,shell=True)
    else: # maybe Windows
        number_of_total_cores = 2
        
    #python 3 compatibility 
    ntc=type(number_of_total_cores)
    if ntc is str:
        pass
    elif ntc is bytes:
        number_of_total_cores=number_of_total_cores.decode()
    
    print("\tUser's computer's operating system: " + platform.system(), "\n")
    return number_of_total_cores
######### end of know_total_number_of_cores function


def locate_Phenix_executable():
    cryo_fit_repository_dir = libtbx.env.dist_path("cryo_fit")
    cryo_fit_repository_dir = cryo_fit_repository_dir + "/" # for later
    print("\tcryo_fit_repository_dir:",cryo_fit_repository_dir)
    return cryo_fit_repository_dir
    
    ''' # not needed but keep for other applications
    path = check_output(["which", "phenix.cryo_fit"])
    splited = path.split("/")
    command_path = ''
    for i in range(len(splited)-3):
      command_path = command_path + splited[i] + "/"
    command_path = command_path + "modules/cryo_fit/"
    print "\tUser's phenix.cryo_fit executable comes from ", command_path
    STOP()
    return command_path
    '''
############################## end of locate_Phenix_executable function


def make_trajectory_gro(cryo_fit_path):
    print("\n\tMake a trajectory.gro file")
    current_directory = os.getcwd()

    command_string = "echo 0 > input_parameter" # to select system
    print("\t\tcommand: ", command_string)
    libtbx.easy_run.fully_buffered(command_string)
    command_string = cryo_fit_path + "trjconv -f traj.xtc -o trajectory.gro -s for_cryo_fit.tpr < input_parameter"
    print("\t\tcommand: ", command_string)
    libtbx.easy_run.fully_buffered(command_string)
    
    if (os.path.isfile("trajectory.gro") == False):
        print("no trajectory.gro file, exit here")
        STOP()
    os.remove("input_parameter")
######################## end of def make_trajectory_gro():
    

def minimize(cores_to_use, ns_type, common_command_string):
    command_string = common_command_string + " -nt 1 -dd 1 1 1 "
    print("\tcommand: ", command_string)
    libtbx.easy_run.call(command=command_string)
    return command_string
######################## end of minimize function


def mrc_to_sit(inputs, map_file_name, pdb_file_name):
    print("\n\tConvert mrc format map to situs format map")
    
    new_map_file_name = ''
    if ((map_file_name[len(map_file_name)-4:len(map_file_name)] == ".map") or \
        (map_file_name[len(map_file_name)-4:len(map_file_name)] == ".mrc")):
        new_map_file_name = map_file_name[:-4] + "_converted_to_sit.sit"
    elif (map_file_name[len(map_file_name)-5:len(map_file_name)] == ".ccp4"):
        new_map_file_name = map_file_name[:-5] + "_converted_to_sit.sit"
    
    new_map_file_name = new_map_file_name.replace(" ","")
    new_map_file_name = new_map_file_name.replace("(","")
    new_map_file_name = new_map_file_name.replace(")","")
    # macOS can't deal with /bin/sh: -c: line 0: syntax error near unexpected token `('
    #/bin/sh: -c: line 0: `DYLD_FALLBACK_LIBRARY_PATH="/Users/doonam/bin/phenix-1.15rc3-3442/build/lib:/Users/doonam/bin/phenix-1.15rc3-3442/build/../conda_base/lib" exec python runme_cryo_fit.py /Users/doonam/bin/phenix-1.15rc3-3442/modules/cryo_fit/ 4 max /Users/doonam/research/cryo_fit/Nick/input/cryosparc_P20_J268_005_volume_map_sharp(5)_converted_to_sit.sit /Users/doonam/research/cryo_fit/Nick False False /Users/doonam/bin/cryo_fit/bin/'
    #Step 8  didn't successfully run
    
    f_out = open(new_map_file_name, 'wt')
    user_input_map = map_file_name
    # Compute a target map
    from iotbx import ccp4_map
    ccp4_map = ccp4_map.map_reader(user_input_map)
    print("\t\tMap read from %s" %(user_input_map))
    #used to work in older phenix versions
    #target_map_data = ccp4_map.map_data()
    #new code for phenix-1.19
    target_map_data = ccp4_map.map_data().as_double()
    
    #print "\tdir(): ", dir(ccp4_map)
    # acc = target_map_data.accessor() # not used, but keep for now
    print("\t\ttarget_map_data.origin():",target_map_data.origin())

    emmap_z0 = target_map_data.origin()[2] # tRNA: 0, nucleosome: -98
    emmap_y0 = target_map_data.origin()[1] # tRNA: 0, nucleosome: -98
    emmap_x0 = target_map_data.origin()[0] # tRNA: 0, nucleosome: -98
    
    ori_emmap_z0 = emmap_z0 # very original origin in z axis
    ori_emmap_y0 = emmap_y0 # very original origin in y axis
    ori_emmap_x0 = emmap_x0 # very original origin in x axis
    
    print("\t\tccp4_map.unit_cell_parameters", ccp4_map.unit_cell_parameters)
    a,b,c = ccp4_map.unit_cell_parameters[:3]
    #print "\t\tccp4_map.unit_cell_parameters[:3]:", ccp4_map.unit_cell_parameters[:3]
    # L1 stalk: (377.9999694824219, 377.9999694824219, 377.9999694824219)
    # emd_8249: (126.72000122070312, 126.72000122070312, 126.72000122070312
    # tRNA: (74.4800033569336, 63.70000076293945, 72.52000427246094)
    print("\t\ttarget_map_data.all():",target_map_data.all())
    # L1 stalk: (169, 158, 156), emd_8249: (24, 24, 24), tRNA: (76, 65, 74)
    
    ##### this works for most maps except phenix.map_box ed maps
    #widthx = a/target_map_data.all()[0]
    # tutorial            : 0.945000010835
    # L1 stalk (original?): 2.23668620996
    # L1 stalk map boxed  : 3.81818150992 -> will bring cc as nan
    
    widthx = a/ccp4_map.unit_cell_grid[0]
    
    print("\t\twidthx:", widthx) # with nucleosome, I confirmed that widthx doesn't change by origin shift
    # James_new_relion_image_handled_400: 0.665
    # James_new_original:                 0.665000047141
    
    origin_shited_to_000 = False # just assume that it will not be shifted
    shifted_in_x = 0
    shifted_in_y = 0
    shifted_in_z = 0 
    print("\t\t(before shifting map origin)")
    
    print("\t\tcurrent origins")
    print("\t\t\temmap_x0:",emmap_x0) # L1 stalk: 97, tRNA: 0, emd_1044: 0, emd_8249: -12
    print("\t\t\temmap_y0:",emmap_y0) # L1 stalk: 58, tRNA: 0, emd_1044: 0, emd_8249: -12
    print("\t\t\temmap_z0:",emmap_z0) # L1 stalk: 167, tRNA: 0, emd_1044: 52, emd_8249: -12
    
    ### (begin) shift map origin if current map origin != 0
    # when I gaussian filtered mrc by chimera, emmap_x0, emmap_y0, emmap_z0 were 0
    if (emmap_x0 != 0 or emmap_y0 != 0 or emmap_z0 != 0): 
        print("\t\t\tShift map origin since current map origin != 0")    
        origin_shited_to_000 = True
        pdb_inp = iotbx.pdb.input(file_name=pdb_file_name)
        model = mmtbx.model.manager(
            model_input = pdb_inp,
            crystal_symmetry=inputs.crystal_symmetry)
            #, build_grm=True) #no longer needed
        target_map_data = shift_origin_of_mrc_map_if_needed(target_map_data, model)
    
        shifted_in_z = target_map_data.origin()[2] - emmap_z0
        shifted_in_y = target_map_data.origin()[1] - emmap_y0
        shifted_in_x = target_map_data.origin()[0] - emmap_x0
        
        # origin is shifted, so reassign emmap_z0,y0,x0
        emmap_z0 = target_map_data.origin()[2] # L1_stalk: 167, tRNA: 0, nucleosome: -98, emd_1044: 52, emd_8249: 0
        emmap_y0 = target_map_data.origin()[1] # L1_stalk: 58, tRNA: 0, nucleosome: -98, emd_1044: 0, emd_8249: 0
        emmap_x0 = target_map_data.origin()[0] # L1_stalk: 97, tRNA: 0, nucleosome: -98, emd_1044: 0, emd_8249: 0
        print("\t\t\ttarget_map_data.origin() after shifting:",target_map_data.origin())
        
        print("\t\t\t(after shifting map origin)")
        print("\t\t\t\temmap_x0 (origin in x axis):",emmap_x0)
        print("\t\t\t\temmap_y0 (origin in y axis):",emmap_y0)
        print("\t\t\t\temmap_z0 (origin in z axis):",emmap_z0)
    ### (end) shift map origin
        #pdb_file_name = translate_pdb_file_by_xyz(pdb_file_name, shifted_in_x, shifted_in_y, shifted_in_z, widthx, False)
    #'''
    
    
    ''' # "shifting map origin whether current map origin != 0 or = 0" failed the regression
    print "\t\t\tShift map origin whether current map origin != 0 or = 0"
    origin_shited_to_000 = True
    pdb_inp = iotbx.pdb.input(file_name=pdb_file_name)
    model = mmtbx.model.manager(
        model_input = pdb_inp,
        crystal_symmetry=inputs.crystal_symmetry,
        build_grm=True)
    target_map_data = shift_origin_of_mrc_map_if_needed(target_map_data, model)

    shifted_in_z = target_map_data.origin()[2] - emmap_z0
    shifted_in_y = target_map_data.origin()[1] - emmap_y0
    shifted_in_x = target_map_data.origin()[0] - emmap_x0
    
    # origin is shifted, so reassign emmap_z0,y0,x0
    emmap_z0 = target_map_data.origin()[2] # tRNA: 0, nucleosome: -98, emd_1044: 52, emd_8249: 0
    emmap_y0 = target_map_data.origin()[1] # tRNA: 0, nucleosome: -98, emd_1044: 0, emd_8249: 0
    emmap_x0 = target_map_data.origin()[0] # tRNA: 0, nucleosome: -98, emd_1044: 0, emd_8249: 0
    print "\t\t\ttarget_map_data.origin() after shifting:",target_map_data.origin()
    
    print "\t\t\t(after shifting map origin)"
    print "\t\t\t\temmap_x0:",emmap_x0
    print "\t\t\t\temmap_y0:",emmap_y0
    print "\t\t\t\temmap_z0:",emmap_z0
    '''
    
    print("\t\ttarget_map_data.all():", target_map_data.all()) # for L1 stalk, 169, 158, 156
    
    print("\n\t\tConversion of mrc-> sit started.")
    print("\t\t\t(If a user's mrc map file is big like ~300MB, this conversion takes 7~17 minutes requiring ~1.5 Gigabytes of harddisk)")
    print("\t\t\t(Therefore, if a user want to re-run cryo_fit, providing the already converted .sit file will save the conversion time)")
    print("\t\t\t(However, reading ~1.5 gigabytes .sit file also takes > 5 minutes anyway)\n")
    
    emmap_nz = target_map_data.all()[2] # L1 talk: 156, H40: 109, nucleosome: 196
    emmap_ny = target_map_data.all()[1] # L1 talk: 158, H40: 104, nucleosome: 196
    emmap_nx = target_map_data.all()[0] # L1 talk: 169, H40: 169, nucleosome: 196
    
    print("\t\t\t\temmap_nx (dimension in x axis):",emmap_nx)
    print("\t\t\t\temmap_ny (dimension in y axis):",emmap_ny)
    print("\t\t\t\temmap_nz (dimension in z axis):",emmap_nz)
    
    #print "\n\t\t\t\temmap_x/y/z0 are origins in x/y/z axis"
    line = str(widthx) + " " + str(emmap_x0) + " " + str(emmap_y0) + " " + str(emmap_z0) + " " + str(emmap_nx) + " " + str(emmap_ny) + " " + str(emmap_nz) + "\n"
    
    ############ only use for temporary development!!!!!!!!
    #line = str(1) + " " + str(emmap_x0) + " " + str(emmap_y0) + " " + str(emmap_z0) + " " + str(emmap_nx) + " " + str(emmap_ny) + " " + str(emmap_nz) + "\n"
    
    f_out.write(line)
    
    counter = 0
    for k in range(emmap_z0, emmap_nz): # L1 stalk: 0 ~ 155
      for j in range(emmap_y0, emmap_ny): # L1 stalk: 0 ~ 157
        for i in range(emmap_x0, emmap_nx): # L1 stalk: 0 ~ 168
            #print "i:",i # emd_8249:0.0, tRNA: 0.0, emd_1044: 0.0
            #print "j:",j # emd_8249:0.0, tRNA: 0.0, emd_1044: 0.0
            #print "k:",k # emd_8249:0.0, tRNA: 0.0, emd_1044: 52
            
            x=i/emmap_nx
            y=j/emmap_ny
            z=k/emmap_nz
          #  print "x:",x # first value of L1 stalk:0, emd_8249:0.0, tRNA: 0.0, emd_1044: 0.0
          #  print "y:",y # first value of L1 stalk:0, emd_8249:0.0, tRNA: 0.0, emd_1044: 0.0
          #  print "z:",z # first value of L1 stalk:0, emd_8249:0.0, tRNA: 0.0, emd_1044: 0.945454545455
            value = target_map_data.value_at_closest_grid_point((x,y,z)) # doesn't work when x,y,z < 0
            
            # print "value: %10.6f" %value,
            line = " " + str(value)
            f_out.write(line)
            counter = counter + 1
            if (counter==10):
              counter=0
              f_out.write("\n")
    f_out.write("\n")
    f_out.close()
    
    if (origin_shited_to_000 == True):
        print("\t\t\tReassign shifted_origin into original ones (not necessarily to 0,0,0)")
        print("\t\t\tThis reassigning of origins is needed so that step_8 cryo_fit can run model and map superposed as seen with fastest_run_emd_8249")
        print("\t\t\tmap_file_name:", map_file_name)
        
        new_map_file_name_w_ori_origins = new_map_file_name[:-4] + "_converted_to_sit_origin_recovered.sit"
        
        print("\t\t\tnew_map_file_name_with original origins:", new_map_file_name_w_ori_origins)
        f_in = open(new_map_file_name, 'r')
        f_out = open(new_map_file_name_w_ori_origins, 'wt')
        first_line = True
        for line in f_in:
            if (first_line == True):
                # ori_emmap_x/y/z0 -> very original origins in x/y/z axis
                # for L1 stalk, ori_emmap_x/y/z0 = 97, 58, 167 
                # for L1 stalk, emmap_nx/y/z = 169, 158, 156
                line = str(widthx) + " " + \
                       str(widthx*ori_emmap_x0) + " " + str(widthx*ori_emmap_y0) + " " + str(widthx*ori_emmap_z0) + " " +\
                       str(emmap_nx) + " " + str(emmap_ny) + " " + str(emmap_nz) + "\n"
                first_line = False
            f_out.write(line)
        f_in.close()
        f_out.close()
        return new_map_file_name_w_ori_origins
    else:
        return new_map_file_name
################ end of mrc_to_sit(map_file_name)


def print_author():
  version = get_version()
  release_tag = get_release_tag()
  print("""\
 %s
  cryo_fit %s 
    - Doo Nam Kim, Nigel Moriarty, Serdal Kirmizialtin, Billy Poon, Karissa Sanbonmatsu
 %s""" % ("-"*78, version, "-"*78))
########## end of print_author()


def remake_and_move_to_this_folder(starting_dir, this_folder):
  if (os.path.isdir(this_folder) == True):
      shutil.rmtree(this_folder)
  os.mkdir(this_folder)
  
  new_path = starting_dir + "/" + this_folder
  os.chdir( new_path )
################ end of remake_and_move_to_this_folder function


def remake_this_folder(this_folder):
  if (os.path.isdir(this_folder) == True):
      #print "\tRemove a former " + this_folder + " folder"
      shutil.rmtree(this_folder)
  #print "\tMake a new " + this_folder + " folder"
  os.mkdir(this_folder)
################# end of remake_this_folder function


def remove_former_files():
    current_directory = os.getcwd()
    print("\tRemove former files in ", current_directory)
    for each_file in glob.glob("*"):
      if (each_file[:1] == "#") or (each_file[-1:] == "~") or (each_file[-4:] == ".edr") \
        or (each_file == "cryo_fit_log") or (each_file[-4:] == ".log") or (each_file == "md.log") \
        or (each_file[-4:] == ".trr") or (each_file[-4:] == ".xtc") or (each_file == "md.out"):
          subprocess.call(["rm", each_file])
############################## end of remove_former_files function 


def remove_water_for_gromacs(input_pdb_file_name):
    f_in = open(input_pdb_file_name)
    output_pdb_file_name = input_pdb_file_name[:-4] + "_wo_HOH.pdb"
    f_out = open(output_pdb_file_name, 'wt')
    for line in f_in:
      if line[17:20] != "HOH":
        f_out.write(line)
    f_in.close()
    f_out.close()
    return output_pdb_file_name
    # using construct_hierarchy() will be great, but my own code would be much faster to develop
    '''
    pdb_input = iotbx.pdb.input(file_name=file)
    pdb_hierarchy = pdb_input.construct_hierarchy()
    for model in pdb_hierarchy.models():
      chains = model.chains()
      for chain in chains:
        conformers = chain.conformers()
        for conformer in conformers:
          residues = conformer.residues()
          for residue in residues:
            print "residue.resname:", residue.resname
    '''
########################### end of remove_water_for_gromacs ()


def renumber_cc_record_full(cc_record_full):
   f_in = open(cc_record_full)
   renumbered_cc_record_full = cc_record_full + "_renumbered"
   f_out = open(renumbered_cc_record_full, "w")
   old_step = -9
   add_this_step = 0
   #step_gap = 0
   # step_gap was useful for cc_record_full_renumbered alone, \
   # but better not used for matching extracted.gro/pdb and cc_record_full_renumbered
   for line in f_in:
      splited = line.split(" ")
      step = splited[1]
      if (int(step) > int(old_step)):
         #if (int(step_gap) == 0):
         #   if (int(old_step) == 0):
         #      step_gap = int(step) - int(old_step)
         new_step = int(step)+int(add_this_step)
         new_line = splited[0] + " " + str(new_step) + " " + splited[2] + " " + splited[3] + " " + splited[4] + "\n"
         f_out.write(new_line)
         old_step = step
      else:
         #add_this_step = int(add_this_step) + int(old_step) + int(step_gap)
         add_this_step = int(add_this_step) + int(old_step)
         new_step = int(step)+int(add_this_step)
         new_line = splited[0] + " " + str(new_step) + " " + splited[2] + " " + splited[3] + " " + splited[4] + "\n"
         f_out.write(new_line)
         old_step = step
   f_out.close()
################################ end of renumber_cc_record_full


def return_number_of_atoms_in_gro():
  for check_this_file in glob.glob("*.gro"): # there will be only one *.gro file for step_5
    command_string = "wc -l " + check_this_file
    wc_result = libtbx.easy_run.fully_buffered(command=command_string).raise_if_errors().stdout_lines
    splited = wc_result[0].split()
    print("\tUser's ", check_this_file, " has ", str(splited[0]), " atoms")
    return str(splited[0])
############################## end of return_number_of_atoms_in_gro function


def run_cryo_fit_itself(cores_to_use, common_command_string, restart_w_longer_steps):
    command_string = '' # just initial
    print("\tRestarted with longer steps:", restart_w_longer_steps)
    if (cores_to_use == 2):
        if (str(restart_w_longer_steps) == "False"):
            command_string = common_command_string + " -nt 2 -dd 2 1 1 "
        else:
            command_string = common_command_string + " -nt 2 -dd 2 1 1 -cpi state.cpt"
    elif (cores_to_use == 4):
        if (str(restart_w_longer_steps) == "False"):
            command_string = common_command_string + " -nt 4 -dd 2 2 1 "
        else:
            command_string = common_command_string + " -nt 4 -dd 2 2 1 -cpi state.cpt"
    elif (cores_to_use == 8):
        if (str(restart_w_longer_steps) == "False"):
            command_string = common_command_string + " -nt 8 -dd 2 2 2 "
        else:
            command_string = common_command_string + " -nt 8 -dd 2 2 2 -cpi state.cpt"
    elif (cores_to_use == 12):
        if (str(restart_w_longer_steps) == "False"):
            command_string = common_command_string + " -nt 12 -dd 3 2 2 " # [keep this comment] for -nt 12, -dd 3 2 2 is needed instead of 2 2 3
        else:
            command_string = common_command_string + " -nt 12 -dd 3 2 2 -cpi state.cpt"
    else: #elif (cores_to_use == 16):
        if (str(restart_w_longer_steps) == "False"):
            command_string = common_command_string + " -nt 16 -dd 4 2 2 "
        else:
            command_string = common_command_string + " -nt 16 -dd 4 2 2 -cpi state.cpt"
    #else:
        # [keep this comment 4/27/2018]
        # command_string = common_command_string + " -nt " + str(cores_to_use) + " -dd 0 "
        # Major Warning: this resulted in "charge group moved" error in nuclesome with all emweights, although looks simpler and convinient
    
    print("\tcommand: ", command_string)
    libtbx.easy_run.call(command=command_string)
    return command_string
################ end of run_cryo_fit_itself function


def search_charge_in_md_log():
  command_string = "grep \"A charge group moved too far between two domain decomposition steps\" md.log > grepped"
  libtbx.easy_run.fully_buffered(command_string)
  returned_file_size = file_size("grepped")
  if (returned_file_size > 0):
    print("\tStep 8 (run cryo_fit) failed because of \"A charge group moved too far between two domain decomposition steps\" message in md.log")
    return 1 # found "charge group..."
  print("\n\t\"A charge group moved too far between two domain decomposition steps\" not found in md.log")
  return 0 # not found "charge group..."
################# end of search_charge_in_md_log function


def shift_origin_of_mrc_map_if_needed(map_data, model):
    print("\tShift_origin_of_mrc_map since needed")
    #soin = maptbx.shift_origin_if_needed(map_data=map_data,
    #    sites_cart=model.get_sites_cart(), crystal_symmetry=model.crystal_symmetry())
    soin = maptbx.shift_origin_if_needed(map_data=map_data,
        crystal_symmetry=model.crystal_symmetry())
    map_data = soin.map_data
    return map_data
################# end of shift_origin_of_mrc_map_if_needed ()


def shorten_file_name_if_needed(model_file_without_pathways):
  print("\tShorten_file_name_if_needed")

  if len(model_file_without_pathways) > 30:
    print("\tThe length of model_file_without_pathways (",len(model_file_without_pathways))
    print(") is too long for macOS like nucleosome_w_H1_histone_5nl0_ATOM_TER_END_fitted_to_map_emd_3659.pdb")
    print("\tTherefore, cryo_fit will copy another short named file.")
    extension = model_file_without_pathways[len(model_file_without_pathways)-4:len(model_file_without_pathways)]
    new_model_file_without_pathways = model_file_without_pathways[:20] + extension
    
    command_string = "mv " + model_file_without_pathways + " " +  new_model_file_without_pathways
    print("\tcommand: ", command_string)
    libtbx.easy_run.call(command=command_string)
    
    return new_model_file_without_pathways
  return model_file_without_pathways
################# end of shorten_file_name_if_needed


def show_header(title):
  print("\n")
  multiply_asterisk = 95
  print('#'*multiply_asterisk)
  number_of_remaining_sharp = multiply_asterisk - len(title)
  put_this_number_of_sharp = int(int(number_of_remaining_sharp)/2)
  print('#'*(put_this_number_of_sharp-1) + " " + title + " " + '#'*(put_this_number_of_sharp-1))
  print('#'*multiply_asterisk)
########### end of show_header function


def show_time(time_start, time_end):
    time_took = 0 # temporary of course
    if (round((time_end-time_start)/60, 1) < 1):
      time_took = " finished in " + str(round((time_end-time_start), 2)) + " seconds (wallclock)."
    elif (round((time_end-time_start)/60/60, 1) < 1):
      time_took = " finished in " + str(round((time_end-time_start)/60, 2)) + " minutes (wallclock)."
    else:
      time_took = " finished in " + str(round((time_end-time_start)/60/60, 1)) + " hours (wallclock)."
    return time_took
############### end of show_time function


def translate_pdb_file_by_xyz(input_pdb_file_name, move_x_by, move_y_by, move_z_by, widthx, retranslate_to_original):
    #print "\ttranslate_pdb_file_by_xyz"
    move_x_by = move_x_by*widthx
    move_y_by = move_y_by*widthx
    move_z_by = move_z_by*widthx
    f_in = open(input_pdb_file_name)
    if (retranslate_to_original == False):
        output_pdb_file_name = input_pdb_file_name[:-4] + "_translated" + ".pdb"
    else:
        output_pdb_file_name = input_pdb_file_name[:-4] + "_retranslated" + ".pdb"
    f_out = open(output_pdb_file_name, "w")
    for line in f_in:
      if line[0:4] == "ATOM" or line[0:6] == "HETATM":
        x_coor_former = line[30:38]
        
        if (retranslate_to_original == False):
            new_x_coor = str(float(x_coor_former) + float(move_x_by))
        else:
            new_x_coor = str(float(x_coor_former) - float(move_x_by))
       
        new_x_coor = str(round(float(new_x_coor), 3))
        
        splited = new_x_coor.split(".")
        multi_before_period = 4-len(splited[0])
        multi_after_period = 3-len(splited[1])
        new_line = line[:30] + multi_before_period*" "+splited[0] + "." + splited [1]+multi_after_period*" "
        
        y_coor_former = line[38:46]
        
        if (retranslate_to_original == False):
            new_y_coor = str(float(y_coor_former) + float(move_y_by))
        else:
            new_y_coor = str(float(y_coor_former) - float(move_y_by))
            
        new_y_coor = str(round(float(new_y_coor), 3))
        
        splited = new_y_coor.split(".")
        multi_before_period = 4-len(splited[0])
        multi_after_period = 3-len(splited[1])
        new_line = new_line + multi_before_period*" "+splited[0] + "." + splited [1]+multi_after_period*" "
        
        z_coor_former = line[46:54]
        
        if (retranslate_to_original == False):
            new_z_coor = str(float(z_coor_former) + float(move_z_by))
        else:
            new_z_coor = str(float(z_coor_former) - float(move_z_by))
        
        new_z_coor = str(round(float(new_z_coor), 3))
        
        splited = new_z_coor.split(".")
        multi_before_period = 4-len(splited[0])
        multi_after_period = 3-len(splited[1])
        new_line = new_line + multi_before_period*" "+splited[0] + "." + splited [1]+multi_after_period*" " \
              + line[54:]
        f_out.write(new_line)
        
      elif line[0:3] == "TER":
        f_out.write(line)
    f_in.close()
    f_out.close()
    return output_pdb_file_name   
########### end of translate_pdb_file_by_xyz ()


def write_for_cryo_fit_mdp(fout, fin, emsteps, time_step_for_cryo_fit, number_of_steps_for_cryo_fit, \
                         emweight_multiply_by, emwritefrequency, lincs_order, nstxtcout):
  for line in fin:
    splited = line.split()
    if splited[0] == "dt":
      new_line = "dt = " + str(time_step_for_cryo_fit) + "\n"
      fout.write(new_line)
    elif splited[0] == "emsteps":
      if (emsteps == None):
          new_line = "emsteps = " + str(int(number_of_steps_for_cryo_fit/100)) + "\n" # to make cryo_fit step 8 faster
          # when emsteps is too sparse, cc went to become worse
          fout.write(new_line)
      else:
        new_line = "emsteps = " + str(emsteps) + "\n"
        fout.write(new_line)
    elif splited[0] == "emweight":
      number_of_atoms_in_gro = return_number_of_atoms_in_gro()
      print("\temweight_multiply_by:", emweight_multiply_by)
      new_line = "emweight = " + str(int(number_of_atoms_in_gro)*int(emweight_multiply_by)) + "\n"
      fout.write(new_line)
    elif splited[0] == "emwritefrequency":
      if (emwritefrequency == None): # default is 1,000,000, because I don't see any usefulness of writing intermediate .sit file
        fout.write(line)
      else:
        new_line = "emwritefrequency = " + str(emwritefrequency) + "\n"
        fout.write(new_line)
    elif splited[0] == "lincs-order":
      if (lincs_order == None):
        fout.write(line)
      else:
        new_line = "lincs-order  = " + str(lincs_order) + "\n"
        fout.write(new_line)
    elif splited[0] == "nsteps":
      new_line = "nsteps          = " + str(number_of_steps_for_cryo_fit) + " ; Maximum number of steps to perform cryo_fit\n"
      fout.write(new_line)
    elif splited[0] == "nstxtcout":
      new_line = "nstxtcout          = " + str(nstxtcout) + "\n"
      fout.write(new_line)
    else:
      fout.write(line)
  fout.close()
  fin.close()
############### end of write_for_cryo_fit_mdp(fout, fin):
