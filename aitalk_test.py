#!/usr/bin/env python3_32

import os
import sys
import aitalk
import ctypes


def main():
    aitalk.init()
    aitalk.lang_load("standard")
    aitalk.voice_load("nozomi_22")
    aitalk.end()

if __name__ == '__main__':
    sys.exit(main())