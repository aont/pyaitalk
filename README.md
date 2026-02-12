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

## Environment variables

- `AITALK_PATH`: installation directory that contains `aitalked.dll`
- `AITALK_AUTHCODE`: auth code (used when `--auth-code` is not provided)

## CLI usage

```bash
echo hello | python aitalk_wav.py out.wav
```

Show all options:

```bash
python aitalk_wav.py --help
```

Main options:

- `--voice`: voice name (default: `nozomi_22`)
- `--language`: language profile (default: `standard`)
- `--auth-code`: auth code
- `--input-encoding`: stdin text encoding (default: auto-detect)


HTTP API 経由で合成するCLI:

> `aitalk_http_wav.py` はサーバー側で初期化済みであることを前提に `/synthesize` を呼び出します。


```bash
echo こんにちは | python aitalk_http_wav.py out.wav
```

主なオプション:

- `--api-url`: API ベースURL (default: `http://127.0.0.1:8080`)
- `--timeout`: HTTPタイムアウト秒数
- `--input-encoding`: stdin テキストエンコーディング (default: auto-detect)

## HTTP API server (`aiohttp`)

Start server:

```bash
aitalk-api-server --host 0.0.0.0 --port 8080
```

Initialize engine on startup:

```bash
aitalk-api-server --auth-code "$AITALK_AUTHCODE" --language standard --voice nozomi_22
```

Endpoints:

- `GET /health`
- `POST /lang/load` `{ "language": "standard" }`
- `POST /voice/load` `{ "voice": "nozomi_22" }`
- `POST /text-to-kana` `{ "text": "こんにちは" }`
- `POST /kana-to-speech` `{ "kana": "...", "output": "binary|base64" }`
- `POST /synthesize` `{ "text": "こんにちは", "output": "wav|pcm|base64" }`

Example:

```bash
curl -X POST http://127.0.0.1:8080/lang/load \
  -H 'content-type: application/json' \
  -d '{"language":"standard"}'

curl -X POST http://127.0.0.1:8080/voice/load \
  -H 'content-type: application/json' \
  -d '{"voice":"nozomi_22"}'

curl -X POST http://127.0.0.1:8080/synthesize \
  -H 'content-type: application/json' \
  -d '{"text":"こんにちは","output":"wav"}' > out.wav
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
