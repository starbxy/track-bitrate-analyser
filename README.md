# track-bitrate-analyser

Scans a folder of audio files and reports codec, bitrate, sample rate, channels and duration using `ffprobe`. Optionally generates a spectrogram per track with `ffmpeg` so you can spot fake or upscaled files (bright content stopping at ~16 kHz usually means a low-bitrate source).

All files in the `/tracks` directory are analysed.

## Setup

```bash
brew install ffmpeg
```

## Usage

```bash
python3 bitrate_analyser.py tracks            # table + analysis/bitrates.csv
python3 bitrate_analyser.py tracks -s         # also write spectrograms to analysis/spectrograms/
```

## Notes

- `stream` is the audio stream bitrate; `overall` includes artwork/tags so reads slightly high.
- FLAC/WAV may not report a stream bitrate, so check `overall` for those.
- Supported: mp3, flac, wav, m4a, aac, ogg, opus, aiff.
- Content up to about 20kHz means a genuine 320kbps or high-quality source. A cutoff around 19-20kHz is normal for a real 320 MP3, since the encoder’s own lowpass sits there.