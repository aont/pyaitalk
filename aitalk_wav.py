#!/usr/bin/env python3_32
"""CLI utility: synthesize stdin text to a WAV file using aitalked.dll."""

import argparse
import locale
import os
import sys
import wave

import aitalk

DEFAULT_LANGUAGE = "standard"
DEFAULT_VOICE = "nozomi_22"


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


class WavWriter:
    """Context manager for writing AI Talk raw PCM into a WAV file."""

    def __init__(self, outwavfn):
        self.wave_file = wave.open(outwavfn, "wb")
        self.wave_file.setnchannels(1)
        self.wave_file.setsampwidth(2)
        self.wave_file.setframerate(aitalk.VOICE_SAMPLERATE)

    def stdin(self):
        return self

    def write(self, data):
        self.wave_file.writeframesraw(data)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.wave_file.close()


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Read text from stdin and output speech WAV.",
    )
    parser.add_argument("output", help="Output WAV file path")
    parser.add_argument(
        "--language",
        default=DEFAULT_LANGUAGE,
        help=f"Language profile to load (default: {DEFAULT_LANGUAGE})",
    )
    parser.add_argument(
        "--voice",
        default=DEFAULT_VOICE,
        help=f"Voice name to load (default: {DEFAULT_VOICE})",
    )
    parser.add_argument(
        "--auth-code",
        default=os.environ.get("AITALK_AUTHCODE"),
        help="Auth code. Defaults to AITALK_AUTHCODE environment variable.",
    )
    parser.add_argument(
        "--input-encoding",
        default=None,
        help="Input text encoding. If omitted, encoding is auto-detected.",
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if not args.auth_code:
        raise ValueError("auth code is required (use --auth-code or AITALK_AUTHCODE)")

    raw_text = sys.stdin.buffer.read()
    text = decode_input_text(raw_text, args.input_encoding)
    with aitalk.AITalkSession(args.auth_code, language=args.language, voice=args.voice) as session:
        kana = session.text_to_kana(text)
        with WavWriter(args.output) as wav_writer:
            aitalk.kana_to_speech(kana, wav_writer.stdin())

    return 0


if __name__ == "__main__":
    sys.exit(main())
