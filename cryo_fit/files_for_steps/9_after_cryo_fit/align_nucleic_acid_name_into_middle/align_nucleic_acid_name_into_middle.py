from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import glob, os

def align_nucleic_acid_name_into_middle(input_pdb_file_name):
  f_in = open(input_pdb_file_name)
  output_pdb_file_name = input_pdb_file_name[:-4] + "_aligned_NA_name_into_middle.pdb"
  f_out = open(output_pdb_file_name, 'wt')
  for line in f_in:
    residue = line[17:20].strip()
    print("residue:", residue)
    if (residue == "A"):
      new_line = line[:17] + ' A ' + line[20:]
      f_out.write(new_line)
    elif (residue == "T"):
      new_line = line[:17] + ' T ' + line[20:]
      f_out.write(new_line)
    elif (residue == "U"):
      new_line = line[:17] + ' U ' + line[20:]
      f_out.write(new_line)
    elif (residue == "G"):
      new_line = line[:17] + ' G ' + line[20:]
      f_out.write(new_line)
    elif (residue == "C"):
      new_line = line[:17] + ' C ' + line[20:]
      f_out.write(new_line)
    else:
      f_out.write(line)
  f_in.close()
  f_out.close()
  #cmd = "rm " + input_pdb_file_name
  #os.system(cmd)
  os.remove(input_pdb_file_name)
  return output_pdb_file_name
####### end of align_nucleic_acid_name_into_middle function

def run(args, log=sys.stdout):
  for pdb_file in glob.glob("*.pdb"):
      print(pdb_file)
      with open(pdb_file) as f_in:
          align_nucleic_acid_name_into_middle(pdb_file)
      
########## end of run()########
if (__name__ == "__main__") :
  run(sys.argv[1:])  
