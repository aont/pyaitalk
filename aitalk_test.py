#!/usr/bin/env python3_32

import os
import sys
import aitalk
import subprocess

def gen_lame(outmp3fn):
    return subprocess.Popen(("lame", "--silent", "-r", "-s", "22050", "--signed", "-m", "m", "-q", "0", "--vbr-old", "-V", "4", "-", outmp3fn), stdin=subprocess.PIPE)

def main():
    sys.stderr.write("[debug] pid=%s\n"%os.getpid())
    outmp3fn = "test.mp3"

    auth_code = os.environ["AITALK_AUTHCODE"]
    aitalk.init(auth_code)
    aitalk.lang_load("standard")
    aitalk.voice_load("nozomi_22")

    user_data = aitalk.UserData()

    text = "こんにちは。今日はいい天気ですね。"
    sys.stderr.write("text=%s\n" % text)

    sys.stderr.write("[debug] text_to_kana\n")
    kana = aitalk.text_to_kana(user_data, text)
    sys.stderr.write("kana=%s\n" % kana)

    sys.stderr.write("[debug] launch lame\n")
    
    lame = gen_lame(outmp3fn)
    user_data.speech_output = lame.stdin
    sys.stderr.write("[debug] kana_to_speech\n")
    aitalk.kana_to_speech(user_data, kana)
    lame.stdin.close()
    ret = lame.wait()
    if ret!=0:
        raise Exception("lame exited with status code %s"%ret)

    aitalk.end()

if __name__ == '__main__':
    sys.exit(main())