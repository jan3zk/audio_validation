# -*- coding: utf-8 -*-
import sys
import os
import argparse
import sox
import pprint
import re
import speech_recognition as sr
from jiwer import wer
import textdistance
from num2words import num2words

def argparser():
  ap = argparse.ArgumentParser(
    description = "Fast validation of the input wav file.")
  ap._action_groups.pop()
  required = ap.add_argument_group("required arguments")
  optional = ap.add_argument_group("optional arguments")
  required.add_argument("-w",
    type = str,
    metavar = "WAV_FILE",
    default = "",
    help = "Directory with WAV files.")
  optional.add_argument("-t",
    type = str,
    metavar = "REF_TEXT",
    default = "",
    help = "Reference text.")
  optional.add_argument("--csv",
    action='store_true')
  args = ap.parse_args()
  return args


def num_wrapper(text):
    return re.sub(r"(([0-9]+[,.]?)+([,.][0-9]+)?)", num_wrapper_inner, text)

def num_wrapper_inner(match):
    return num2words(match.group().replace(',','.'), lang='sl')

def verify_audio(args):
  tfm = sox.Transformer()
  sox_stats = tfm.stats(args.w)
  sox_stats2 = sox.file_info.stat(args.w)
  all_stats = {**sox_stats, **sox_stats2}
  wav_name = os.path.splitext(os.path.basename(args.w))[0]
  if args.csv:
     csv_stats = ', '.join('{}'.format(v) for v in all_stats.values())
  else:
    print('Audio statistics:')
    pprint.pprint(all_stats)

  if args.t:
    r = sr.Recognizer()
    target_txt = re.sub(r'[^\w\s]','',args.t).lower()
    target_txt = re.sub('\n|\r|\t|-', ' ', target_txt)
    target_txt = target_txt.rstrip()
    target_txt = target_txt.lstrip()
    with sr.AudioFile(args.w) as audio_src:
      audio_data = r.record(audio_src)
      spoken_txt = r.recognize_google(audio_data, language="sl-SL")
      spoken_txt = re.sub('-', ' ', spoken_txt)
      spoken_txt = num_wrapper(spoken_txt)
      txt_lev = textdistance.levenshtein.normalized_similarity(spoken_txt, target_txt)
      txt_wer = wer(spoken_txt, target_txt)
      if args.csv:
        print('%s, %.2f, %.2f'%(csv_stats, txt_wer, txt_lev))
      else:
        print('\nMatching with the reference text:')
        print('Referenčno besedilo: "%s"'%re.sub('\n|\r|\t|-', ' ', target_txt))
        print('Razpoznano besedilo: "%s"'%spoken_txt)
        print('WER: %.2f, LS: %.2f'%(txt_wer,txt_lev))


if __name__ == '__main__':
  args = argparser()
  verify_audio(args)
