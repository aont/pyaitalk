#!/usr/bin/env python3_32

import os
import sys
import aitalk
import ctypes


def main():
    sys.stderr.write("[debug] pid=%s\n"%os.getpid())
    # aitalk.end()
    auth_code = os.environ["AITALK_AUTHCODE"]
    aitalk.init(auth_code)
    aitalk.lang_load("standard")
    aitalk.voice_load("nozomi_22")

    user_data = aitalk.gen_user_data()

    text = "こんにちは"
    # text = "abc"
    sys.stderr.write("text=%s\n" % text)

    kana = aitalk.text_to_kana(user_data, text)
    sys.stderr.write("kana=%s\n" % kana)

    speech = aitalk.kana_to_speech(user_data, kana)

    aitalk.end()

    with open("output.raw", "wb") as f:
        f.write(speech)


if __name__ == '__main__':
    sys.exit(main())