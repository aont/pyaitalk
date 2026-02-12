# pyaitalk

Python bindings and CLI utilities for `aitalked.dll`.

## Repository layout

- `aitalk.py`: `ctypes` bindings for `aitalked.dll` plus a small high-level session API
- `aitalk_mp3.py`: CLI that converts stdin text into WAV output

## Requirements

- Windows
- A local installation that provides `aitalked.dll`

## Environment variables

- `AITALK_PATH`: installation directory that contains `aitalked.dll`
- `AITALK_AUTHCODE`: auth code (used when `--auth-code` is not provided)

## CLI usage

```bash
echo hello | python aitalk_mp3.py out.wav
```

Show all options:

```bash
python aitalk_mp3.py --help
```

Main options:

- `--voice`: voice name (default: `nozomi_22`)
- `--language`: language profile (default: `standard`)
- `--auth-code`: auth code

## Python API example

```python
import io
import os
import aitalk

text = "hello"
auth_code = os.environ["AITALK_AUTHCODE"]

with aitalk.AITalkSession(auth_code, language="standard", voice="nozomi_22") as session:
    kana = session.text_to_kana(text)
    raw = io.BytesIO()
    aitalk.kana_to_speech(kana, raw)
```
