# Backend

Requires ffmpeg and ffprobe on the machine that runs it. A static host cannot run this.

```bash
python3 backend/studio.py init SONG --session sessions/one
python3 backend/produce.py measure sessions/one/A_original/SONG
python3 backend/studio.py apply --session sessions/one --plan plans/edit.json
```

`studio.py` locks A, refuses unknown plan keys, and writes a new take plus a receipt.

`produce.py` measures loudness and can render the fixed counterfactual set B, C, D, F, G.

Allowed plan keys: gain_db, highpass_hz, lowpass_hz, eq_hz, eq_gain_db, width, compress, trim_start, trim_end, fade_in, fade_out, plus name, hypothesis, predicted_proxy.

Harmonic delay is not possible on a stereo file. Do not fake it.
