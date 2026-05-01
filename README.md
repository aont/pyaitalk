# pyaitalk

Python bindings and CLI utilities for `aitalked.dll`.

## Repository layout

- `aitalk.py`: `ctypes` bindings for `aitalked.dll` plus a small high-level session API
- `aitalk_wav.py`: CLI that converts stdin text into WAV output
- `aitalk_api_server.py`: `aiohttp` based HTTP API server that exposes `aitalk.py` functions
- `aitalk_http_wav.py`: CLI that sends stdin text to the HTTP API and writes WAV output

## Requirements

- Windows
- A local installation that provides `aitalked.dll`

## Configuration (`config.toml`)

Create `config.toml`:

```toml
aitalk_path = "C:/path/to/aitalk"
aitalk_authcode = "YOUR_AUTH_CODE"
```

Deprecated (still supported): `AITALK_PATH`, `AITALK_AUTHCODE`.

## CLI usage

```bash
echo "こんにちは" | python aitalk_wav.py out.wav
```

Show all options:

```bash
python aitalk_wav.py --help
```

Main options:

- `--voice`: voice name (default: `nozomi_22`)
- `--language`: language profile (default: `standard`)
- `--config`: path to `config.toml`
- `--auth-code`: deprecated
- `--input-encoding`: stdin text encoding (default: auto-detect)


CLI for synthesis via HTTP API:

> `aitalk_http_wav.py` calls `/synthesize` and can query `/voice/list` to show available characters.


```bash
echo こんにちは | python aitalk_http_wav.py --character nozomi_22 out.wav
python aitalk_http_wav.py --list-characters
```

Main options:

- `--api-url`: API base URL (default: `http://127.0.0.1:8080`)
- `--character`: character/voice name to load before synthesis
- `--list-characters`: list available characters from the API and exit
- `--timeout`: HTTP timeout in seconds
- `--input-encoding`: stdin text encoding (default: auto-detect)

## HTTP API server (`aiohttp`)

Start server:

```bash
aitalk-api-server --host 0.0.0.0 --port 8080
```

Initialize engine on startup:

```bash
aitalk-api-server --config ./config.toml --language standard --voice nozomi_22
```

Endpoints:

- `GET /health`
- `POST /lang/load` `{ "language": "standard" }`
- `GET /voice/list`
- `POST /text-to-kana` `{ "text": "こんにちは" }`
- `POST /kana-to-speech` `{ "kana": "...", "output": "binary|base64" }`
- `POST /synthesize` `{ "text": "こんにちは", "character": "nozomi_22"(optional), "output": "wav|pcm|base64" }`


Character switching behavior:

- If `character` is omitted, synthesis uses the currently loaded voice.
- If `character` is provided and it differs from the currently loaded voice, the server terminates the AITalk engine and reinitializes it before loading that character.

Example:

```bash
curl -X POST http://127.0.0.1:8080/lang/load \
  -H 'content-type: application/json' \
  -d '{"language":"standard"}'


curl -X POST http://127.0.0.1:8080/synthesize \
  -H 'content-type: application/json' \
  -d '{"text":"こんにちは","character":"nozomi_22","output":"wav"}' > out.wav
```

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
