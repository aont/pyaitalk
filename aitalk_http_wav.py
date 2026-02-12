#!/usr/bin/env python3
"""CLI utility: synthesize stdin text to speech via pyaitalk HTTP API."""

import argparse
import json
import locale
import os
import sys
import urllib.error
import urllib.request

DEFAULT_API_URL = "http://127.0.0.1:8080"


def decode_input_text(raw_text, input_encoding=None):
    """Decode stdin bytes into text.

    If input_encoding is None, detect the encoding with BOM first and then try
    a set of common candidates.
    """

    if input_encoding:
        return raw_text.decode(input_encoding)

    if raw_text.startswith((b"\xff\xfe", b"\xfe\xff")):
        return raw_text.decode("utf-16")
    if raw_text.startswith((b"\xff\xfe\x00\x00", b"\x00\x00\xfe\xff")):
        return raw_text.decode("utf-32")
    if raw_text.startswith(b"\xef\xbb\xbf"):
        return raw_text.decode("utf-8-sig")

    locale_encoding = locale.getpreferredencoding(False)
    candidates = [
        "utf-8",
        locale_encoding,
        "cp932",
        "shift_jis",
        "euc_jp",
    ]

    tried = set()
    for encoding in candidates:
        if not encoding or encoding.lower() in tried:
            continue
        tried.add(encoding.lower())
        try:
            return raw_text.decode(encoding)
        except UnicodeDecodeError:
            continue

    raise UnicodeDecodeError(
        "unknown",
        raw_text,
        0,
        len(raw_text),
        "failed to auto-detect input encoding; specify --input-encoding",
    )


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Read text from stdin and request speech synthesis over HTTP API.",
    )
    parser.add_argument("output", help="Output WAV file path")
    parser.add_argument(
        "--api-url",
        default=DEFAULT_API_URL,
        help=f"API base URL (default: {DEFAULT_API_URL})",
    )
    parser.add_argument(
        "--input-encoding",
        default=None,
        help="Input text encoding. If omitted, encoding is auto-detected.",
    )
    parser.add_argument(
        "--timeout",
        default=60,
        type=float,
        help="HTTP request timeout in seconds (default: 60)",
    )
    parser.add_argument(
        "--auth-code",
        default=os.environ.get("AITALK_AUTHCODE"),
        help="Auth code used for lazy initialization when the API is not initialized.",
    )
    parser.add_argument(
        "--language",
        default="standard",
        help="Language profile used for lazy initialization (default: standard)",
    )
    parser.add_argument(
        "--voice",
        default="nozomi_22",
        help="Voice used for lazy initialization (default: nozomi_22)",
    )
    return parser.parse_args(argv)


def post_json(api_url, endpoint, payload, timeout):
    request = urllib.request.Request(
        url=f"{api_url.rstrip('/')}/{endpoint.lstrip('/')}",
        data=json.dumps(payload).encode("utf-8"),
        headers={"content-type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        return response.read()


def ensure_initialized(api_url, timeout, auth_code, language, voice):
    if not auth_code:
        raise RuntimeError(
            "API is not initialized; provide --auth-code or set AITALK_AUTHCODE "
            "for automatic initialization"
        )

    post_json(api_url, "/init", {"auth_code": auth_code}, timeout)
    post_json(api_url, "/lang/load", {"language": language}, timeout)
    post_json(api_url, "/voice/load", {"voice": voice}, timeout)


def synthesize_wav(api_url, text, timeout):
    return post_json(api_url, "/synthesize", {"text": text, "output": "wav"}, timeout)


def synthesize_wav_with_lazy_init(api_url, text, timeout, auth_code, language, voice):
    try:
        return synthesize_wav(api_url, text, timeout)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        if exc.code != 400 or "engine is not initialized" not in detail:
            raise RuntimeError(f"HTTP {exc.code} from API: {detail}") from exc

        try:
            ensure_initialized(api_url, timeout, auth_code, language, voice)
            return synthesize_wav(api_url, text, timeout)
        except urllib.error.HTTPError as init_exc:
            init_detail = init_exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {init_exc.code} from API: {init_detail}") from init_exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"failed to connect to API: {exc.reason}") from exc


def main(argv=None):
    args = parse_args(argv)

    raw_text = sys.stdin.buffer.read()
    text = decode_input_text(raw_text, args.input_encoding)

    wav_bytes = synthesize_wav_with_lazy_init(
        args.api_url,
        text,
        args.timeout,
        args.auth_code,
        args.language,
        args.voice,
    )
    with open(args.output, "wb") as output_file:
        output_file.write(wav_bytes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
