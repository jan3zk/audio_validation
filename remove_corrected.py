import os
import pandas as pd
import numpy as np
import argparse


def remove_corrected(xlsx_file, txt_file):
  xfile = pd.read_excel(xlsx_file)
  tfile = np.loadtxt(txt_file,dtype=str)
  print('Število zavrnitev pred popravki: %d.'%xfile['napaka'].count())
  for tf in tfile:
     xfile.loc[xfile['ID koda govorca:'] == os.path.splitext(tf)[0], 'napaka'] = np.nan
     xfile.loc[xfile['ID koda govorca:'] == os.path.splitext(tf)[0], 'opis'] = np.nan
  print('Število zavrnitev po popravkih: %d.'%xfile['napaka'].count())
  xwriter = pd.ExcelWriter(os.path.basename(xlsx_file), engine='openpyxl')
  xfile.to_excel(xwriter, index=False, sheet_name='povedi_za_snemanje')
  xwriter.sheets['povedi_za_snemanje'].column_dimensions['A'].width = 22
  xwriter.sheets['povedi_za_snemanje'].column_dimensions['B'].width = 90
  xwriter.sheets['povedi_za_snemanje'].column_dimensions['C'].width = 10
  xwriter.sheets['povedi_za_snemanje'].column_dimensions['D'].width = 60
  xwriter.sheets['povedi_za_snemanje'].column_dimensions['E'].width = 60
  xwriter.save()
  

if __name__ == '__main__':

  ap = argparse.ArgumentParser()
  ap.add_argument("-x",
    type = str,
    metavar = "XLSX_FILE",
    help = "Po do datoteke XLSX s seznamom povedi.")
  ap.add_argument("-t", 
    type = str,
    metavar = "TXT_FILE",
    help = "Po do datoteke TXT s seznamom odobrenih popravljenih povedi.")
  args = ap.parse_args()

  remove_corrected(args.x, args.t)
