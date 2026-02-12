#!/usr/bin/env python3_32
"""CLI utility: synthesize stdin text to a WAV file using aitalked.dll."""

import argparse
import os
import sys
import wave

import aitalk

DEFAULT_LANGUAGE = "standard"
DEFAULT_VOICE = "nozomi_22"


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
        description="Read UTF-8 text from stdin and output speech WAV.",
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
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    if not args.auth_code:
        raise ValueError("auth code is required (use --auth-code or AITALK_AUTHCODE)")

    text = sys.stdin.read()
    with aitalk.AITalkSession(args.auth_code, language=args.language, voice=args.voice) as session:
        kana = session.text_to_kana(text)
        with WavWriter(args.output) as wav_writer:
            aitalk.kana_to_speech(kana, wav_writer.stdin())

    return 0


if __name__ == "__main__":
    sys.exit(main())
