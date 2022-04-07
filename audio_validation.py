# -*- coding: utf-8 -*-
print('Loading libraries ...')
import sys
from glob import glob
import os
import argparse
import soundfile as sf
import numpy as np
import sox
import matplotlib.pyplot as plt
import pandas as pd
from pydub import AudioSegment,silence
from pydub.playback import play
import speech_recognition as sr
import re
import tkinter.filedialog as filedialog
import tkinter as tk
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import tkinter.scrolledtext as st
import datetime
import difflib as dl
from num2words import num2words
from jiwer import wer
from openpyxl.styles import Alignment
import pyloudnorm as pyln
from utils import speech_trim
from ctypes import *
from contextlib import contextmanager
# ~ import textdistance
# ~ import matplotlib
# ~ from matplotlib import rc
# ~ matplotlib.rc('text', usetex = True)


# Handle pydub warnings
ERROR_HANDLER_FUNC = CFUNCTYPE(None, c_char_p, c_int, c_char_p, c_int, c_char_p)
def py_error_handler(filename, line, function, err, fmt):
  pass
c_error_handler = ERROR_HANDLER_FUNC(py_error_handler)
@contextmanager
def noalsaerr():
  asound = cdll.LoadLibrary('libasound.so')
  asound.snd_lib_error_set_handler(c_error_handler)
  yield
  asound.snd_lib_error_set_handler(None)


ap = argparse.ArgumentParser(
  description = '''he tool assists the user in verifying several preset 
  audio requirements, such as the compliance with the reference text, 
  correct audio format, initial and final non-speech segments and audio volume.''')
ap._action_groups.pop()
required = ap.add_argument_group('required arguments')
optional = ap.add_argument_group('optional arguments')
optional.add_argument("-w",
  type = str,
  metavar = "WAV_DIR",
  default = "",
  help = "Directory with WAV files.")
optional.add_argument("-x",
  type = str,
  metavar = "XLSX_FILE",
  default = "",
  help = "XLSX filepath.")
optional.add_argument("-s",
  type = int,
  metavar = "START_NUM",
  default = 1,
  help = '''Audio clip index at which the validation is started. Default:
    %(default)s (start with first audio clip).''')
optional.add_argument("-f",
  type = float,
  metavar = "SPEEDUP",
  default = 1,
  help = '''Audio playback speedup. Default:
    %(default)s (should be greater or equal to 1).''')


args = ap.parse_args()

SMALL_SIZE = 8
MEDIUM_SIZE = 9
BIGGER_SIZE = 10
plt.rc('font', size=SMALL_SIZE)
plt.rc('axes', titlesize=MEDIUM_SIZE)
plt.rc('axes', labelsize=SMALL_SIZE)
plt.rc('xtick', labelsize=SMALL_SIZE)
plt.rc('ytick', labelsize=SMALL_SIZE)
plt.rc('legend', fontsize=SMALL_SIZE)
plt.rc('figure', titlesize=BIGGER_SIZE)

master = tk.Tk()
master.title('Audio validation')

def speed_change(sound, speed=1.0):
  sound_with_altered_frame_rate = sound._spawn(sound.raw_data, overrides={
    "frame_rate": int(sound.frame_rate * speed)})
  return sound_with_altered_frame_rate.set_frame_rate(sound.frame_rate)

def play_wav(wf, speed=1.0):
  if os.name == 'nt':
    play(speed_change(AudioSegment.from_wav(wf), speed))
  else:
    with noalsaerr():
      play(speed_change(AudioSegment.from_wav(wf), speed))

def num_wrapper(text):
    """ Wraps num2words to allow mixed text-numeric types """
    return re.sub(r"(([0-9]+[,.]?)+([,.][0-9]+)?)", num_wrapper_inner, text)

def num_wrapper_inner(match):
    """ Inner wrapper feeds the string from the regex match to num2words """
    return num2words(match.group().replace(',','.'), lang='sl')

