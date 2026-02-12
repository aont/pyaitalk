#!/usr/bin/env python3_32
"""CLI utility: synthesize stdin text to an MP3 file using aitalked.dll + lame."""

import argparse
import os
import subprocess
import sys

import aitalk

DEFAULT_LANGUAGE = "standard"
DEFAULT_VOICE = "nozomi_22"


class Lame:
    """Context manager for a running lame encoder process."""

    def __init__(self, outmp3fn):
        self.proc = subprocess.Popen(
            (
                "lame",
                "--silent",
                "-r",
                "-s",
                "22050",
                "--signed",
                "-m",
                "m",
                "-q",
                "0",
                "--vbr-old",
                "-V",
                "4",
                "-",
                outmp3fn,
            ),
            stdin=subprocess.PIPE,
            creationflags=subprocess.CREATE_NEW_PROCESS_GROUP,
        )

    def stdin(self):
        return self.proc.stdin

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        self.proc.stdin.close()
        ret = self.proc.wait()
        if ret != 0:
            raise Exception("lame exited with status code %s" % ret)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Read UTF-8 text from stdin and output speech MP3.",
    )
    parser.add_argument("output", help="Output MP3 file path")
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
        with Lame(args.output) as lame:
            aitalk.kana_to_speech(kana, lame.stdin())

    return 0


if __name__ == "__main__":
    sys.exit(main())
