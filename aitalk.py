#!/usr/bin/env python3_32
"""`aitalked.dll` API wrapper.

This module provides low-level bindings around ``aitalked.dll`` and a small,
high-level interface for common use cases:

* initialize engine
* load language and voice
* convert text to kana
* convert kana to raw PCM audio
"""

import os
import sys
import ctypes
from ctypes import wintypes
import enum
import io
import asyncio

import subprocess

__all__ = [
    "AITalkSession",
    "end",
    "init",
    "kana_to_speech",
    "lang_load",
    "synthesize_text_to_stream",
    "text_to_kana",
    "voice_load",
]

from aitalk_config import resolve_aitalk_path

install_path = resolve_aitalk_path()
voice_db_dir = "Voice"
license_path = "aitalk.lic"

aitalked_dll = ctypes.WinDLL(os.path.join(install_path, "aitalked.dll"))
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

INFINITE = 0xFFFFFFFF


class WinHandle:
    def __init__(self, handle):
        self.handle = handle

    def close(self):
        if self.handle:
            kernel32.CloseHandle(self.handle)
            self.handle = None


kernel32.CloseHandle.restype = wintypes.BOOL
kernel32.CloseHandle.argtypes = (wintypes.HANDLE,)

kernel32.CreateEventW.restype = wintypes.HANDLE
kernel32.CreateEventW.argtypes = (
    wintypes.LPVOID,
    wintypes.BOOL,
    wintypes.BOOL,
    wintypes.LPCWSTR,
)

kernel32.GetStdHandle.restype = wintypes.HANDLE
kernel32.GetStdHandle.argtypes = (wintypes.DWORD,)

kernel32.SetEvent.restype = wintypes.BOOL
kernel32.SetEvent.argtypes = (wintypes.HANDLE,)


def create_event(manual_reset=True, initial_state=False, name=None):
    handle = kernel32.CreateEventW(None, manual_reset, initial_state, name)
    if not handle:
        raise ctypes.WinError(ctypes.get_last_error())
    return WinHandle(handle)


def set_event(event_handle):
    if not kernel32.SetEvent(event_handle.handle):
        raise ctypes.WinError(ctypes.get_last_error())


async def wait_complete(close_event_handle, timeout=INFINITE):
    """Wait for the conversion completion event using asyncio proactor APIs."""
    loop = asyncio.get_running_loop()
    proactor = getattr(loop, "_proactor", None)
    if proactor is None:
        raise RuntimeError("Current event loop does not support _proactor")

    timeout_seconds = None if timeout == INFINITE else timeout / 1000
    try:
        await proactor.wait_for_handle(int(close_event_handle.handle), timeout_seconds)
    except TimeoutError as exc:
        raise Exception("timeout") from exc

class Err(enum.IntEnum):
    SUCCESS = 0
    INTERNAL_ERROR = -1
    UNSUPPORTED = -2
    INVALID_ARGUMENT = -3
    WAIT_TIMEOUT = -4
    NOT_INITIALIZED = -10
    ALREADY_INITIALIZED = 10
    NOT_LOADED = -11
    ALREADY_LOADED = 11
    INSUFFICIENT = -20
    PARTIALLY_REGISTERED = 21
    LICENSE_ABSENT = -100
    LICENSE_EXPIRED = -101
    LICENSE_REJECTED = -102
    TOO_MANY_JOBS = -201
    INVALID_JOBID = -202
    JOB_BUSY = -203
    NOMORE_DATA = 204
    OUT_OF_MEMORY = -206
    FILE_NOT_FOUND = -1001
    PATH_NOT_FOUND = -1002
    READ_FAULT = -1003
    COUNT_LIMIT = -1004
    USERDIC_LOCKED = -1011
    USERDIC_NOENTRY = -1012

class EventReasonCode(enum.IntEnum):
    TEXTBUF_FULL = 101
    TEXTBUF_FLUSH = 102
    TEXTBUF_CLOSE = 103
    RAWBUF_FULL = 201
    RAWBUF_FLUSH = 202
    RAWBUF_CLOSE = 203
    PH_LABEL = 301
    BOOKMARK = 302
    AUTOBOOKMARK = 303

