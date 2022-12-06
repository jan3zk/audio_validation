# -*- coding: utf-8 -*-
#print('Nalaganje programskih knjižnic ...')
from glob import glob
import os, sys
import argparse
import soundfile as sf
import librosa
import numpy as np
from pydub import AudioSegment,silence
import matplotlib.pyplot as plt
import scipy.signal as sps
from io import BytesIO
import contextlib
import wave
import webrtcvad
import collections
import random
import shutil
import uuid

def read_wave(path):
  """Reads a .wav file.
  Takes the path, and returns (PCM audio data, sample rate).
  """
  with contextlib.closing(wave.open(path, 'rb')) as wf:
    num_channels = wf.getnchannels()
    assert num_channels == 1
    sample_width = wf.getsampwidth()
    assert sample_width == 2
    sample_rate = wf.getframerate()
    assert sample_rate in (8000, 16000, 32000, 48000)
    pcm_data = wf.readframes(wf.getnframes())
    return pcm_data, sample_rate
    
def write_wave(path, audio, sample_rate):
  """Writes a .wav file.
  Takes path, PCM audio data, and sample rate.
  """
  with contextlib.closing(wave.open(path, 'wb')) as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(sample_rate)
    wf.writeframes(audio)
    
def np2pydub(np_data,rate):
  pydub_data = AudioSegment(
    np_data.tobytes(), 
    frame_rate = rate,
    sample_width = np_data.dtype.itemsize, 
    channels=1)
  return pydub_data

class Frame(object):
  """Represents a "frame" of audio data."""
  def __init__(self, bytes, timestamp, duration):
    self.bytes = bytes
    self.timestamp = timestamp
    self.duration = duration

def frame_generator(frame_duration_ms, audio, sample_rate):
  """Generates audio frames from PCM audio data.
  Takes the desired frame duration in milliseconds, the PCM data, and
  the sample rate.
  Yields Frames of the requested duration.
  """
  n = int(sample_rate * (frame_duration_ms / 1000.0) * 2)
  offset = 0
  timestamp = 0.0
  duration = (float(n) / sample_rate) / 2.0
  while offset + n < len(audio):
    yield Frame(audio[offset:offset + n], timestamp, duration)
    timestamp += duration
    offset += n

def initial_final_pauses(wav, aa, am, ad, at, ac):
  data, rate = sf.read(wav)
  t_end = len(data)/rate
  y, sr = librosa.load(wav, sr=32000)
  tmp_file = str(uuid.uuid4())+'.wav'
  sf.write(tmp_file, y, sr)
  audio, sample_rate = read_wave(tmp_file)
  os.remove(tmp_file) 
  vad = webrtcvad.Vad(int(aa))
  frames = frame_generator(30, audio, sample_rate)
  frames = list(frames)
  segments = vad_collector(sample_rate, 30, 300, vad, frames)
  for i, segment in enumerate(segments):
    vad_timings = np.array(segment[1]) - np.array(segment[0])
    if not all(segment):
      t_ini = 0.2
      t_fin = 0.2
    else:
      max_len = np.argmax(np.array(segment[1]) - np.array(segment[0]))
      t_ini = segment[0][np.argmax(np.array(segment[1]) - np.array(segment[0]))]
      t_fini = segment[1][np.argmax(np.array(segment[1]) - np.array(segment[0]))]
      for right_sec in range(max_len+1,len(segment[0])):
        if (segment[0][right_sec] - segment[1][right_sec-1]) < am and vad_timings[right_sec] > ad:
          t_fini = segment[1][right_sec]
      for left_sec in range(max_len,0,-1):
        if (segment[0][left_sec] - segment[1][left_sec-1]) < am and vad_timings[left_sec] > ad:
          t_ini = segment[0][left_sec-1]
      t_fin = t_end - t_fini
  # Find precise lenghts of initial and final silence
  speech = AudioSegment.from_file(wav)
  t_ini_v = silence.detect_leading_silence(speech[t_ini*1000:], silence_threshold=at, chunk_size=ac)
  t_ini = t_ini + t_ini_v/1000
  t_fin_v = silence.detect_leading_silence(speech.reverse()[t_fin*1000:], silence_threshold=at, chunk_size=ac)
  t_fin = t_fin + t_fin_v/1000
  return (t_ini, t_fin)

