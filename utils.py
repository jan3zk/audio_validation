# -*- coding: utf-8 -*-
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
  'Estimate initial/final silence lengths and crop the WAV file accordingly.')
  ap._action_groups.pop()
  required = ap.add_argument_group('required arguments')
  optional = ap.add_argument_group('optional arguments')
  required.add_argument('-i',
    type = str,
    help = 'Input WAV file or directory containing WAV files.')
  optional.add_argument('-o',
    type = str,
    help = 'Output WAV file or director where cropped WAV files will be stored.')
  optional.add_argument('-v', 
    action='store_true',
    help = 'Verbose flag.')
  optional.add_argument('-p', 
    type=float,
    default=0.8,
    help = 'Desired initial/final silence length in seconds.')
  optional.add_argument('-t', 
    type=int,
    default=-36,
    help = 'Silence threshold in dbFS.')
  optional.add_argument('-c', 
    type=int,
    default=75,
    help = 'Processing step in milliseconds.')
  optional.add_argument('-a', 
    type=int,
    default=3,
    help = 'Aggressiveness mode, which is an integer between 0 and 3. 0 is the least aggressive about filtering out non-speech, 3 is the most aggressive.')
  optional.add_argument('-m', 
    type=float,
    default=0.5,
    help = 'Longest intermediate silence length within the speech section (in seconds).')
  optional.add_argument('-d', 
    type=float,
    default=0.75,
    help = 'Minimum speech length (in seconds).')
  args = ap.parse_args(raw_args)
  
  if os.path.isfile(args.i):
    in_wavs = [args.i]
  else:
    in_wavs = glob(os.path.join(args.i, '*.wav'))
  tini = []
  tfin = []
  for wav in in_wavs:
    # Find approximate lenghts of initial and final silence
    y, sr = librosa.load(wav, sr=32000)
    sf.write('tmp.wav', y, sr)
    audio, sample_rate = read_wave('tmp.wav')
    os.remove('tmp.wav') 
    vad = webrtcvad.Vad(int(args.a))
    frames = frame_generator(30, audio, sample_rate)
    frames = list(frames)
    segments = vad_collector(sample_rate, 30, 300, vad, frames)
    for i, segment in enumerate(segments):
      vad_timings = np.array(segment[1]) - np.array(segment[0])# > args.d
      max_len = np.argmax(np.array(segment[1]) - np.array(segment[0]))
      t_ini = segment[0][np.argmax(np.array(segment[1]) - np.array(segment[0]))]
      t_fin = segment[1][np.argmax(np.array(segment[1]) - np.array(segment[0]))]
      for right_sec in range(max_len+1,len(segment[0])):
        if (segment[0][right_sec] - segment[1][right_sec-1]) < args.m and vad_timings[right_sec] > args.d:
          t_fin = segment[1][right_sec]
      for left_sec in range(max_len,0,-1):
        if (segment[0][left_sec] - segment[1][left_sec-1]) < args.m and vad_timings[left_sec] > args.d:
          t_ini = segment[0][left_sec-1]
    data, rate = sf.read(wav)
    t_end = len(data)/rate
    t_fin = t_end - t_fin
    # Find precise lenghts of initial and final silence
    speech = AudioSegment.from_file(wav)
    t_ini_v = silence.detect_leading_silence(speech[t_ini*1000:], silence_threshold=args.t, chunk_size=args.c)
    t_ini = t_ini + t_ini_v/1000
    t_fin_v = silence.detect_leading_silence(speech.reverse()[t_fin*1000:], silence_threshold=args.t, chunk_size=args.c)
    t_fin = t_fin + t_fin_v/1000
    leading_trim = t_ini-args.p if t_ini-args.p > 0 else 0
    trailing_trim = t_fin-args.p if t_fin-args.p > 0 else 0
    if args.o:
      if os.path.isfile(args.o):
        out_path = args.o
      else:
        out_path = os.path.join(args.o,os.path.basename(wav))
      print('Prirezani posnetek: %s'%out_path)
      sf.write(out_path, data[int((leading_trim)*rate):int((t_end-trailing_trim)*rate)], rate)
    # Plot signal and detected silence
    if args.v:
      print('\nInput file: %s'%wav)
      print('Estimated initial silence length: %.1f'%t_ini)
      print('Estimated final silence length: %.1f'%t_fin)
      print('Initial crop: %.1f s'%leading_trim)
      print('Final crop: %.1f s'%trailing_trim)
      if t_ini < 0.5: print('\tWARNING: Initial silence too short.')
      if t_fin < 0.5: print('\tWARNING: Final silence too short.')
      fig, ax = plt.subplots()
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
      plt.xlabel('Time [s]')
      plt.ylabel('Amplitude')
      ax.set_title('Initial silence: %.2f s, final silence: %.2f s'%(t_ini, t_fin))
      plt.show()
    tini.append(t_ini)
    tfin.append(t_fin)
  if len(tini) == 1:
    tini = tini[0]
    tfin = tfin[0]
  return (tini, tfin)