_close_kana = getattr(aitalked_dll, "_AITalkAPI_CloseKana@8")
_close_speech = getattr(aitalked_dll, "_AITalkAPI_CloseSpeech@8")
_end = getattr(aitalked_dll, "_AITalkAPI_End@0")
_get_data = getattr(aitalked_dll, "_AITalkAPI_GetData@16")
_get_jeita_control = getattr(aitalked_dll, "_AITalkAPI_GetJeitaControl@8")
_get_kana = getattr(aitalked_dll, "_AITalkAPI_GetKana@20")
_get_param = getattr(aitalked_dll, "_AITalkAPI_GetParam@8")
_get_status = getattr(aitalked_dll, "_AITalkAPI_GetStatus@8")
_init = getattr(aitalked_dll, "_AITalkAPI_Init@4")
_lang_clear = getattr(aitalked_dll, "_AITalkAPI_LangClear@0")
_lang_load = getattr(aitalked_dll, "_AITalkAPI_LangLoad@4")
_license_date = getattr(aitalked_dll, "_AITalkAPI_LicenseDate@4")
_license_info = getattr(aitalked_dll, "_AITalkAPI_LicenseInfo@16")
_module_flag = getattr(aitalked_dll, "_AITalkAPI_ModuleFlag@0")
_reload_phrase_dic = getattr(aitalked_dll, "_AITalkAPI_ReloadPhraseDic@4")
_reload_symbol_dic = getattr(aitalked_dll, "_AITalkAPI_ReloadSymbolDic@4")
_reload_word_dic = getattr(aitalked_dll, "_AITalkAPI_ReloadWordDic@4")
_set_param = getattr(aitalked_dll, "_AITalkAPI_SetParam@4")
_text_to_kana = getattr(aitalked_dll, "_AITalkAPI_TextToKana@12")
_text_to_speech = getattr(aitalked_dll, "_AITalkAPI_TextToSpeech@12")
_version_info = getattr(aitalked_dll, "_AITalkAPI_VersionInfo@16")
_voice_clear = getattr(aitalked_dll, "_AITalkAPI_VoiceClear@0")
_voice_load = getattr(aitalked_dll, "_AITalkAPI_VoiceLoad@4")



VOICE_SAMPLERATE = 22050
TIMEOUT = 10000
KANA_BUFFER_SIZE = 0x1000
SPEECH_BUFFER_SIZE = 0x10000

ENCODING = "cp932"

class Config(ctypes.Structure):
    _pack_ = 1
    _fields_ = (
        ("hz_voice_db", ctypes.c_uint32),
        ("dir_voice_dbs", ctypes.c_char_p),
        ("msec_timeout", ctypes.c_uint32),
        ("path_license", ctypes.c_char_p),
        ("code_auth_seed", ctypes.c_char_p),
        ("__reserved__", ctypes.c_uint32),
    )

MAX_VOICENAME = 80
MAX_JEITACONTROL = 12

ProcTextBuf = ctypes.WINFUNCTYPE(ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.py_object)
ProcRawBuf = ctypes.WINFUNCTYPE(ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_uint64, ctypes.py_object)
ProcEventTTS = ctypes.WINFUNCTYPE(ctypes.c_int32, ctypes.c_int32, ctypes.c_int32, ctypes.c_uint64, ctypes.c_char_p, ctypes.py_object)

class ExtendedFormat(enum.IntEnum):
    NONE = 0
    JEITA_RUBY = 1
    AUTO_BOOKMARK = 16


class JeitaParam(ctypes.Structure):
    _pack_ = 1
    _fields_ = (
        ("female_name", ctypes.ARRAY(ctypes.c_char, MAX_VOICENAME)),
        ("male_name", ctypes.ARRAY(ctypes.c_char, MAX_VOICENAME)),
        ("pause_middle", ctypes.c_int32),
        ("pause_long", ctypes.c_int32),
        ("pause_sentence", ctypes.c_int32),
        ("control", ctypes.ARRAY(ctypes.c_char, MAX_JEITACONTROL)),
    )