def vad_collector(sample_rate, frame_duration_ms,
                  padding_duration_ms, vad, frames):
  """Filters out non-voiced audio frames.
  Given a webrtcvad.Vad and a source of audio frames, yields only
  the voiced audio.
  Uses a padded, sliding window algorithm over the audio frames.
  When more than 90% of the frames in the window are voiced (as
  reported by the VAD), the collector triggers and begins yielding
  audio frames. Then the collector waits until 90% of the frames in
  the window are unvoiced to detrigger.
  The window is padded at the front and back to provide a small
  amount of silence or the beginnings/endings of speech around the
  voiced frames.
  Arguments:
  sample_rate - The audio sample rate, in Hz.
  frame_duration_ms - The frame duration in milliseconds.
  padding_duration_ms - The amount to pad the window, in milliseconds.
  vad - An instance of webrtcvad.Vad.
  frames - a source of audio frames (sequence or generator).
  Returns: A generator that yields PCM audio data.
  """
  num_padding_frames = int(padding_duration_ms / frame_duration_ms)
  # We use a deque for our sliding window/ring buffer.
  ring_buffer = collections.deque(maxlen=num_padding_frames)
  # We have two states: TRIGGERED and NOTTRIGGERED. We start in the
  # NOTTRIGGERED state.
  triggered = False
  t_inis = []
  t_fins = []
  for frame in frames:
    is_speech = vad.is_speech(frame.bytes, sample_rate)
    if not triggered:
      ring_buffer.append((frame, is_speech))
      num_voiced = len([f for f, speech in ring_buffer if speech])
      # If we're NOTTRIGGERED and more than 90% of the frames in
      # the ring buffer are voiced frames, then enter the
      # TRIGGERED state.
      if num_voiced > 0.9 * ring_buffer.maxlen:
        triggered = True
        t_inis.append(ring_buffer[0][0].timestamp)
        # We want to yield all the audio we see from now until
        # we are NOTTRIGGERED, but we have to start with the
        # audio that's already in the ring buffer.
        ring_buffer.clear()
    else:
      # We're in the TRIGGERED state, so collect the audio data
      # and add it to the ring buffer.
      ring_buffer.append((frame, is_speech))
      num_unvoiced = len([f for f, speech in ring_buffer if not speech])
      # If more than 90% of the frames in the ring buffer are
      # unvoiced, then enter NOTTRIGGERED and yield whatever
      # audio we've collected.
      if num_unvoiced > 0.9 * ring_buffer.maxlen:
        t_fins.append(frame.timestamp + frame.duration)
        triggered = False
        ring_buffer.clear()
  if triggered:
      t_fins.append(frame.timestamp + frame.duration)
  yield (t_inis, t_fins)

