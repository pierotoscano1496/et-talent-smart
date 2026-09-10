import io
import math
import os
import sys
import wave
from array import array
from functools import lru_cache

import groq
from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse, Response
from groq import Groq


load_dotenv()


ASSISTANT_INSTRUCTIONS = """
Eres un asistente virtual integrado en un ESP32-C6.
Responde siempre en espanol.
Las respuestas deben ser breves, naturales y faciles de escuchar.
Responde en maximo 180 caracteres.
"""

DEFAULT_STT_MODEL = "whisper-large-v3-turbo"
DEFAULT_CHAT_MODEL = "openai/gpt-oss-120b"
DEFAULT_TTS_MODEL = "canopylabs/orpheus-v1-english"
DEFAULT_TTS_VOICE = "troy"
DEFAULT_CHAT_MAX_COMPLETION_TOKENS = "96"
DEFAULT_TTS_MAX_CHARS = "190"
DEFAULT_STT_MIN_RMS = "80"
DEFAULT_STT_MAX_NO_SPEECH_PROBABILITY = "0.6"


@lru_cache
def get_groq_client():
    if not os.getenv("GROQ_API_KEY"):
        raise RuntimeError(
            "No se encontro GROQ_API_KEY en .env"
        )

    return Groq(
        max_retries=get_int_config("GROQ_MAX_RETRIES", "4"),
        timeout=get_float_config("GROQ_TIMEOUT_SECONDS", "60")
    )


def get_config(name, default):
    return os.getenv(name, default)


def get_int_config(name, default):
    return int(get_config(name, default))


def get_float_config(name, default):
    return float(get_config(name, default))


def get_groq_error_message(exc):
    body = getattr(exc, "body", None)

    if isinstance(body, dict):
        error = body.get("error")

        if isinstance(error, dict) and error.get("message"):
            return str(error["message"])

        if body.get("message"):
            return str(body["message"])

    return str(exc)


def get_groq_error_action(message):
    if "requires terms acceptance" in message:
        return (
            "Aceptar terminos del modelo en "
            "https://console.groq.com/playground?"
            "model=canopylabs%2Forpheus-v1-english"
        )

    return None


def raise_groq_http_error(stage, exc):
    message = get_groq_error_message(exc)
    action = get_groq_error_action(message)
    detail = {
        "provider": "groq",
        "stage": stage,
        "error": type(exc).__name__,
        "message": message
    }

    if action:
        detail["action"] = action

    print(f"Groq error en {stage}: {type(exc).__name__}: {message}")

    raise HTTPException(
        status_code=502,
        detail=detail
    ) from exc


def limit_tts_text(texto):
    max_chars = get_int_config("GROQ_TTS_MAX_CHARS", DEFAULT_TTS_MAX_CHARS)
    texto = " ".join(texto.split())

    if len(texto) <= max_chars:
        return texto

    clipped = texto[:max_chars].rstrip()

    for separator in (". ", "? ", "! ", "; ", ", "):
        position = clipped.rfind(separator)

        if position >= 80:
            return clipped[:position + 1].rstrip()

    return clipped.rstrip(" ,;:.") + "."


def analyze_wav_input(wav_input):
    try:
        with wave.open(io.BytesIO(wav_input), "rb") as wav_file:
            channels = wav_file.getnchannels()
            sample_width = wav_file.getsampwidth()
            sample_rate = wav_file.getframerate()
            pcm = wav_file.readframes(wav_file.getnframes())
    except (EOFError, wave.Error) as exc:
        raise HTTPException(
            status_code=400,
            detail="El cuerpo recibido no es un archivo WAV valido"
        ) from exc

    if channels != 1 or sample_width != 2:
        raise HTTPException(
            status_code=400,
            detail="El WAV debe ser PCM mono de 16 bits"
        )

    samples = array("h")
    samples.frombytes(pcm)

    if sys.byteorder == "big":
        samples.byteswap()

    if not samples:
        raise HTTPException(
            status_code=422,
            detail="El WAV no contiene muestras de audio"
        )

    mean = sum(samples) / len(samples)
    square_sum = sum((sample - mean) ** 2 for sample in samples)
    rms = math.sqrt(square_sum / len(samples))
    peak = max(abs(sample - mean) for sample in samples)

    return {
        "sample_rate": sample_rate,
        "samples": len(samples),
        "rms": rms,
        "peak": peak
    }


def get_transcription_metrics(transcription):
    segments = getattr(transcription, "segments", None) or []
    no_speech_values = [
        float(segment.no_speech_prob)
        for segment in segments
        if getattr(segment, "no_speech_prob", None) is not None
    ]
    logprob_values = [
        float(segment.avg_logprob)
        for segment in segments
        if getattr(segment, "avg_logprob", None) is not None
    ]

    return {
        "no_speech_probability": (
            min(no_speech_values) if no_speech_values else None
        ),
        "avg_logprob": max(logprob_values) if logprob_values else None
    }