def verify_audio(wavdir, xlsx_file, start_num, mode, sim_thresh):
  wav_files = sorted(glob(os.path.join(wavdir, "*.wav")))
  r = sr.Recognizer()
  if xlsx_file is not None:
    xtext = pd.read_excel(xlsx_file, engine='openpyxl')
    if 'napaka' not in xtext:
      xtext['napaka'] = None
    if 'opis' not in xtext:
      xtext['opis'] = None
    if 'opomba' not in xtext:
      xtext['opomba'] = None

  wav_names = [os.path.splitext(os.path.basename(wf))[0] for wf in wav_files]
  xlsx_names = xtext['ID koda govorca:'].to_list()
  missing_wavs = np.setdiff1d(xlsx_names, wav_names)
  if missing_wavs.size:
    print('Missing files:')
    for mw in missing_wavs:
      if '***' not in mw:
        print(mw)
        xtext.loc[xtext.iloc[:,0] == mw, 'opomba'] = 'manjkajoč posnetek'

  tfm = sox.Transformer()
  now = datetime.datetime.now()
  rejfile = os.path.splitext(os.path.basename(xlsx_file))[0]+now.strftime("_%Y%m%d-%H%M%S")+os.path.splitext(xlsx_file)[-1]
  xwriter = pd.ExcelWriter(rejfile, engine='openpyxl')
  for c, wf in enumerate(wav_files[start_num-1:]):
    err = []
    reason = []
    cmnt = []
    fname = os.path.basename(wf)
    master.title('Validation of the file %s (%i/%i)'%(fname,c+start_num,len(wav_files)))
    sox_stats = tfm.stats(wf)
    sox_stats2 = sox.file_info.stat(wf)
    SNR_sox = float(sox_stats['RMS Pk dB']) - float(sox_stats['RMS Tr dB'])
    print("\n%s (%i/%i)"%(fname, c+start_num, len(wav_files)))
    all_stats = {**sox_stats, **sox_stats2}
    stats_label.config(text = '\n'.join("{}: {}".format(k, d) for k, d in all_stats.items()))

    print('Audio format check:')
    stats = sf.info(wf)
    if (stats.samplerate != 44100 or stats.channels != 1 or 
        stats.format != "WAV" or stats.subtype != "PCM_16"):
      print("    Wrong format.")
      reason.append("neustrezen format zapisa (vzorcenje: %d, kanali: %d,"
        "format: %s, podtip: %s)"
        %(stats.samplerate, stats.channels, stats.format, stats.subtype))
      err.append('f')
    else:
      print("    Correct format.")

    if xlsx_file is not None:
      fnm = os.path.splitext(fname)[0]
      target_txt = xtext[xtext.iloc[:,0] == fnm].iloc[:,1].values[0]
      target_txt = re.sub('\n', ' ', target_txt)
      target_txt_clean = re.sub(r'[^\w\s]','',target_txt).lower()
      target_txt_clean = re.sub('\n|\r|\t|-', ' ', target_txt_clean)
      target_txt_clean = target_txt_clean.rstrip()
      target_txt_clean = target_txt_clean.lstrip()
      man_switch = 0
      print("Compliance with the reference text:")
      print('    Reference text:  "%s"'%re.sub('\n|\r|\t|-', ' ', target_txt))
      if mode == 0:
        txt_label.delete('1.0', tk.END)
        txt_label.insert(tk.INSERT, "Reference text:\n%s"%target_txt)
        master.update()
      elif mode == 1 or mode == 2: #recognize speech in auto and semiauto mode
        try:
          with sr.AudioFile(wf) as audio_src:
            audio_data = r.record(audio_src)
            spoken_txt = r.recognize_google(audio_data, language="sl-SL")
            spoken_txt = re.sub('-', ' ', spoken_txt)
            spoken_txt = num_wrapper(spoken_txt)
            print('    Spoken text: "%s"'%spoken_txt)
            #txt_wer = textdistance.levenshtein.normalized_similarity(spoken_txt, target_txt_clean)
            txt_wer = wer(spoken_txt, target_txt_clean)
            if txt_wer > sim_thresh:
              if mode == 1:
                print('    Audio does not comply with reference text (WER = %.2f).'%txt_wer)
                reason.append('neskladje z besedilom (WER = %.2f)'%txt_wer)
                err.append('b')
            else:
              print('    Audio complies with reference text (WER = %.2f).'%txt_wer)
          txt_label.delete('1.0', tk.END)
          txt_label.insert(tk.INSERT, "Reference text:\n%s\n\nSpoken text:\n%s\n\nWER = %.3f"%(target_txt_clean, spoken_txt, txt_wer))

          seqm = dl.SequenceMatcher(None, target_txt_clean, spoken_txt)
          for opcode, a0, a1, b0, b1 in seqm.get_opcodes():
            if opcode == 'insert':
              txt_label.tag_add("ins", "2.%d"%a0, "2.%d"%a1)
              txt_label.tag_add("ins", "5.%d"%b0, "5.%d"%b1)
              txt_label.tag_config("ins", foreground="green")
            elif opcode == 'replace':
              txt_label.tag_add("rep", "2.%d"%a0, "2.%d"%a1)
              txt_label.tag_add("rep", "5.%d"%b0, "5.%d"%b1)
              txt_label.tag_config("rep", foreground="orange")
            elif opcode == 'delete':
              txt_label.tag_add("del", "2.%d"%a0, "2.%d"%a1)
              txt_label.tag_add("del", "5.%d"%b0, "5.%d"%b1)
              txt_label.tag_config("del", foreground="red")
          master.update()
        except:
          print('Text could not be automatically recognized. Switching to manual mode.')
          man_switch = 1
          txt_wer = np.inf
          txt_label.delete('1.0', tk.END)
          txt_label.insert(tk.INSERT, "Reference text:\n%s"%target_txt)
          master.update()
      if mode == 0 or (mode ==2 and (txt_wer > sim_thresh)) or man_switch:
        play_wav(wf, args.f)
        print("    Answer by pressing dedicated button or keyboard shortcut: Yes <space>, No <n>, Repeat <p>, Comment <o>.")
        qvar_txt = tk.IntVar()
        yes_txt = tk.Button(txt_frame, text = "Yes", command=lambda: qvar_txt.set(1))
        master.bind('<space>', lambda e: qvar_txt.set(1))
        no_txt = tk.Button(txt_frame, text = "No", command=lambda: qvar_txt.set(2))
        master.bind('n', lambda e: qvar_txt.set(2))
        repeat_txt = tk.Button(txt_frame, text = "Repeat", command=lambda: qvar_txt.set(3))
        master.bind('p', lambda e: qvar_txt.set(3))
        cmnt_txt = tk.Button(txt_frame, text="Comment", command=lambda: qvar_txt.set(4))
        master.bind('o', lambda e: qvar_txt.set(4))
        while True:
          yes_txt.grid(row=2, column=0)
          no_txt.grid(row = 2, column = 1)
          repeat_txt.grid(row = 2, column = 2)
          cmnt_txt.grid(row = 2, column = 3)
          master.update()
          yes_txt.wait_variable(qvar_txt)
          yes_txt.grid_forget()
          no_txt.grid_forget()
          repeat_txt.grid_forget()
          cmnt_txt.grid_forget()
          master.update()
          if qvar_txt.get() == 1: #Odg:Da
            print('    Audio is compliant with the reference text.')
            break
          elif qvar_txt.get() == 2: #Odg:Ne
            print('    Audio is not compliant with the reference text. Add optional comment explaining non-matching part')
            reason.append('neskladje z besedilom')
            err.append('b')
            descr = popup_description('neskladje z besedilom (ref.: "", izg.: "")')
            if descr:
              reason[-1] = descr
            break
          elif qvar_txt.get() == 3: #Odg: Ponovitev
            play_wav(wf)
            qvar_txt.set(0)
          elif qvar_txt.get() == 4: #Odg: Opomba
            cmnt.append(popup_description())
            qvar_txt.set(0)

    # Determine if initial and final pauses are appropriate
    data, rate = sf.read(wf)
    fail_string = []
    meter = pyln.Meter(rate)
    vol_mean = meter.integrated_loudness(data)
    (t_ini, t_fin) = speech_trim(['-i', wf])

    #Signal-to-noise ratio
    speechRMS = np.sqrt(np.mean(data[int(t_ini*rate):-int(t_fin*rate)]**2))
    noiseRMS = np.sqrt(np.mean(np.append(data[:int(t_ini*rate)],
      data[-int(t_fin*rate):])**2))
    SNR = 20*np.log10(speechRMS/noiseRMS)

    pcolr = 'k'
    PAUSE_TOL = 0.25 #allow PAUSE_TOL seconds tolerance for initial and final pause restriction
    if t_ini < .5-PAUSE_TOL or t_ini > 1+PAUSE_TOL:
      pcolr = 'r'
      fail_string.append("začetni premor: %.1f s"%t_ini)
    if t_fin < .5-PAUSE_TOL or t_fin > 1+PAUSE_TOL:
      pcolr = 'r'
      fail_string.append("končni premor: %.1f s"%t_fin)
    vcolr = 'k'
    SPEECH_VOLUME_THRESH = -27
    if vol_mean < SPEECH_VOLUME_THRESH:
      vcolr = 'r'
      fail_string.append("glasnost: %.1f dBFS"%vol_mean)

    print("Non-speech length and audio volume check:")
    if mode == 0 or (mode==2 and fail_string): #manual or failed semiautomatic
      SEGMENT_MS = 5
      speech = AudioSegment.from_file(wf)
      t_ini_v = int(t_ini*1000/SEGMENT_MS)
      t_fin_v = int(t_fin*1000/SEGMENT_MS)
      volume = [segment.dBFS for segment in speech[::SEGMENT_MS]]
      t_vol = np.arange(len(volume))*(SEGMENT_MS / 1000)

      print('    Initial silence length: %.2f s, final silence length: %.2f s'%(t_ini, t_fin))
      t_end = len(data)/rate
      ax1 = plt.subplot(311)
      plt.plot( np.linspace(0,t_ini,len(data[:int(t_ini*rate)])),
        data[:int(t_ini*rate)], 'r')
      plt.plot( np.linspace(t_ini,t_end-t_fin,
        len(data[int(t_ini*rate):int((t_end-t_fin)*rate)])),
        data[int(t_ini*rate):int((t_end-t_fin)*rate)], 'g')
      plt.plot( np.linspace(t_end-t_fin,t_end,
        len(data[int((t_end-t_fin)*rate):])),
        data[int((t_end-t_fin)*rate):], 'r')
      plt.axvspan(0, .5, facecolor='r', alpha=.3)
      plt.axvspan(t_end, t_end-.5, facecolor='r', alpha=.3)
      plt.axvspan(1, t_end-1, facecolor='g', alpha=.3)
      plt.axhline(y=.5, color='k', linestyle='--')
      plt.axhline(y=-.5, color='k', linestyle='--')
      plt.ylim([-1, 1])
      plt.xlim(0,t_end)
      plt.xlabel("Time[s]")
      plt.ylabel("Amplitude")
      ax1.set_title("Initial silence: %.2f s, final silence: %.2f s"%
        (t_ini, t_fin), color=pcolr)
      #plt.xlabel("$\mathrm{Time}[s]$")
      #plt.ylabel("$\mathrm{Amplitude}$")
      #fig.savefig("tmp.pdf", bbox_inches="tight",format="pdf")

      ax2 = plt.subplot(312)
      if data.ndim > 1:
        plt.specgram(data[:,0],Fs=rate)
      else:
        plt.specgram(data,Fs=rate)
      plt.xlim(0, t_end)
      plt.xlabel("Time [s]")
      plt.ylabel("Frequency [Hz]")
      ax2.set_title("Spectrogram")
      
      ax3 = plt.subplot(313)
      plt.plot(t_vol[:t_ini_v], volume[:t_ini_v],'r')
      plt.plot(t_vol[t_ini_v:-t_fin_v], volume[t_ini_v:-t_fin_v],'g')
      ax3.set_title("Max.: %.2f dBFS, mean: %.2f dBFS"%
      (speech.max_dBFS, vol_mean), color=vcolr)
      plt.plot(t_vol[-t_fin_v:], volume[-t_fin_v:],'r')
      plt.axhline(y=-6, color='k', linestyle='--')
      plt.axhline(y=-18, color='k', linestyle='--')
      plt.xlim(0, t_end)
      plt.xlabel("Time[s]")
      plt.ylabel("Volume[dBFS]")
      plt.tight_layout()
      fig.canvas.draw()

      if mode==2 and (txt_wer <= sim_thresh): #passed semiautomatic
        play_wav(wf, args.f)
      print("    Answer by pressing the dedicated button or key: Yes <space>, No <n>, Comment <o>.")
      qvar_time = tk.IntVar()
      yes_tm = tk.Button(timing_frame, text = "Yes", command=lambda: qvar_time.set(1))
      master.bind('<space>', lambda e: qvar_time.set(1))
      no_tm = tk.Button(timing_frame, text = "No", command=lambda: qvar_time.set(2))
      master.bind('n', lambda e: qvar_time.set(2))
      cmnt_tm = tk.Button(timing_frame, text="Comment", command=lambda: qvar_time.set(3))
      master.bind('o', lambda e: qvar_time.set(3))
      while True:
        yes_tm.grid(row=1, column=1)
        no_tm.grid(row = 1, column = 2)
        cmnt_tm.grid(row = 1, column = 3)
        master.update()
        yes_tm.wait_variable(qvar_time)
        yes_tm.grid_forget()
        no_tm.grid_forget()
        cmnt_tm.grid_forget()
        master.update()
        plt.clf()
        fig.canvas.draw()
        if qvar_time.get() == 1:
          print('    Non-speech sections and audio volume meet the requirements.')
          break
        elif qvar_time.get() == 2:
          if fail_string:
            reason.append("; ".join(fail_string))
          else:
            reason.append('premori in/ali glasnost niso ustrezni')
          err.append('p')
          print('    Non-speech sections and/or audio volume do not meet the requirements. Add optional comment.')
          descr = popup_description(( "; ".join(fail_string)).replace(".",","))
          if descr:
            reason[-1] = descr
          break
        elif qvar_time.get() == 3:
          cmnt.append(popup_description())
    else: #automatic or passed semiautomatic
      if fail_string:
        print('    Non-speech sections and/or audio volume do not meet the requirements..')
        fail_string.append("(SNR: %.1f, SNR_sox: %.1f)"%(SNR, SNR_sox))
        reason.append("; ".join(fail_string))
        err.append('p')
      else:
        print('    Non-speech sections and audio volume meet the requirements.')
    fig.clf()
    master.update()

    if reason:
      reject_area.insert(tk.INSERT, fname+'\n')
    else:
      accept_area.insert(tk.INSERT, fname+'\n')

    xtext.loc[xtext.iloc[:,0] == fnm, 'napaka'] = ", ".join(err)
    xtext.loc[xtext.iloc[:,0] == fnm, 'opis'] = "; ".join(reason)
    xtext.loc[xtext.iloc[:,0] == fnm, 'opomba'] = "; ".join(cmnt)

    xtext.to_excel(xwriter, index=False, sheet_name='povedi_za_snemanje')

    xwriter.sheets['povedi_za_snemanje'].column_dimensions['A'].width = 22
    xwriter.sheets['povedi_za_snemanje'].column_dimensions['B'].width = 90
    xwriter.sheets['povedi_za_snemanje'].column_dimensions['C'].width = 10
    xwriter.sheets['povedi_za_snemanje'].column_dimensions['D'].width = 60
    xwriter.sheets['povedi_za_snemanje'].column_dimensions['E'].width = 60
    for cell in xwriter.sheets['povedi_za_snemanje']['B']:
      cell.alignment = Alignment(wrap_text=True)
    xwriter.save()