class SpeakerParam(ctypes.Structure):
    _pack_ = 1
    _fields_ = (
        ("voice_name", ctypes.ARRAY(ctypes.c_char, MAX_VOICENAME)),
        ("volume", ctypes.c_float),
        ("speed", ctypes.c_float),
        ("pitch", ctypes.c_float),
        ("range", ctypes.c_float),
        ("pause_middle", ctypes.c_int32),
        ("pause_long", ctypes.c_int32),
        ("pause_sentence", ctypes.c_int32),
        ("style_rate", ctypes.ARRAY(ctypes.c_char, MAX_VOICENAME)),
    )

def gen_TtsParam(num_speakers):
    class TtsParam(ctypes.Structure):
        _pack_ = 1
        _fields_ = (
            ("size", ctypes.c_uint32),
            ("proc_text_buf", ProcTextBuf),
            ("proc_raw_buf", ProcRawBuf),
            ("proc_event_tts", ProcEventTTS),
            ("len_text_buf_bytes", ctypes.c_uint32),
            ("len_raw_buf_bytes", ctypes.c_uint32),
            ("volume", ctypes.c_float),
            ("pause_begin", ctypes.c_int32),
            ("pause_term", ctypes.c_int32),
            ("extend_format", ctypes.c_int32),
            ("voice_name", ctypes.ARRAY(ctypes.c_char, MAX_VOICENAME)),
            ("jeita", JeitaParam),
            ("num_speakers", ctypes.c_uint32),
            ("__reserved__", ctypes.c_int32),
            ("speaker", ctypes.ARRAY(SpeakerParam, num_speakers)),
        )
    return TtsParam
TtsParam1 = gen_TtsParam(1)
TtsParam0 = gen_TtsParam(0)

def raise_for_result(code):
    """Raise ``Exception`` when a dll error code is returned."""
    if code!=Err.SUCCESS:
        for e in Err:
            if e.value == code:
                raise Exception("code: %s (%s)" % (code, e.name))
        else:
            raise Exception("code: %s" % (code, ))

def init(auth_code):
    """Initialize the engine.

    Args:
        auth_code: Authorization code (seed) for the runtime.
    """
    config = Config()
    config.hz_voice_db = VOICE_SAMPLERATE
    config.dir_voice_dbs = os.path.join(install_path, voice_db_dir).encode(ENCODING)
    config.msec_timeout = TIMEOUT
    config.path_license = os.path.join(install_path, license_path).encode(ENCODING)
    config.code_auth_seed = auth_code.encode(ENCODING)
    config.__reserved__ = 0
    raise_for_result(_init(ctypes.byref(config)))



def lang_load(language_name):
    """Load a language profile from ``<AITALK_PATH>/Lang``."""
    language_path = os.path.join(os.path.join(install_path, "Lang"), language_name)
    cwd_save = os.getcwd()
    
    os.chdir(install_path)
    result = _lang_load(language_path.encode(ENCODING))
    os.chdir(cwd_save)
    raise_for_result(result)



class JobIOMode(enum.IntEnum):
    PLAIN_TO_WAVE = 11
    AIKANA_TO_WAVE = 12
    JEITA_TO_WAVE = 13
    PLAIN_TO_AIKANA = 21
    AIKANA_TO_JEITA = 32

class JobParam(ctypes.Structure):
    _pack_ = 1
    _fields_ = (
        ("mode_io", ctypes.c_int32),
        ("user_data", ctypes.py_object),
    )


class ConversionData():
    def __init__(self, outfile, buffer_length):
        self.buffer = (ctypes.c_char*buffer_length)()
        self.close_event_handle = create_event(True, False, None)
        self.output = outfile
        
    def __enter__(self):
        return self
    def __exit__(self, exc_type, exc_value, traceback):
        self.close_event_handle.close()

