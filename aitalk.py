#!/usr/bin/env python3_32

import os
# import sys
import ctypes
import enum

install_path = os.getenv("AITALK_PATH")
voice_db_dir = "Voice"
license_path = "aitalk.lic"
auth_code = os.getenv("AITALK_AUTHCODE")

aitalked_dll = ctypes.WinDLL(os.path.join(install_path, "aitalked.dll"))

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

PATH_ENCODING = "cp932"

class Config(ctypes.Structure):
    _fields_ = (
        ("hzVoiceDB", ctypes.c_uint32),
        ("dirVoiceDBS", ctypes.c_char_p),
        ("msecTimeout", ctypes.c_uint32),
        ("pathLicense", ctypes.c_char_p),
        ("codeAuthSeed", ctypes.c_char_p),
        ("__reserved__", ctypes.c_uint32),
    )

MAX_VOICENAME = 80
MAX_JEITACONTROL = 12

# using AITalkProcTextBuf = int(__stdcall *)(AITalkEventReasonCode reasonCode, int32_t jobID, void *userData);
# using AITalkProcRawBuf = int (__stdcall *)(AITalkEventReasonCode reasonCode, int32_t jobID, uint64_t tick, void *userData);
# using AITalkProcEventTTS = int(__stdcall *)(AITalkEventReasonCode reasonCode, int32_t jobID, uint64_t tick, const char *name, void *userData);
ProcTextBuf = ctypes.c_void_p
ProcRawBuf = ctypes.c_void_p
ProcEventTTS = ctypes.c_void_p

class ExtendedFormat(enum.IntEnum):
    NONE = 0
    JEITA_RUBY = 1
    AUTO_BOOKMARK = 16


class JeitaParam(ctypes.Structure):
    _pack_ = 1
    _fields_ = (
        ("femaleName", ctypes.ARRAY(ctypes.c_char, MAX_VOICENAME)),
        ("maleName", ctypes.ARRAY(ctypes.c_char, MAX_VOICENAME)),
        ("pauseMiddle", ctypes.c_int32),
        ("pauseLong", ctypes.c_int32),
        ("pauseSentence", ctypes.c_int32),
        ("control", ctypes.ARRAY(ctypes.c_char, MAX_JEITACONTROL)),
    )

class SpeakerParam(ctypes.Structure):
    _pack_ = 1
    _fields_ = (
        ("voiceName", ctypes.ARRAY(ctypes.c_char, MAX_VOICENAME)),
        ("volume", ctypes.c_float),
        ("speed", ctypes.c_float),
        ("pitch", ctypes.c_float),
        ("range", ctypes.c_float),
        ("pauseMiddle", ctypes.c_int32),
        ("pauseLong", ctypes.c_int32),
        ("pauseSentence", ctypes.c_int32),
        ("styleRate", ctypes.ARRAY(ctypes.c_char, MAX_VOICENAME)),
    )

def gen_TtsParam(num_speakers):
    class TtsParam(ctypes.Structure):
        _pack_ = 1
        _fields_ = (
            ("size", ctypes.c_uint32),
            ("procTextBuf", ProcTextBuf),
            ("procRawBuf", ProcRawBuf),
            ("procEventTts", ProcEventTTS),
            ("lenTextBufBytes", ctypes.c_uint32),
            ("lenRawBufBytes", ctypes.c_uint32),
            ("volume", ctypes.c_float),
            ("pauseBegin", ctypes.c_int32),
            ("pauseTerm", ctypes.c_int32),
            ("extendFormat", ctypes.c_int32),
            ("voiceName", ctypes.ARRAY(ctypes.c_char, MAX_VOICENAME)),
            ("Jeita", JeitaParam),
            ("numSpeakers", ctypes.c_uint32),
            ("__reserved__", ctypes.c_int32),
            ("Speaker", SpeakerParam*num_speakers),
        )
    return TtsParam
TtsParam1 = gen_TtsParam(1)

def raise_for_result(code):
    if code!=Err.SUCCESS:
        for e in Err:
            if e.value == code:
                raise Exception("code: %s (%s)" % (code, e.name))
        else:
            raise Exception("code: %s" % (code, ))

