#!/usr/bin/env python3_32
"""HTTP API server exposing ``aitalk.py`` features via aiohttp."""

import argparse
import asyncio
import base64
import io
import os
import wave

from aiohttp import web

import aitalk


class AITalkApiService:
    """Stateful wrapper around aitalk module functions.

    The underlying DLL wrapper is process-global, so this service serializes all
    mutation/synthesis operations with a single lock.
    """

    def __init__(self):
        self._lock = asyncio.Lock()
        self._initialized = False

    async def init(self, auth_code):
        async with self._lock:
            aitalk.init(auth_code)
            self._initialized = True

    async def lang_load(self, language):
        async with self._lock:
            self._require_initialized()
            aitalk.lang_load(language)

    async def voice_load(self, voice):
        async with self._lock:
            self._require_initialized()
            aitalk.voice_load(voice)

    async def text_to_kana(self, text):
        async with self._lock:
            self._require_initialized()
            return await aitalk.text_to_kana(text)

    async def kana_to_speech(self, kana):
        async with self._lock:
            self._require_initialized()
            out = io.BytesIO()
            await aitalk.kana_to_speech(kana, out)
            return out.getvalue()

    async def synthesize_text_to_pcm(self, text):
        kana = await self.text_to_kana(text)
        return await self.kana_to_speech(kana)

    async def end(self):
        async with self._lock:
            if self._initialized:
                aitalk.end()
                self._initialized = False

    def _require_initialized(self):
        if not self._initialized:
            raise RuntimeError("engine is not initialized; call /init first")


@web.middleware
async def error_middleware(request, handler):
    try:
        return await handler(request)
    except web.HTTPException:
        raise
    except Exception as exc:  # noqa: BLE001
        return web.json_response({"error": str(exc)}, status=400)


def json_response_ok(**payload):
    return web.json_response({"ok": True, **payload})


async def _read_json(request):
    if request.content_type != "application/json":
        raise web.HTTPBadRequest(text="content-type must be application/json")
    return await request.json()


async def handle_health(request):
    service = request.app["service"]
    return json_response_ok(initialized=service._initialized)


async def handle_init(request):
    body = await _read_json(request)
    auth_code = body.get("auth_code") or os.environ.get("AITALK_AUTHCODE")
    if not auth_code:
        raise web.HTTPBadRequest(text="auth_code is required")
    await request.app["service"].init(auth_code)
    return json_response_ok()


async def handle_lang_load(request):
    body = await _read_json(request)
    language = body.get("language", "standard")
    await request.app["service"].lang_load(language)
    return json_response_ok(language=language)


async def handle_voice_load(request):
    body = await _read_json(request)
    voice = body.get("voice", "nozomi_22")
    await request.app["service"].voice_load(voice)
    return json_response_ok(voice=voice)


async def handle_text_to_kana(request):
    body = await _read_json(request)
    text = body.get("text")
    if text is None:
        raise web.HTTPBadRequest(text="text is required")
    kana = await request.app["service"].text_to_kana(text)
    return json_response_ok(kana=kana)


async def handle_kana_to_speech(request):
    body = await _read_json(request)
    kana = body.get("kana")
    if kana is None:
        raise web.HTTPBadRequest(text="kana is required")
    pcm = await request.app["service"].kana_to_speech(kana)

    output = body.get("output", "binary")
    if output == "base64":
        encoded = base64.b64encode(pcm).decode("ascii")
        return json_response_ok(
            audio_b64=encoded,
            sample_rate=aitalk.VOICE_SAMPLERATE,
            encoding="s16le",
            channels=1,
        )

    return web.Response(
        body=pcm,
        content_type="application/octet-stream",
        headers={
            "X-Sample-Rate": str(aitalk.VOICE_SAMPLERATE),
            "X-Audio-Encoding": "s16le",
            "X-Audio-Channels": "1",
        },
    )


async def handle_synthesize(request):
    body = await _read_json(request)
    text = body.get("text")
    if text is None:
        raise web.HTTPBadRequest(text="text is required")

    pcm = await request.app["service"].synthesize_text_to_pcm(text)
    output = body.get("output", "wav")

    if output == "pcm":
        return web.Response(body=pcm, content_type="application/octet-stream")
    if output == "base64":
        encoded = base64.b64encode(pcm).decode("ascii")
        return json_response_ok(
            audio_b64=encoded,
            sample_rate=aitalk.VOICE_SAMPLERATE,
            encoding="s16le",
            channels=1,
        )

    wav_bytes = io.BytesIO()
    with wave.open(wav_bytes, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(aitalk.VOICE_SAMPLERATE)
        wf.writeframes(pcm)
    return web.Response(body=wav_bytes.getvalue(), content_type="audio/wav")


async def handle_end(request):
    await request.app["service"].end()
    return json_response_ok()


async def cleanup_context(app):
    try:
        yield
    finally:
        await app["service"].end()


def create_app():
    app = web.Application(middlewares=[error_middleware])
    app["service"] = AITalkApiService()
    app.cleanup_ctx.append(cleanup_context)

    app.add_routes(
        [
            web.get("/health", handle_health),
            web.post("/init", handle_init),
            web.post("/lang/load", handle_lang_load),
            web.post("/voice/load", handle_voice_load),
            web.post("/text-to-kana", handle_text_to_kana),
            web.post("/kana-to-speech", handle_kana_to_speech),
            web.post("/synthesize", handle_synthesize),
            web.post("/end", handle_end),
        ]
    )
    return app


def parse_args(argv=None):
    parser = argparse.ArgumentParser(description="Expose pyaitalk via HTTP API.")
    parser.add_argument("--host", default="127.0.0.1", help="bind host")
    parser.add_argument("--port", default=8080, type=int, help="bind port")
    parser.add_argument(
        "--auto-init",
        action="store_true",
        help="call /init, /lang/load and /voice/load on startup",
    )
    parser.add_argument(
        "--auth-code",
        default=os.environ.get("AITALK_AUTHCODE"),
        help="auth code used with --auto-init",
    )
    parser.add_argument(
        "--language",
        default="standard",
        help="language used with --auto-init",
    )
    parser.add_argument(
        "--voice",
        default="nozomi_22",
        help="voice used with --auto-init",
    )
    return parser.parse_args(argv)


async def _try_auto_init(app, args):
    if not args.auto_init:
        return
    if not args.auth_code:
        raise ValueError("--auth-code (or AITALK_AUTHCODE) is required with --auto-init")

    service = app["service"]
    await service.init(args.auth_code)
    await service.lang_load(args.language)
    await service.voice_load(args.voice)


async def _start(args):
    app = create_app()
    await _try_auto_init(app, args)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host=args.host, port=args.port)
    await site.start()

    print(f"pyaitalk API server listening on http://{args.host}:{args.port}")
    stop_event = asyncio.Event()
    await stop_event.wait()


def main(argv=None):
    args = parse_args(argv)
    asyncio.run(_start(args))


if __name__ == "__main__":
    main()
