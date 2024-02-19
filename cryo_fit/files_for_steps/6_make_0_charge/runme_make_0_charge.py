from __future__ import absolute_import
from __future__ import division
from __future__ import print_function
import glob, os, sys

def make_0_charge(input_top_file_name):
  output_top_name = input_top_file_name[:-4] + "_0_charge.top"
  cmd = "awk -f changetop.awk < " + input_top_file_name + " > " + output_top_name
  os.system(cmd)

def make_0_charge2(input_top_file_name):
  #Replacing the original awk script. LWH Oct-2023
  f_in=input_top_file_name
  f_out=input_top_file_name[:-4] + "_0_charge.top"
  toplist=open(f_in,'r').readlines()
  edit1=['[ atoms ]\n']
  edit0=['[ pairs ]\n','[ bonds ]\n','[ exclusions ]\n','[ angles ]\n',\
         '[ dihedrals ]\n','[ system ]\n','[ moleculetype ]\n']
  zerolist=[]
  edit=False
  skip=[';','\n','#']
  for i in toplist: 
    if edit:
      if i in edit0:
        edit=False
        zerolist.append(i)
      elif i[0] in skip:
        zerolist.append(i)
      else:
        c=i.split()
        if i[0] not in skip and len(c)==11:
          j="{:6d}{:>11}{:7d}{:>7}{:>7}{:7d}{:11.4f}{:>11}"\
             .format(int(c[0]),c[1],int(c[2]),c[3],c[4],int(c[5]),float('0.0000'),c[7])
          j1=j+'\n'
          zerolist.append(j1)
        else:
          zerolist.append(i)
    else:
      if i in edit1:
        edit=True
        zerolist.append(i)
      else:
        zerolist.append(i)
  open(f_out,'w').writelines(zerolist)
  return f_out
    
#if (__name__ == "__main__") :

def run(args, log=sys.stdout):
  #args=sys.argv[1:]
  if len(args)<1:
    count = 0
    for top_file in glob.glob("*.top"):
      input_top_file_name = top_file # if there is only 1 top file in this folder, use it
      count +=1
      if count == 2:
        print("Please specify one input top file")
        print("example usage: runme_make_0_charge.py input.top")
        sys.exit("runme_make_0_charge exits now (expecting a top file at next run)")
    make_0_charge2(input_top_file_name)
  else:
    input_top_file_name=args[0] # pdb input file
    make_0_charge2(input_top_file_name)

########## end of run()########
if (__name__ == "__main__") :
  run(sys.argv[1:])  
        