def init():
    config = Config()
    config.hzVoiceDB = VOICE_SAMPLERATE
    config.dirVoiceDBS = os.path.join(install_path, voice_db_dir).encode(PATH_ENCODING)
    config.msecTimeout = TIMEOUT
    config.pathLicense = os.path.join(install_path, license_path).encode(PATH_ENCODING)
    config.codeAuthSeed = auth_code.encode()
    raise_for_result(_init(config))

def lang_load(language_name):
    language_path = os.path.join(os.path.join(install_path, "Lang"), language_name)
    cwd_save = os.getcwd()
    os.chdir(install_path)
    result = _lang_load(language_path.encode(PATH_ENCODING))
    os.chdir(cwd_save)
    raise_for_result(result)

def voice_load(voice_name):
    raise_for_result(_voice_load(voice_name.encode()))
    size = ctypes.c_uint32()
    result = _get_param(None, ctypes.byref(size))
    if result != Err.INSUFFICIENT or size.value < ctypes.sizeof(TtsParam1):
        raise Exception("sizeof(TtsParam1) (=%s) > size (=%s)" % (ctypes.sizeof(TtsParam1), size.value))
    num_speakers = int((size.value-ctypes.sizeof(gen_TtsParam(0)))/ctypes.sizeof(SpeakerParam))
    TtsParamN = gen_TtsParam(num_speakers)
    if ctypes.sizeof(TtsParamN) != size.value:
        raise Exception("sizeof(TtsParamN) (=%s) != size (=%s)" % (ctypes.sizeof(TtsParamN), size.value))
    param = TtsParamN()
    param.size = size.value
    result = _get_param(ctypes.byref(param), ctypes.byref(size))
    raise_for_result(result)

    # param->procTextBuf = callbackTextBuf;
    # param->procRawBuf = callbackRawBuf;
    # param->procEventTts = callbackEventTts;
    param.extendFormat = ExtendedFormat.JEITA_RUBY | ExtendedFormat.AUTO_BOOKMARK
    result = _set_param(ctypes.byref(param))
    raise_for_result(result)
    # todo: setparam callback 



def end():
    raise_for_result(_end())



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
_get_data.argtypes = (ctypes.c_int32, ctypes.POINTER(ctypes.c_int16), ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32))

# using Type_AITalkAPI_GetJeitaControl = AITalkResultCode(__stdcall *)(int32_t, const char*);
_get_jeita_control.restype = ctypes.c_int32
_get_jeita_control.argtypes = (ctypes.c_int32, ctypes.c_char_p)

# using Type_AITalkAPI_GetKana = AITalkResultCode(__stdcall *)(int32_t, char*, uint32_t, _uint32_t*, uint32_t*);
_get_kana.restype = ctypes.c_int32
_get_kana.argtypes = (ctypes.c_int32, ctypes.c_char_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32), ctypes.POINTER(ctypes.c_uint32))

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
_text_to_kana.argtypes = (ctypes.POINTER(ctypes.c_int32), ctypes.c_void_p, ctypes.c_char_p)

# using Type_AITalkAPI_TextToSpeech = AITalkResultCode(__stdcall *)(int32_t*, AITalk_TJobParam*, _const char*);
_text_to_speech.restype = ctypes.c_int32
_text_to_speech.argtypes = (ctypes.POINTER(ctypes.c_int32), ctypes.c_void_p, ctypes.c_char_p)

# using Type_AITalkAPI_VersionInfo = AITalkResultCode(__stdcall *)(int32_t, char*, uint32_t, _uint32_t*);
_version_info.restype = ctypes.c_int32
_version_info.argtypes = (ctypes.c_int32, ctypes.c_char_p, ctypes.c_uint32, ctypes.POINTER(ctypes.c_uint32))

# using Type_AITalkAPI_VoiceClear = AITalkResultCode(__stdcall *)(void);
_voice_clear.restype = ctypes.c_int32
_voice_clear.argtypes = ()

# using Type_AITalkAPI_VoiceLoad = AITalkResultCode(__stdcall *)(const char*);
_voice_load.restype = ctypes.c_int32
_voice_load.argtypes = (ctypes.c_char_p, )




