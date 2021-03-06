import argparse
import pandas as pd
import os

ap = argparse.ArgumentParser()
ap._action_groups.pop()
required = ap.add_argument_group('required arguments')
optional = ap.add_argument_group('optional arguments')
required.add_argument("-x",
  type = str,
  metavar = "XLSX_FILE",
  help = "Pot do datoteke XLSX s seznamom povedi.")
optional.add_argument("-w",
  type = str,
  metavar = "WAV_DIR",
  default = "",
  help = "Direktorij s posnetki WAV.")
ap.add_argument('-n',
  type = str,
  nargs = '+',
  default = '',
  help = "Seznam napak, ki naj se upoštevajo (npr. 'a b f').")
args = ap.parse_args()

xlsx_file = args.x
wav_path = args.w
if wav_path:
  if not wav_path.endswith(os.path.sep):
    wav_path += os.path.sep

xlist = pd.read_excel(args.x, engine='openpyxl')
xfile_tmp = []
if args.n:
  for err_lbl in args.n:
    xfile_tmp.append(xlist.loc[xlist['napaka'] == err_lbl,'ID koda govorca:'])
  xfile = pd.concat(xfile_tmp)
  xfile = xfile.sort_index()
else:
  xfile = xlist.loc[xlist['napaka'].notna(),'ID koda govorca:']
xfile = wav_path + xfile + '.wav'
txt_file = os.path.splitext(xlsx_file)[0]+'.txt'
xfile.to_csv(txt_file, sep='\t', index=False, header=False)