def popup_warning():
  window = tk.Toplevel()
  window.title('Warning')
  label = tk.Label(window, text="First define the WAV directory, XSLX file and operating mode!")
  label.pack(fill='x', padx=50, pady=5)
  button_close = tk.Button(window, text="Close", command=window.destroy)
  button_close.pack(fill='x')
  
def popup_description(default_text=''):
  def disable_esc():
   pass
  window = tk.Toplevel()
  window.protocol("WM_DELETE_WINDOW", disable_esc)
  window.title('Add comment')
  desc_entry= tk.Entry(window, width= 130)
  desc_entry.insert(tk.END, default_text)
  desc_entry.pack()
  close_var = tk.IntVar()
  button_close = tk.Button(window, text="Close", command=lambda: close_var.set(1))
  button_close.pack(fill='x')
  print('    To close the pop-up window press "Close" button or <Enter> key.')
  window.bind('<Return>', lambda e: close_var.set(1))
  button_close.wait_variable(close_var)
  descr = desc_entry.get()
  window.destroy()
  return descr

def select_wav_dir():
  wdir = filedialog.askdirectory()
  wav_entry.delete(1, tk.END)
  wav_entry.insert(0, wdir)

def select_xlsx_file():
  xfile = tk.filedialog.askopenfilename()
  xlsx_entry.delete(1, tk.END)
  xlsx_entry.insert(0, xfile)