def gen_text_to_kana_data(outfile):
    return ConversionData(outfile, KANA_BUFFER_SIZE)

async def text_to_kana(text, timeout=INFINITE):
    """Convert plain text to AIKANA text."""
    text_encoded = text.encode(ENCODING, errors='ignore')
    with io.BytesIO() as outfile, gen_text_to_kana_data(outfile) as user_data:
        job_param = JobParam()
        job_param.mode_io = JobIOMode.PLAIN_TO_AIKANA
        job_param.user_data = user_data
        job_id = ctypes.c_int32()
        raise_for_result(_text_to_kana(ctypes.byref(job_id), ctypes.byref(job_param), text_encoded))
        await wait_complete(user_data.close_event_handle, timeout)
        raise_for_result(_close_kana(job_id, 0))
        outfile.seek(0)
        return outfile.read().decode(ENCODING)

def gen_kana_to_speech_data(file):
    return ConversionData(file, SPEECH_BUFFER_SIZE*2)

async def kana_to_speech(kana, outfile, timeout=INFINITE):
    """Convert AIKANA text to little-endian 16-bit PCM and write to stream."""
    kana_encoded = kana.encode(ENCODING)
    with gen_kana_to_speech_data(outfile) as user_data:
        job_param = JobParam()
        job_param.mode_io = JobIOMode.AIKANA_TO_WAVE
        job_param.user_data = user_data
        job_id = ctypes.c_int32()
        raise_for_result(_text_to_speech(ctypes.byref(job_id), ctypes.byref(job_param), kana_encoded))
        await wait_complete(user_data.close_event_handle, timeout)
        raise_for_result(_close_speech(job_id, 0))

def callback_text_buf(reason_code, job_id, user_data):
    if reason_code in (EventReasonCode.TEXTBUF_FULL, EventReasonCode.TEXTBUF_FLUSH, EventReasonCode.TEXTBUF_CLOSE):
        buffer = user_data.buffer
        buffer_size = len(buffer)
        read_bytes = ctypes.c_uint32()
        while True:
            pos = ctypes.c_uint32()
            result = _get_kana(job_id, ctypes.byref(buffer), buffer_size, ctypes.byref(read_bytes), ctypes.byref(pos))
            if result != Err.SUCCESS:
                break
            user_data.output.write(buffer[:read_bytes.value])
            if (buffer_size-1) > read_bytes.value:
                break
        if reason_code != EventReasonCode.TEXTBUF_CLOSE:
            return 0
    set_event(user_data.close_event_handle)
    return 0
callback_text_buf_ptr = ProcTextBuf(callback_text_buf)

def callback_raw_buf(reason_code, job_id, tick, user_data):
    if reason_code in (EventReasonCode.RAWBUF_FULL, EventReasonCode.RAWBUF_FLUSH, EventReasonCode.RAWBUF_CLOSE):
        buffer = user_data.buffer
        buffer_size = len(buffer)//2
        read_samples = ctypes.c_uint32()
        while True:
            result = _get_data(job_id, buffer, buffer_size, ctypes.byref(read_samples))
            if result != Err.SUCCESS:
                break
            user_data.output.write(buffer[:read_samples.value*2])
            if buffer_size > read_samples.value:
                break
        if reason_code != EventReasonCode.RAWBUF_CLOSE:
            return 0
    set_event(user_data.close_event_handle)
    return 0
callback_raw_buf_ptr = ProcRawBuf(callback_raw_buf)

def callback_event_tts(reason_code, job_id, tick, name, user_data):
    return 0
callback_event_tts_ptr = ProcEventTTS(callback_event_tts)