def transcribe_audio(client, wav_input):
    transcription = client.audio.transcriptions.create(
        model=get_config("GROQ_STT_MODEL", DEFAULT_STT_MODEL),
        file=(
            "pregunta.wav",
            wav_input,
            "audio/wav"
        ),
        language="es",
        response_format="verbose_json",
        timestamp_granularities=["segment"],
        temperature=0
    )

    metrics = get_transcription_metrics(transcription)
    no_speech_probability = metrics["no_speech_probability"]
    avg_logprob = metrics["avg_logprob"]

    if no_speech_probability is not None:
        print(f"Groq no_speech_prob: {no_speech_probability:.3f}")

    if avg_logprob is not None:
        print(f"Groq avg_logprob: {avg_logprob:.3f}")

    max_probability = get_float_config(
        "GROQ_STT_MAX_NO_SPEECH_PROBABILITY",
        DEFAULT_STT_MAX_NO_SPEECH_PROBABILITY
    )
    if (
        no_speech_probability is not None
        and no_speech_probability >= max_probability
    ):
        return "", metrics

    return transcription.text.strip(), metrics


async def transcribe_request(request, client):
    wav_input = await request.body()

    if not wav_input:
        raise HTTPException(
            status_code=400,
            detail="No se recibio audio WAV"
        )

    metrics = analyze_wav_input(wav_input)
    print(
        f"Audio recibido: {len(wav_input)} bytes, "
        f"{metrics['sample_rate']} Hz, "
        f"RMS={metrics['rms']:.1f}, pico={metrics['peak']:.1f}"
    )

    min_rms = get_float_config("GROQ_STT_MIN_RMS", DEFAULT_STT_MIN_RMS)
    if metrics["rms"] < min_rms:
        raise HTTPException(
            status_code=422,
            detail={
                "error": "audio_too_quiet",
                "message": "El audio no contiene una voz con nivel suficiente",
                "rms": round(metrics["rms"], 1),
                "minimum_rms": min_rms
            }
        )

    try:
        text, transcription_metrics = transcribe_audio(client, wav_input)
    except groq.APIError as exc:
        raise_groq_http_error("transcripcion", exc)

    if not text:
        raise HTTPException(
            status_code=422,
            detail="No se detecto voz en el audio"
        )

    print(f"Usuario: {text}")
    return text, metrics, transcription_metrics


def generate_answer(client, pregunta):
    completion = client.chat.completions.create(
        model=get_config("GROQ_CHAT_MODEL", DEFAULT_CHAT_MODEL),
        messages=[
            {
                "role": "system",
                "content": ASSISTANT_INSTRUCTIONS.strip()
            },
            {
                "role": "user",
                "content": pregunta
            }
        ],
        temperature=get_float_config("GROQ_CHAT_TEMPERATURE", "0.7"),
        max_completion_tokens=get_int_config(
            "GROQ_CHAT_MAX_COMPLETION_TOKENS",
            DEFAULT_CHAT_MAX_COMPLETION_TOKENS
        ),
        top_p=get_float_config("GROQ_CHAT_TOP_P", "1")
    )

    content = completion.choices[0].message.content or ""
    return content.strip()


def synthesize_speech(client, texto):
    texto = limit_tts_text(texto)

    audio_response = client.audio.speech.create(
        model=get_config("GROQ_TTS_MODEL", DEFAULT_TTS_MODEL),
        voice=get_config("GROQ_TTS_VOICE", DEFAULT_TTS_VOICE),
        response_format="wav",
        input=texto
    )

    return audio_response.read()


def wav_to_pcm_response(wav_output):
    wav_file = io.BytesIO(wav_output)

    with wave.open(wav_file, "rb") as wf:
        sample_rate = wf.getframerate()
        channels = wf.getnchannels()
        bits = wf.getsampwidth() * 8
        pcm = wf.readframes(wf.getnframes())

    return Response(
        content=pcm,
        media_type="application/octet-stream",
        headers={
            "X-Audio-Sample-Rate": str(sample_rate),
            "X-Audio-Bits": str(bits),
            "X-Audio-Channels": str(channels)
        }
    )


app = FastAPI()


@app.get("/")
def inicio():
    return {
        "estado": "Servidor Groq del asistente ESP32-C6 funcionando"
    }


@app.post("/transcribe", response_class=PlainTextResponse)
async def transcribe(
    request: Request,
    client=Depends(get_groq_client)
):
    text, audio_metrics, transcription_metrics = await transcribe_request(
        request,
        client
    )
    headers = {
        "X-Input-RMS": f"{audio_metrics['rms']:.1f}",
        "X-Input-Peak": f"{audio_metrics['peak']:.1f}"
    }

    no_speech_probability = transcription_metrics["no_speech_probability"]
    if no_speech_probability is not None:
        headers["X-STT-No-Speech-Probability"] = (
            f"{no_speech_probability:.3f}"
        )

    avg_logprob = transcription_metrics["avg_logprob"]
    if avg_logprob is not None:
        headers["X-STT-Avg-Logprob"] = f"{avg_logprob:.3f}"

    return PlainTextResponse(text, headers=headers)


@app.post("/ask")
async def ask(
    request: Request,
    client=Depends(get_groq_client)
):
    pregunta, _, _ = await transcribe_request(request, client)

    try:
        texto = generate_answer(client, pregunta)
    except groq.APIError as exc:
        raise_groq_http_error("chat", exc)

    print(f"Asistente: {texto}")

    if not texto:
        raise HTTPException(
            status_code=502,
            detail="Groq no devolvio texto para sintetizar"
        )

    try:
        wav_output = synthesize_speech(client, texto)
    except groq.APIError as exc:
        raise_groq_http_error("tts", exc)

    try:
        return wav_to_pcm_response(wav_output)
    except wave.Error as exc:
        raise HTTPException(
            status_code=502,
            detail="Groq devolvio audio WAV invalido"
        ) from exc
