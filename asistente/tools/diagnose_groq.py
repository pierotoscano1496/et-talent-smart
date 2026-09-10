import argparse
import io
import math
import os
import sys
import wave
from pathlib import Path

import groq
from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

import server


def make_test_wav(seconds=4, sample_rate=16000):
    pcm = bytearray()
    frequency = 440
    amplitude = 9000

    for index in range(seconds * sample_rate):
        sample = int(
            amplitude *
            math.sin(2 * math.pi * frequency * index / sample_rate)
        )
        pcm.extend(sample.to_bytes(2, "little", signed=True))

    wav_file = io.BytesIO()

    with wave.open(wav_file, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(sample_rate)
        wf.writeframes(bytes(pcm))

    return wav_file.getvalue()


def describe_error(stage, exc):
    print(f"[FAIL] {stage}: {type(exc).__name__}")
    print(server.get_groq_error_message(exc))


def run_stt(client):
    wav_input = make_test_wav()
    print(f"[INFO] STT model: {server.get_config('GROQ_STT_MODEL', server.DEFAULT_STT_MODEL)}")
    print(f"[INFO] WAV bytes: {len(wav_input)}")

    text, metrics = server.transcribe_audio(client, wav_input)
    print(f"[OK] STT respondio: {text!r}")
    print(f"[OK] STT metricas: {metrics!r}")
    return text


def run_chat(client, prompt):
    print(f"[INFO] Chat model: {server.get_config('GROQ_CHAT_MODEL', server.DEFAULT_CHAT_MODEL)}")
    text = server.generate_answer(client, prompt)
    print(f"[OK] Chat respondio ({len(text)} chars): {text!r}")
    return text


def run_tts(client, text):
    limited_text = server.limit_tts_text(text)
    print(f"[INFO] TTS model: {server.get_config('GROQ_TTS_MODEL', server.DEFAULT_TTS_MODEL)}")
    print(f"[INFO] TTS voice: {server.get_config('GROQ_TTS_VOICE', server.DEFAULT_TTS_VOICE)}")
    print(f"[INFO] TTS input chars: {len(limited_text)}")

    wav_output = server.synthesize_speech(client, limited_text)
    pcm_response = server.wav_to_pcm_response(wav_output)
    print(f"[OK] TTS devolvio PCM: {len(pcm_response.body)} bytes")
    print(f"[OK] Sample rate: {pcm_response.headers['x-audio-sample-rate']}")
    print(f"[OK] Bits: {pcm_response.headers['x-audio-bits']}")
    print(f"[OK] Channels: {pcm_response.headers['x-audio-channels']}")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--skip-stt",
        action="store_true",
        help="No prueba transcripcion; usa texto fijo para chat/TTS."
    )
    args = parser.parse_args()

    load_dotenv()

    if not os.getenv("GROQ_API_KEY"):
        raise SystemExit("Falta GROQ_API_KEY en .env")

    client = server.get_groq_client()

    if args.skip_stt:
        question = "Responde con una frase corta de prueba."
    else:
        try:
            transcription = run_stt(client)
        except groq.APIError as exc:
            describe_error("transcripcion", exc)
            raise SystemExit(1) from exc

        question = transcription or "Responde con una frase corta de prueba."

    try:
        answer = run_chat(client, question)
    except groq.APIError as exc:
        describe_error("chat", exc)
        raise SystemExit(1) from exc

    try:
        run_tts(client, answer)
    except groq.APIError as exc:
        describe_error("tts", exc)
        raise SystemExit(1) from exc
    except wave.Error as exc:
        print(f"[FAIL] wav: {exc}")
        raise SystemExit(1) from exc


if __name__ == "__main__":
    main()
