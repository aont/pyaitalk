#!/usr/bin/env python3_32

import os
import sys
import aitalk
import subprocess

class Lame:
    def __init__(self, outmp3fn):
        self.proc = subprocess.Popen(("lame", "--silent", "-r", "-s", "22050", "--signed", "-m", "m", "-q", "0", "--vbr-old", "-V", "4", "-", outmp3fn), stdin=subprocess.PIPE, creationflags=subprocess.CREATE_NEW_PROCESS_GROUP)
    def stdin(self):
        return self.proc.stdin
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.proc.stdin.close()
        ret = self.proc.wait()
        if ret!=0:
            raise Exception("lame exited with status code %s"%ret)

class DoOnExit:
    def __init__(self, func, argv=()):
        self.func = func
        self.argv = argv
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.func(*self.argv)

def summarize_text(text):
    size_half = 30
    text_omit = "\n   ...\n"
    if len(text)>(2*size_half+len(text_omit)):
        return text[:size_half] + text_omit + text[-size_half:]
    else:
        return text

def main():
    sys.stderr.write("[debug] pid=%s\n"%os.getpid())
    outmp3fn = "test.mp3"

    auth_code = os.environ["AITALK_AUTHCODE"]
    aitalk.init(auth_code)
    with DoOnExit(aitalk.end):
        aitalk.lang_load("standard")
        aitalk.voice_load("nozomi_22")

        text = "こんにちは。今日はいい天気ですね。"*100
        sys.stderr.write("[debug] text=\n%s\n" % summarize_text(text))

        sys.stderr.write("[debug] text_to_kana\n")
        kana = aitalk.text_to_kana(text)
        sys.stderr.write("[debug] kana=\n%s\n" % summarize_text(kana))

        sys.stderr.write("[debug] launch lame\n")
        with Lame(outmp3fn) as lame:
            sys.stderr.write("[debug] kana_to_speech\n")
            aitalk.kana_to_speech(kana, lame.stdin())
    
    sys.stderr.write("[debug] finished\n")

if __name__ == '__main__':
    sys.exit(main())