#!/bin/bash

# Check if the input file and output file are provided
if [ -z "$1" ] || [ -z "$2" ]; then
  echo "Usage: $0 input.txt output.csv"
  exit 1
fi

input_list="$1"
output_csv="$2"

# Write CSV header
echo -e "Filename\tDuration[s]\tSample Rate[Hz]\tChannels\tSpeech Volume[dB]\tInitial Silence[s]\tFinal Silence[s]\tSNR[dB]" > "$output_csv"

# Print header to console
printf "Filename\tDuration[s]\tSample Rate[Hz]\tChannels\tSpeech Volume[dB]\tInitial Silence[s]\tFinal Silence[s]\tSNR[dB]\n"

while IFS= read -r input_file; do
  if [ -f "$input_file" ]; then
    # Get file information
    input_duration=$(soxi -D "$input_file")
    sample_rate=$(soxi -r "$input_file")
    num_channels=$(soxi -c "$input_file")

    # Create a temporary file without the initial silence
    sox "$input_file" without_init_silence.wav silence 1 0.1 1%

    # Calculate the duration of the file without initial silence
    without_init_silence_duration=$(soxi -D without_init_silence.wav)

    # Remove the final silence from the file without initial silence
    sox without_init_silence.wav without_init_and_final_silence.wav reverse silence 1 0.1 1% reverse

    # Calculate the duration of the file without initial and final silence
    without_init_and_final_silence_duration=$(soxi -D without_init_and_final_silence.wav)

    # Calculate and print the initial and final silence lengths
    initial_silence_length=$(echo "$input_duration - $without_init_silence_duration" | bc)
    final_silence_length=$(echo "$without_init_silence_duration - $without_init_and_final_silence_duration" | bc)

    # Calculate the RMS power of the signal and noise
    signal_rms=$(sox without_init_and_final_silence.wav -n stats -s 16 2>&1 | awk '/^RMS lev dB/ {print $4}')
    noise_rms=$(sox -V1 "$input_file" init_and_final_silence.wav trim 0 "$initial_silence_length" reverse trim 0 "$final_silence_length" && sox init_and_final_silence.wav -n stats -s 16 2>&1 | awk '/^RMS lev dB/ {print $4}')

    # Calculate the SNR in dB
    snr=$(echo "$signal_rms - $noise_rms" | bc)

    # Append data to CSV
    echo -e "$input_file\t$input_duration\t$sample_rate\t$num_channels\t$signal_rms\t$initial_silence_length\t$final_silence_length\t$snr" >> "$output_csv"

    # Print data to console
    printf "%s\t%s\t%s\t%s\t%s\t%s\t%s\t%s\n" "$input_file" "$input_duration" "$sample_rate" "$num_channels" "$signal_rms" "$initial_silence_length" "$final_silence_length" "$snr"

  fi

  # Clean up temporary files
  rm without_init_silence.wav
  rm without_init_and_final_silence.wav
  rm init_and_final_silence.wav

done < "$input_list"
