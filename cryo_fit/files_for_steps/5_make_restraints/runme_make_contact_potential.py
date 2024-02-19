from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import glob, os, sys, shutil, re

''' # only needed for development
def remove_former_files():
    if os.path.isfile("disre1.itp"):
        print "remove a previous disre1.itp"
        os.system("rm disre1.itp")
    if os.path.isfile("disre2.itp"):
        print "remove a previous disre2.itp"
        os.system("rm disre2.itp")
# end of remove_former_files function
'''

def make_contact_potential(input_gro_file_name, cryo_fit_path):
  #remove_former_files() # only needed for separate running other than python overall running
  #os.system("echo 0 > pre_selected ") # make file pre_selected with content 0
  open('pre_selected','w').write('0\n')

  #home_cryo_fit_bin_dir = know_home_cryo_fit_bin_dir_by_ls_find()

  f_out = open('log.step_5', 'wt')
  command_used = cryo_fit_path + "genrestr -f " + input_gro_file_name + " -fc 500 500 500 -disre \
                 -cutoff 0.4 -o disre1.itp < pre_selected"
  # gmx genrestr produces an #include file for a topology containing a list of atom numbers and three force constants for thhe x-, y-, and z-direction based on the contents of the -f file. A single isotropic force constant may be given on the command line instead of three components.
  # -fc          vector 1000 1000 1000  force constants (kJ/mol nm^2)
  # -[no]disre   bool   no      Generate a distance restraint matrix for all the atoms in index
  # -cutoff      real   -1      Only generate distance restraints for atoms pairs within cutoff (nm)
  # -o      posre.itp  Output       Include file for topology
  # < 0 is to select Group     0 (         System) has  (1454) elements
  os.system(command_used)
  write_this_input_command = str(command_used) + "\n"
  f_out.write(write_this_input_command)
  #os.system("rm pre_selected")
  os.remove('pre_selected')

  '''
  command_used = "head -n 4 disre1.itp > disre2.itp"
  # this head -n 4 is....
  #; distance restraints for System of gromacs#

  #[ distance_restraints ]
  #;   i     j ? label      funct         lo        up1        up2     weight
  os.system(command_used)
  write_this_input_command = str(command_used) + "\n"
  f_out.write(write_this_input_command)
  # disre1.itp has too much obvious information. For example, everyone knows that atom 1 and 2 are covalently bonded.
  # Therefore, make disre2.itp for simpler usage
  command_used = "awk '{ if (($1-$2) < -5) print $1,$2,$3,NR-9,$5,$6,$6,$8,$9}' disre1.itp >> disre2.itp" 
  # disre2.itp has the restraints created by changing the square width potential (standard in gromacs) to umbrella potential 
  os.system(command_used)
  write_this_input_command = str(command_used) + "\n"
  f_out.write(write_this_input_command)
  '''
  infile='disre1.itp'
  outfile='disre2.itp'
  outlist=[]
  f=open(infile,'r').readlines()
  idx=1
  for i in f:
    j=i.split()
    if idx<5:
      outlist.append(i)
    elif (int(j[0])-int(j[1])<-5):
      k=(j[0],j[1],j[2],str(idx-9),j[4],j[5],j[5],j[7],j[8])
      outstr='%s %s %s %s %s %s %s %s %s\n'%k
      outlist.append(outstr)
    idx+=1
  open(outfile,'w').writelines(outlist)

  #cmd = "cp ../1_make_gro/*.top ." # there is only one .top file anyway
  #os.system(cmd)
  cur_dir=os.getcwd()
  cppath=os.path.join(os.path.dirname(cur_dir),'1_make_gro','*.top')
  cplst=glob.glob(cppath)
  for i in cplst:
    shutil.copy2(i,cur_dir)

  output_top_file_name = input_gro_file_name[:-4] + "_including_disre2_itp.top"
  '''
  command_used = " sed -e s/POSRES/DISRES/g -e s/posre.itp/disre2.itp/g *.top > " + output_top_file_name
  # after this step_3, two .top files will exist in the folder
  os.system(command_used)
  write_this_input_command = str(command_used) + "\n"
  f_out.write(write_this_input_command)
  f_out.close()
  '''
  for i in glob.glob('*.top'):
    f=open(i,'r').read()
    t1=re.sub('POSRES','DISRES',f)
    t2=re.sub('posre.itp','disre2.itp',t1)
    open(output_top_file_name,'w').write(t2)
    
# end of make_contact_potential function

#if (__name__ == "__main__") :

def run(args, log=sys.stdout):
  #args=sys.argv[1:]
  if len(args)<1:
    count = 0
    for gro_file in glob.glob("*.gro"):
      input_gro_file_name = gro_file # if there is only 1 top file in this folder, use it
      count +=1
      if count == 2:
        print("Please specify one input gro file")
        print("Example usage: runme_make_contact_potential.py input.gro")
        sys.exit("runme_make_contact_potential exits now (expecting a gro file at a next run)")
    make_contact_potential(input_gro_file_name)
  else:
    input_gro_file_name = args[0] # pdb input file
    command_path = args[1]
    cryo_fit_path = args[2]
    common_functions_path = os.path.join(command_path,'common_functions')
    sys.path.insert(0, common_functions_path)
    #from common_functions import *
    
    make_contact_potential(input_gro_file_name, cryo_fit_path)

########## end of run()########
if (__name__ == "__main__") :
  run(sys.argv[1:])  
        
