import rclone
import re
from os.path import expanduser
import subprocess
import glob
import os, sys
import argparse

# nastavi poti do izvornih in odobrenih posnetkov na lokalnem disku in na strežniku nas.jcvt.si
izvorni_bkp = '/storage/rsdo/cjvt/BraniGovor/BraniGovor-04-FE-IzvorniPosnetki-bkp'
izvorni_nas_bkp = ':ASR/BraniGovor/BraniGovor-04-FE-IzvorniPosnetki-bkp'
odobreni = '/storage/rsdo/cjvt/BraniGovor/BraniGovor-05-FE-OdobreniPosnetki'
odobreni_nas = ':ASR/BraniGovor/BraniGovor-05-FE-OdobreniPosnetki'
odobreni_bkp = '/storage/rsdo/cjvt/BraniGovor/BraniGovor-05-FE-OdobreniPosnetki-bkp'
odobreni_nas_bkp = ':ASR/BraniGovor/BraniGovor-05-FE-OdobreniPosnetki-bkp'

class HiddenPrints:
  def __enter__(self):
    self._original_stdout = sys.stdout
    sys.stdout = open(os.devnull, 'w')

  def __exit__(self, exc_type, exc_val, exc_tb):
    sys.stdout.close()
    sys.stdout = self._original_stdout

ap = argparse.ArgumentParser(description = """
Primer klica funkcije:
python check_val.py -s FE-B-S0049 -g Artur-B-G0382 Artur-B-G0383 Artur-B-G0384 Artur-B-G0385 Artur-B-G0386 -n nas_cjvt -r
""")
ap._action_groups.pop()
required = ap.add_argument_group('required arguments')
optional = ap.add_argument_group('optional arguments')
required.add_argument('-s', '--snemalec',
  type = str,
  # ~ default = 'FE-B-S0049',
  metavar = 'SNEMALEC',
  help = "Snemalec (e.g. FE-B-S0049)."
  )
required.add_argument('-g', '--govorci',
  type = str,
  nargs = '+',
  # ~ default = ['Artur-B-G0382'],
  metavar = 'GOVOREC',
  help = "Lista govorcev (npr. 'Artur-B-G0382 Artur-B-G0383 Artur-B-G0384 Artur-B-G0385 Artur-B-G0386')."
  )
optional.add_argument('-c', '--rclone_config',
  type = str,
  default = '~/.config/rclone/rclone.conf',
  help = "Konfiguracijska datoteka za rclone ('/root/.config/rclone/rclone.conf' v primeru sudo rclone)."
  )
optional.add_argument('-n', '--remote_name',
  type = str,
  default = 'CJVT',
  help = "Ime rclone remote-a."
  )
optional.add_argument('-r', 
  action='store_true',
  help = "Argument s katerim vključimo preverjanje tudi na strežniku."
  )
args = ap.parse_args()


snemalec = args.snemalec
govorci = args.govorci

with open(expanduser(args.rclone_config), 'r') as config_file:
  config = config_file.read()