def on_exit():
    master.destroy()
    os._exit(1)

def set_operating_mode(*entry):
  if mode_var.get() == 'automatic' or mode_var.get() == 'semiautomatic':
    print('Vnesi prag WER med razpoznanim in '
    'zahtevanim besedilom, pod katerim smatramo, da se posnetek in ciljno '
    'besedilo ne skladata. (Vrednosti med 0 in 1. 0: sprejmemo le posnetke, pri katerih se '
    'razpoznano besedilo popolnoma sklada s ciljnim besedilom, 1: sprejmemo vse posnetke)')
    sim_label.grid_forget()
    sim_thresh.grid_forget()
    sim_label.grid()
    sim_thresh.grid()
    sim_thresh.delete(0, 'end')
    sim_thresh.insert(tk.END, 0.0)
  elif mode_var.get() == 'manual':
    sim_label.grid_forget()
    sim_thresh.grid_forget()
    sim_thresh.delete(0, 'end')
    sim_thresh.insert(tk.END, np.nan)

master.protocol('WM_DELETE_WINDOW', on_exit)

print('Enter input parameters.')
param_frame = tk.LabelFrame(master, text="(1) Input parameters")
param_frame.grid(row=0, column=0, padx=5, pady=5)

tk.Label(param_frame, text="WAV directory:").grid()
wav_entry = tk.Entry(param_frame, text="", width=40)
wav_entry.insert(tk.END, args.w)
wav_entry.grid()
wav_browse = tk.Button(param_frame, text="Browse", command=select_wav_dir)
wav_browse.grid()
  
