#!/usr/bin/env python3
"""CLI utility: synthesize stdin text to speech via pyaitalk HTTP API."""

import argparse
import json
import locale
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
    parser.add_argument("output", nargs="?", help="Output WAV file path")
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
        "--character",
        default=None,
        help="Character (voice) name to use for this request.",
    )
    parser.add_argument(
        "--list-characters",
        action="store_true",
        help="List available characters (voices) from HTTP API and exit.",
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


def synthesize_wav(api_url, text, timeout, character=None):
    payload = {"text": text, "output": "wav"}
    if character:
        payload["character"] = character
    return post_json(api_url, "/synthesize", payload, timeout)



def fetch_characters(api_url, timeout):
    request = urllib.request.Request(
        url=f"{api_url.rstrip('/')}/voice/list",
        method="GET",
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:
        body = json.loads(response.read().decode("utf-8"))
    return body.get("voices", [])


def synthesize_wav_or_raise(api_url, text, timeout, character=None):
    try:
        return synthesize_wav(api_url, text, timeout, character=character)
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from API: {detail}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"failed to connect to API: {exc.reason}") from exc


def main(argv=None):
    args = parse_args(argv)

    if args.list_characters:
        try:
            voices = fetch_characters(args.api_url, args.timeout)
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"HTTP {exc.code} from API: {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(f"failed to connect to API: {exc.reason}") from exc

        for voice in voices:
            print(voice)
        return 0

    if not args.output:
        raise ValueError("output is required unless --list-characters is specified")

    raw_text = sys.stdin.buffer.read()
    text = decode_input_text(raw_text, args.input_encoding)

    wav_bytes = synthesize_wav_or_raise(
        args.api_url,
        text,
        args.timeout,
        character=args.character,
    )
    with open(args.output, "wb") as output_file:
        output_file.write(wav_bytes)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