def voice_load(voice_name):
    """Load a voice and attach conversion callbacks."""

    raise_for_result(_voice_load(voice_name.encode(ENCODING)))
    size = ctypes.c_uint32()
    result = _get_param(None, ctypes.byref(size))
    if result != Err.INSUFFICIENT:
        raise_for_result(result)
    if size.value < ctypes.sizeof(TtsParam1):
        raise Exception("sizeof(TtsParam1) (=%s) > size (=%s)" % (ctypes.sizeof(TtsParam1), size.value))
    num_speakers, mod = divmod((size.value-ctypes.sizeof(TtsParam0)), ctypes.sizeof(SpeakerParam))
    if mod != 0:
        raise Exception("size is invalid: %s (unable to decide num_speakers)" % (size.value, ))
    TtsParamN = gen_TtsParam(num_speakers)
    if ctypes.sizeof(TtsParamN) != size.value:
        raise Exception("sizeof(TtsParamN) (=%s) != size (=%s)" % (ctypes.sizeof(TtsParamN), size.value))
    param = TtsParamN()
    param.size = size.value
    raise_for_result(_get_param(ctypes.byref(param), ctypes.byref(size)))

    param.proc_text_buf = callback_text_buf_ptr
    param.proc_raw_buf = callback_raw_buf_ptr
    param.proc_event_tts = callback_event_tts_ptr

    param.extend_format = ExtendedFormat.JEITA_RUBY | ExtendedFormat.AUTO_BOOKMARK
    
    raise_for_result(_set_param(ctypes.pointer(param)))

def end():
    """Terminate the engine."""
    raise_for_result(_end())


class AITalkSession:
    """High-level async session object for repeated synthesis.

    Example:
        async with AITalkSession(auth_code, language="standard", voice="nozomi_22") as session:
            await session.synthesize("こんにちは", output_stream)
    """

    def __init__(self, auth_code, language="standard", voice="nozomi_22"):
        self.auth_code = auth_code
        self.language = language
        self.voice = voice

    async def __aenter__(self):
        init(self.auth_code)
        lang_load(self.language)
        voice_load(self.voice)
        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        end()

    async def text_to_kana(self, text):
        return await text_to_kana(text)

    async def synthesize(self, text, outfile):
        kana = await text_to_kana(text)
        await kana_to_speech(kana, outfile)


async def synthesize_text_to_stream(text, outfile, auth_code, language="standard", voice="nozomi_22"):
    """Convenience API: initialize -> synthesize -> finalize in one call."""
    async with AITalkSession(auth_code, language=language, voice=voice) as session:
        await session.synthesize(text, outfile)


# using Type_AITalkAPI_CloseKana = AITalkResultCode(__stdcall *)(int32_t, int32_t);
_close_kana.restype = ctypes.c_int32
_close_kana.argtypes = (ctypes.c_int32, ctypes.c_int32)

# using Type_AITalkAPI_CloseSpeech = AITalkResultCode(__stdcall *)(int32_t, int32_t);
_close_speech.restype = ctypes.c_int32
_close_speech.argtypes = (ctypes.c_int32, ctypes.c_int32)

# using Type_AITalkAPI_End = AITalkResultCode(__stdcall *)(void);
_end.restype = ctypes.c_int32
_end.argtypes = ()

# using Type_AITalkAPI_GetData = AITalkResultCode(__stdcall *)(int32_t, int16_t*, uint32_t, _uint32_t*);
_get_data.restype = ctypes.c_int32
# _get_data.argtypes = (ctypes.c_int32, ctypes.POINTER(ctypes.c_int16), ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32))
_get_data.argtypes = (ctypes.c_int32, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32))

# using Type_AITalkAPI_GetJeitaControl = AITalkResultCode(__stdcall *)(int32_t, const char*);
_get_jeita_control.restype = ctypes.c_int32
_get_jeita_control.argtypes = (ctypes.c_int32, ctypes.c_char_p)

# using Type_AITalkAPI_GetKana = AITalkResultCode(__stdcall *)(int32_t, char*, uint32_t, _uint32_t*, uint32_t*);
_get_kana.restype = ctypes.c_int32
_get_kana.argtypes = (ctypes.c_int32, ctypes.c_void_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32))