tk.Label(param_frame, text="XLSX file:").grid()
xlsx_entry = tk.Entry(param_frame, text="", width=40)
xlsx_entry.insert(tk.END, args.x)
xlsx_entry.grid()
xlsx_browse = tk.Button(param_frame, text="Browse", command=select_xlsx_file)
xlsx_browse.grid()

tk.Label(param_frame, text="Starting index:").grid()
start_num = tk.Entry(param_frame, text="", width=4, justify='right')
start_num.grid()
start_num.insert(tk.END, args.s)

mode_label = tk.Label(param_frame, text="Operating mode:")
mode_label.grid()
mode_choices = ['manual', 'automatic', 'semiautomatic']
mode_var = tk.StringVar(master)
w = tk.OptionMenu(param_frame, mode_var, *mode_choices, command=set_operating_mode)
w.grid()
mode_map = {'manual':0, 'automatic':1, 'semiautomatic':2}

sim_label = tk.Label(param_frame, text="Rejection threshold (WER):")
sim_thresh = tk.Entry(param_frame, text="", width=4, justify='right')

start_var = tk.IntVar()
start_btn = tk.Button(master, text="Run", command=lambda: start_var.set(1))
start_btn.grid()

txt_frame = tk.LabelFrame(master, text="(2) Compliance with the reference text?")
txt_frame.grid(row=2, column=0,padx=5, pady=5)
txt_label = tk.Text(txt_frame, width=40, height=11, wrap="word")
txt_label.config(state=tk.NORMAL, font = ("Helvetica", 11))
txt_label.grid(columnspan=4)