def speech_trim(raw_args=None):
  ap = argparse.ArgumentParser(description = 
  'Skripta za prirez začetnih in končnih premorov v govornih datotekah tipa WAW.')
  ap._action_groups.pop()
  required = ap.add_argument_group('required arguments')
  optional = ap.add_argument_group('optional arguments')
  required.add_argument('-i',
    type = str,
    help = 'Vhodna datoteka ali direktorij s posnetki WAV.')
  optional.add_argument('-o',
    type = str,
    help = 'Izhodna datoteka ali direktorij s posnetki WAV.')
  optional.add_argument('-v', 
    action='store_true',
    help = 'Argument s katerim vključimo izpis na konzolo.')
  optional.add_argument('-p', 
    type=float,
    default=0.75,
    help = 'Dolžina premora v sekundah.')
  optional.add_argument('-t', 
    type=int,
    default=-35,
    help = 'Prag tišine v dbFS.')
  optional.add_argument('-c', 
    type=int,
    default=75,
    help = 'Odsek procesiranja v ms.')
  optional.add_argument('-a', 
    type=int,
    default=2,
    help = 'Stopnja filtriranje negovornih odsekov (vrendnost med 0 in 3).')
  optional.add_argument('-m', 
    type=float,
    default=0.5,
    help = 'Največja dovoljena dolžina vmesnega premora znotraj govornega odseka.')
  optional.add_argument('-d', 
    type=float,
    default=1.0,
    help = 'Minimalna dolžina govornega signala.')
  optional.add_argument('-z',
    action='count',
    default=0,
    help = 'Zapolni prekratke premore s šumom ozadja.')
  optional.add_argument('-s', 
    type=int,
    default=1,
    help = 'Številka začetnega posneka.')

  args = ap.parse_args(raw_args)

  if os.path.isfile(args.i):
    in_wavs = [args.i]
  else:
    in_wavs = sorted(glob(os.path.join(args.i, '*.wav')))
  # ~ bgrnd_all = AudioSegment.empty()
  tini = []
  tfin = []

  if args.v:
    fig = plt.figure()

  for c,wav in enumerate(in_wavs[args.s-1:]):
    lead_add = 0
    trail_add = 0
    t_ini, t_fin = initial_final_pauses(wav, args.a, args.m, args.d, args.t, args.c)
    if args.v:
      print("\n(%i/%i)"%(c+args.s, len(in_wavs)))
      print('\nVhodni posnetek: %s'%wav)
      print('Ocenjen začetni premor: %.1f'%t_ini)
      print('Ocenjen končni premor: %.1f'%t_fin)
    data, rate = sf.read(wav)
    
    if args.z:
      bgrnd = AudioSegment.from_file(wav)

      bgrnd_ini = bgrnd[:int(t_ini*1000*0.5)]
      bgrnd_fin = bgrnd[-int(t_fin*1000*0.5):]
      if len(bgrnd_fin)>3:
        bgrnda = bgrnd_ini.append(bgrnd_fin, crossfade=min([len(bgrnd_ini)/3, len(bgrnd_fin)/3, 100]))
      else:
        bgrnda = bgrnd_ini
      bgrnd_all = AudioSegment.empty()

      trim_ms = 0
      while trim_ms < len(bgrnda):
        if bgrnda[trim_ms:trim_ms+10].dBFS < args.t*1.2:
          bgrnd_all = bgrnd_all + bgrnda[trim_ms:trim_ms+10]
        trim_ms += 10
      while len(bgrnd_all)/1000 < args.p:
        bgrnd_all = bgrnd_all.append(bgrnd_all, crossfade=min([len(bgrnd_all)*0.75, 100]))

      bgrnd_chunk = np.array(bgrnd_all.get_array_of_samples(), dtype=float)
      bgrnd_chunk = bgrnd_chunk/bgrnd_all.max_possible_amplitude
      t_end_chunk = len(bgrnd_chunk)/rate

      if t_ini < args.p:
        t_rand_ini = random.uniform(0,t_end_chunk-args.p+t_ini)
        if t_rand_ini < 0: t_rand_ini = 0
        bgrnd_chunk_ini = bgrnd_chunk[int(t_rand_ini*rate):int((t_rand_ini+args.p-t_ini)*rate)]
        data = np.concatenate((bgrnd_chunk_ini, data))
        lead_add = args.p-t_ini
        if args.v:
          print('Premajhen začetni premor. Dodanega %.2f s šuma na začetek posnetka.'%lead_add)

      if t_fin < args.p:
        t_rand_fin = random.uniform(0,t_end_chunk-args.p+t_fin)
        if t_rand_fin < 0: t_rand_fin = 0 
        bgrnd_chunk_fin = bgrnd_chunk[int(t_rand_fin*rate):int((t_rand_fin+args.p-t_fin)*rate)]
        data = np.concatenate((data, bgrnd_chunk_fin))
        trail_add = args.p-t_fin
        if args.v:
          print('Premajhen končni premor. Dodanega %.2f s šuma na konec posnetka.'%trail_add)

      # Recompute the precise final length on the extended signal
      tmp_mod = str(uuid.uuid4())+'.wav'
      sf.write(tmp_mod, data, rate)
      t_ini, t_fin = initial_final_pauses(tmp_mod, args.a, args.m, args.d, args.t, args.c)
      os.remove(tmp_mod)
    
    #t_ini = 1.0 #user defined initial pause
    #t_fin = 1.5 #user defined final pause
    lead_trim = t_ini-args.p if t_ini-args.p > 0 else 0
    trail_trim = t_fin-args.p if t_fin-args.p > 0 else 0
    if lead_trim < lead_add:
      lead_trim = 0
    else:
      lead_add = 0
    if trail_trim < trail_add:
      trail_trim = 0
    else:
      trail_add = 0
      
    t_end = len(data)/rate
    if args.v:
      print('Dolžina začetnega obreza: %.1f s'%lead_trim)
      print('Dolžina končnega obreza: %.1f s'%trail_trim)

    if args.o:
      if any(np.array([lead_add, trail_add, lead_trim, trail_trim])>0):
        if os.path.isdir(args.o):
          out_path = os.path.join(args.o,os.path.basename(wav))
        else:
          out_path = args.o
        if args.v:
          print('Prirezani posnetek shranjen v: %s'%out_path)
        sf.write(out_path, data[int(lead_trim*rate):int((t_end-trail_trim)*rate)], rate)
      else:
        shutil.copy2(wav, args.o)

    if args.v:
      # Plot signal and detected silence
      ax = plt.subplot(211)
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
      plt.axvspan(0, lead_trim, facecolor='k', alpha=.1, hatch='/')
      plt.axvspan(t_end-trail_trim, t_end, facecolor='k', alpha=.1, hatch='/')
      plt.axvspan(0, lead_add, facecolor='k', alpha=.1, hatch='.')
      plt.axvspan(t_end-trail_add, t_end, facecolor='k', alpha=.1, hatch='.')
      plt.axhline(y=.5, color='k', linestyle='--')
      plt.axhline(y=-.5, color='k', linestyle='--')
      plt.ylim([-1, 1])
      plt.xlim(0,t_end)
      plt.xlabel('Čas [s]')
      plt.ylabel('Amplituda')
      ax.set_title('sprememba na začetku: %.2f s, sprememba na koncu: %.2f s'%(max([-lead_trim, lead_add], key=abs), max([-trail_trim, trail_add], key=abs)))
      ax2 = plt.subplot(212)
      if data.ndim > 1:
        plt.specgram(data[:,0],Fs=rate)
      else:
        plt.specgram(data,Fs=rate)
      plt.xlim(0, t_end)
      plt.xlabel('Čas [s]')
      plt.ylabel('Frekvenca [Hz]')
      ax2.set_title('Spektrogram')
      plt.tight_layout()
      if args.o:
        if os.path.isdir(args.o):
          fig.savefig(os.path.join(args.o,os.path.basename(wav)[:-4]+'.jpg'), bbox_inches='tight',format='jpg')
        else:
          fig.savefig(os.path.join(os.path.basename(args.o)[:-4]+'.jpg'), bbox_inches='tight',format='jpg')
      #plt.show()
      fig.clf()

    tini.append(t_ini)
    tfin.append(t_fin)
  if len(tini) == 1:
    tini = tini[0]
    tfin = tfin[0]
  return (tini, tfin)

if __name__ == '__main__':

  speech_trim()