print('Snemalec %s:'%snemalec)
for g in govorci:
  print('\tGovorec %s:'%g)

  print('\t\tLokalni računalnik:')

  sou_bkp_dir = os.path.join(izvorni_bkp, snemalec, g)
  if os.path.isdir(sou_bkp_dir):
    sou_bkp = len(glob.glob(os.path.join(sou_bkp_dir, '*')))
    print('\t\t\t#%s: %d'%(sou_bkp_dir, sou_bkp))
  else:
    print("\t\t\tMapa %s ne obstaja."%sou_bkp_dir)
    sou_bkp = -1

  acc_dir = os.path.join(odobreni, snemalec, g)
  if os.path.isdir(acc_dir):
    acc = len(glob.glob(os.path.join(acc_dir,'*')))
    print('\t\t\t#%s: %d'%(acc_dir, acc))
  else:
    print("\t\t\tMapa %s ne obstaja."%acc_dir)
    acc = -2

  acc_bkp_dir = os.path.join(odobreni_bkp,snemalec,g)
  if os.path.isdir(acc_bkp_dir):
    acc_bkp = len(glob.glob(os.path.join(acc_bkp_dir,'*')))
    print('\t\t\t#%s: %d'%(acc_bkp_dir, acc_bkp))
  else:
    print("\t\t\tMapa %s ne obstaja."%acc_bkp_dir)
    acc_bkp = -3

  rej_dir = os.path.join(izvorni_bkp,snemalec,'ZavrnjeniPosnetki',g)
  if os.path.isdir(rej_dir):
    rej = len(glob.glob(os.path.join(rej_dir,'*')))
    print('\t\t\t#%s: %d'%(rej_dir, rej))
  else:
    print("\t\t\tMapa %s ne obstaja."%rej_dir)
    rej = -3

  if acc == acc_bkp:
    chk = 'OK'
  else:
    chk = 'ERR'
  print('\t\t\t#odobreni = #odobreni_bkp ... %s'%chk)

  if sou_bkp - acc == rej:
    chk_bkp = 'OK'
  else:
    chk_bkp = 'ERR'
  print('\t\t\t#izvorni_bkp - #odobreni = #zavrnjeni ... %s'%chk_bkp)

  if args.r:
    print('\t\tStrežnik %s:'%args.remote_name)

    sou_nas_bkp_dir = os.path.join(args.remote_name+izvorni_nas_bkp,snemalec,g)
    with HiddenPrints():
      sou_nas_bkp = rclone.with_config(config).run_cmd(command='size', extra_args=[sou_nas_bkp_dir])
    if not sou_nas_bkp['error']:
      sou_nas_bkp = sou_nas_bkp['out'].decode('utf-8')
      sou_nas_bkp = int(re.search(r'\d+', sou_nas_bkp).group())
      print('\t\t\t#%s: %d'%(sou_nas_bkp_dir, sou_nas_bkp))
    else:
      print('\t\t\tNapaka pri branju %s: %s.'%(sou_nas_bkp_dir, str(sou_nas_bkp['error']).split('last error was:')[-1]))
      sou_nas_bkp = -1

    acc_nas_dir = os.path.join(args.remote_name+odobreni_nas,snemalec,g)
    with HiddenPrints():
      acc_nas = rclone.with_config(config).run_cmd(command='size', extra_args=[acc_nas_dir])
    if not acc_nas['error']:
      acc_nas = acc_nas['out'].decode('utf-8')
      acc_nas = int(re.search(r'\d+', acc_nas).group())
      print('\t\t\t#%s: %d'%(acc_nas_dir, acc_nas))
    else:
      print('\t\t\tNapaka pri branju %s: %s.'%(acc_nas_dir, str(acc_nas['error']).split('last error was:')[-1]))
      acc_nas = -2

    acc_nas_bkp_dir = os.path.join(args.remote_name+odobreni_nas_bkp,snemalec,g)
    with HiddenPrints():
      acc_nas_bkp = rclone.with_config(config).run_cmd(command='size', extra_args=[acc_nas_bkp_dir])
    if not acc_nas_bkp['error']:
      acc_nas_bkp = acc_nas_bkp['out'].decode('utf-8')
      acc_nas_bkp = int(re.search(r'\d+', acc_nas_bkp).group())
      print('\t\t\t#%s: %d'%(acc_nas_bkp_dir, acc_nas_bkp))
    else:
      print('\t\t\tNapaka pri branju %s: %s.'%(acc_nas_bkp_dir, str(acc_nas_bkp['error']).split('last error was:')[-1]))
      acc_nas_bkp = -3

    rej_nas_dir = os.path.join(args.remote_name+izvorni_nas_bkp,snemalec,'ZavrnjeniPosnetki',g)
    with HiddenPrints():
      rej_nas = rclone.with_config(config).run_cmd(command='size', extra_args=[rej_nas_dir])
    if not rej_nas['error']:
      rej_nas = rej_nas['out'].decode('utf-8')
      rej_nas = int(re.search(r'\d+', rej_nas).group())
      print('\t\t\t#%s: %d'%(rej_nas_dir, rej_nas))
    else:
      print('\t\t\tNapaka pri branju %s: %s.'%(rej_nas_dir, str(rej_nas['error']).split('last error was:')[-1]))
      rej_nas = -4

    if acc_nas == acc_nas_bkp:
      chk_nas = 'OK'
    else:
      chk_nas = 'ERR'
    print('\t\t\t#odobreni_nas = #odobreni_nas_bkp ... %s'%chk_nas)

    if sou_nas_bkp - acc_nas == rej_nas:
      chk_nas_bkp = 'OK'
    else:
      chk_nas_bkp = 'ERR'
    print('\t\t\t#izvorni_nas_bkp - #odobreni_nas = #zavrnjeni_nas ... %s'%chk_nas_bkp)