timing_frame = tk.LabelFrame(master, text="(3) Non-speech segments lengths and speech volume?")
timing_frame.grid(row=0, column=1, rowspan=3, padx=5, pady=5)
fig = plt.figure()
fig.set_figwidth(4)
canvas = FigureCanvasTkAgg(fig, master=timing_frame)
canvas.get_tk_widget().grid(row=0,column=1,columnspan=3)

accept_frame = tk.LabelFrame(master, text="Accepted recordings")
accept_frame.grid(row=0, column=2, rowspan=1, padx=5, pady=5)
accept_area = st.ScrolledText(accept_frame, wrap = tk.WORD, 
              width = 30, height = 14, font = ("Helvetica", 10))
accept_area.grid()

reject_frame = tk.LabelFrame(master, text="Rejected recordings")
reject_frame.grid(row=1, column=2, rowspan=2, padx=5, pady=5)
reject_area = st.ScrolledText(reject_frame, wrap = tk.WORD, 
              width = 30, height = 14, font = ("Helvetica", 10))
reject_area.grid()

stats_frame = tk.LabelFrame(master, text="Statistical data")
stats_frame.grid(row=0, column=3, rowspan=3, padx=5, pady=5)
stats_label = tk.Label(stats_frame, text = "", wraplength=300, font=("Helvetica", 10))
stats_label.grid(rowspan=2)

while True:
  start_btn.wait_variable(start_var)
  param_frame.update()
  if start_var.get() == 1:
    wav_dir = wav_entry.get()
    xlsx_file = xlsx_entry.get()
    if not wav_dir or not xlsx_file or not mode_var.get():
      popup_warning()
      start_var.set(0)
    else:
      start_btn.grid_forget()
      wav_browse.grid_forget()
      xlsx_browse.grid_forget()
      w.config(state="disabled")
      verify_audio(wav_dir, xlsx_file, int(start_num.get()), mode_map[mode_var.get()], float(sim_thresh.get()))
      break
  master.update()