# using Type_AITalkAPI_GetParam = AITalkResultCode(__stdcall *)(AITalk_TTtsParam*, uint32_t*);
_get_param.restype = ctypes.c_int32
_get_param.argtypes = (ctypes.c_void_p, ctypes.POINTER(ctypes.c_uint32))

# using Type_AITalkAPI_GetStatus = AITalkResultCode(__stdcall *)(int32_t, AITalkStatusCode*);
_get_status.restype = ctypes.c_int32
_get_status.argtypes = (ctypes.c_int32, ctypes.POINTER(ctypes.c_int32))

# using Type_AITalkAPI_Init = AITalkResultCode(__stdcall *)(AITalk_TConfig*);
_init.restype = ctypes.c_int32
_init.argtypes = (ctypes.POINTER(Config), )

# using Type_AITalkAPI_LangClear = AITalkResultCode(__stdcall *)(void);
_lang_clear.restype = ctypes.c_int32
_lang_clear.argtypes = ()

# using Type_AITalkAPI_LangLoad = AITalkResultCode(__stdcall *)(const char*);
_lang_load.restype = ctypes.c_int32
_lang_load.argtypes = (ctypes.c_char_p, )

# using Type_AITalkAPI_LicenseDate = AITalkResultCode(__stdcall *)(char*);
_license_date.restype = ctypes.c_int32
_license_date.argtypes = (ctypes.c_char_p, )

# using Type_AITalkAPI_LicenseInfo = AITalkResultCode(__stdcall *)(const char*, char*, uint32_t, _uint32_t*);
_license_info.restype = ctypes.c_int32
_license_info.argtypes = (ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32))

# using Type_AITalkAPI_ModuleFlag = AITalkResultCode(__stdcall *)(void);
_module_flag.restype = ctypes.c_int32
_module_flag.argtypes = ()

# using Type_AITalkAPI_ReloadPhraseDic = AITalkResultCode(__stdcall *)(const char*);
_reload_phrase_dic.restype = ctypes.c_int32
_reload_phrase_dic.argtypes = (ctypes.c_char_p, )

# using Type_AITalkAPI_ReloadSymbolDic = AITalkResultCode(__stdcall *)(const char*);
_reload_symbol_dic.restype = ctypes.c_int32
_reload_symbol_dic.argtypes = (ctypes.c_char_p, )

# using Type_AITalkAPI_ReloadWordDic = AITalkResultCode(__stdcall *)(const char*);
_reload_word_dic.restype = ctypes.c_int32
_reload_word_dic.argtypes = (ctypes.c_char_p, )

# using Type_AITalkAPI_SetParam = AITalkResultCode(__stdcall *)(const AITalk_TTtsParam*);
_set_param.restype = ctypes.c_int32
_set_param.argtypes = (ctypes.c_void_p, )

# using Type_AITalkAPI_TextToKana = AITalkResultCode(__stdcall *)(int32_t*, AITalk_TJobParam*, _const char*);
_text_to_kana.restype = ctypes.c_int32
_text_to_kana.argtypes = (ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(JobParam), ctypes.c_char_p)

# using Type_AITalkAPI_TextToSpeech = AITalkResultCode(__stdcall *)(int32_t*, AITalk_TJobParam*, _const char*);
_text_to_speech.restype = ctypes.c_int32
_text_to_speech.argtypes = (ctypes.POINTER(ctypes.c_int32), ctypes.POINTER(JobParam), ctypes.c_char_p)

# using Type_AITalkAPI_VersionInfo = AITalkResultCode(__stdcall *)(int32_t, char*, uint32_t, _uint32_t*);
_version_info.restype = ctypes.c_int32
_version_info.argtypes = (ctypes.c_int32, ctypes.c_char_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32))

# using Type_AITalkAPI_VoiceClear = AITalkResultCode(__stdcall *)(void);
_voice_clear.restype = ctypes.c_int32
_voice_clear.argtypes = ()

# using Type_AITalkAPI_VoiceLoad = AITalkResultCode(__stdcall *)(const char*);
_voice_load.restype = ctypes.c_int32
_voice_load.argtypes = (ctypes.c_char_p, )
