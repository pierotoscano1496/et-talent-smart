import io
import os
import unittest
import wave
from types import SimpleNamespace
from unittest.mock import patch

import groq
import httpx
from fastapi.testclient import TestClient

import server


def make_wav(pcm, sample_rate=16000, channels=1, sample_width=2):
    wav_file = io.BytesIO()

    with wave.open(wav_file, "wb") as wf:
        wf.setnchannels(channels)
        wf.setsampwidth(sample_width)
        wf.setframerate(sample_rate)
        wf.writeframes(pcm)

    return wav_file.getvalue()


class FakeSpeechResponse:
    def __init__(self, wav_output):
        self.wav_output = wav_output

    def read(self):
        return self.wav_output


class FakeTranscriptions:
    def __init__(self, client):
        self.client = client

    def create(self, **kwargs):
        self.client.transcription_kwargs = kwargs
        if self.client.transcription_error:
            raise self.client.transcription_error

        return SimpleNamespace(
            text=self.client.transcription_output,
            segments=self.client.transcription_segments
        )


class FakeSpeech:
    def __init__(self, client):
        self.client = client

    def create(self, **kwargs):
        self.client.speech_kwargs = kwargs
        if self.client.speech_error:
            raise self.client.speech_error

        return FakeSpeechResponse(self.client.wav_output)


class FakeAudio:
    def __init__(self, client):
        self.transcriptions = FakeTranscriptions(client)
        self.speech = FakeSpeech(client)


class FakeChatCompletions:
    def __init__(self, client):
        self.client = client

    def create(self, **kwargs):
        self.client.chat_kwargs = kwargs
        return SimpleNamespace(
            choices=[
                SimpleNamespace(
                    message=SimpleNamespace(
                        content=self.client.chat_output
                    )
                )
            ]
        )


class FakeChat:
    def __init__(self, client):
        self.completions = FakeChatCompletions(client)


class FakeGroqClient:
    def __init__(self, wav_output):
        self.wav_output = wav_output
        self.chat_output = "  Todo funciona correctamente.  "
        self.transcription_output = "  cual es el estado  "
        self.transcription_segments = []
        self.transcription_error = None
        self.speech_error = None
        self.audio = FakeAudio(self)
        self.chat = FakeChat(self)
        self.transcription_kwargs = None
        self.chat_kwargs = None
        self.speech_kwargs = None


class ServerTestCase(unittest.TestCase):
    def setUp(self):
        self.config_patch = patch.dict(
            os.environ,
            {"GROQ_STT_MIN_RMS": "0", "TALENTOSITO_DEVICE_KEY": "test-device"}
        )
        self.config_patch.start()
        self.pcm_output = b"\x01\x02\x03\x04"
        self.fake_groq = FakeGroqClient(make_wav(self.pcm_output))
        server.app.dependency_overrides[server.get_groq_client] = (
            lambda: self.fake_groq
        )
        self.client = TestClient(server.app, headers={"X-Device-Key": "test-device"})

    def tearDown(self):
        server.app.dependency_overrides.clear()
        self.config_patch.stop()

    def test_inicio_returns_health_message(self):
        response = self.client.get("/")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {"estado": "Servidor Groq del asistente ESP32-C6 funcionando"}
        )

    def test_voice_rejects_unauthenticated_device(self):
        response = self.client.post("/ask", content=b"audio", headers={"X-Device-Key": "wrong"})
        self.assertEqual(response.status_code, 401)
        self.assertIsNone(self.fake_groq.transcription_kwargs)

    def test_voice_has_a_body_size_limit(self):
        response = self.client.post("/ask", content=b"x" * (4 * 1024 * 1024 + 1))
        self.assertEqual(response.status_code, 413)

    def test_context_needs_valid_backend_identity(self):
        with patch("server.httpx.AsyncClient.get", new_callable=unittest.mock.AsyncMock) as get:
            get.return_value = httpx.Response(401, request=httpx.Request("GET", "http://backend"))
            response = self.client.post("/ask", content=make_wav(b"\\x10\\x20"), headers={"X-User-Token": "bad"})
        self.assertEqual(response.status_code, 403)
        self.assertIsNone(self.fake_groq.transcription_kwargs)

    def test_ask_returns_pcm_audio_with_metadata_headers(self):
        wav_input = make_wav(b"\x10\x20")

        response = self.client.post(
            "/ask",
            content=wav_input,
            headers={"Content-Type": "audio/wav"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, self.pcm_output)
        self.assertEqual(
            response.headers["content-type"],
            "application/octet-stream"
        )
        self.assertEqual(response.headers["x-audio-sample-rate"], "16000")
        self.assertEqual(response.headers["x-audio-bits"], "16")
        self.assertEqual(response.headers["x-audio-channels"], "1")

        transcription_file = self.fake_groq.transcription_kwargs["file"]
        self.assertEqual(transcription_file[0], "pregunta.wav")
        self.assertEqual(transcription_file[1], wav_input)
        self.assertEqual(transcription_file[2], "audio/wav")
        self.assertEqual(
            self.fake_groq.transcription_kwargs["model"],
            "whisper-large-v3-turbo"
        )
        self.assertEqual(
            self.fake_groq.transcription_kwargs["language"],
            "es"
        )
        self.assertEqual(
            self.fake_groq.transcription_kwargs["response_format"],
            "verbose_json"
        )
        self.assertEqual(
            self.fake_groq.transcription_kwargs["timestamp_granularities"],
            ["segment"]
        )

        chat_messages = self.fake_groq.chat_kwargs["messages"]
        self.assertEqual(chat_messages[1]["content"], "cual es el estado")
        self.assertEqual(
            self.fake_groq.chat_kwargs["model"],
            "openai/gpt-oss-120b"
        )
        self.assertEqual(
            self.fake_groq.chat_kwargs["max_completion_tokens"],
            96
        )

        self.assertEqual(
            self.fake_groq.speech_kwargs["input"],
            "Todo funciona correctamente."
        )
        self.assertEqual(
            self.fake_groq.speech_kwargs["model"],
            "canopylabs/orpheus-v1-english"
        )
        self.assertEqual(self.fake_groq.speech_kwargs["voice"], "troy")

    def test_transcribe_returns_plain_text_without_chat_or_tts(self):
        wav_input = make_wav(b"\x10\x20")
        self.fake_groq.transcription_segments = [
            SimpleNamespace(no_speech_prob=0.02, avg_logprob=-0.12)
        ]

        response = self.client.post(
            "/transcribe",
            content=wav_input,
            headers={"Content-Type": "audio/wav"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.text, "cual es el estado")
        self.assertTrue(
            response.headers["content-type"].startswith("text/plain")
        )
        self.assertEqual(response.headers["x-input-rms"], "0.0")
        self.assertEqual(
            response.headers["x-stt-no-speech-probability"],
            "0.020"
        )
        self.assertEqual(response.headers["x-stt-avg-logprob"], "-0.120")
        self.assertIsNone(self.fake_groq.chat_kwargs)
        self.assertIsNone(self.fake_groq.speech_kwargs)

        transcription_file = self.fake_groq.transcription_kwargs["file"]
        self.assertEqual(transcription_file[0], "pregunta.wav")
        self.assertEqual(transcription_file[1], wav_input)
        self.assertEqual(transcription_file[2], "audio/wav")

    def test_transcribe_reports_groq_error(self):
        response = httpx.Response(
            400,
            request=httpx.Request("POST", "https://api.groq.com"),
            json={"error": {"message": "Audio file is invalid"}}
        )
        self.fake_groq.transcription_error = groq.BadRequestError(
            "Bad request",
            response=response,
            body=response.json()
        )

        api_response = self.client.post(
            "/transcribe",
            content=make_wav(b"\x10\x20"),
            headers={"Content-Type": "audio/wav"}
        )

        self.assertEqual(api_response.status_code, 502)
        self.assertEqual(
            api_response.json()["detail"],
            {
                "provider": "groq",
                "stage": "transcripcion",
                "error": "BadRequestError",
                "message": "Audio file is invalid"
            }
        )

    def test_transcribe_rejects_quiet_audio_before_calling_groq(self):
        with patch.dict(os.environ, {"GROQ_STT_MIN_RMS": "80"}):
            response = self.client.post(
                "/transcribe",
                content=make_wav(b"\x00\x00" * 100),
                headers={"Content-Type": "audio/wav"}
            )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"]["error"], "audio_too_quiet")
        self.assertEqual(response.json()["detail"]["rms"], 0.0)
        self.assertIsNone(self.fake_groq.transcription_kwargs)

    def test_transcribe_rejects_high_no_speech_probability(self):
        self.fake_groq.transcription_output = "Gracias"
        self.fake_groq.transcription_segments = [
            SimpleNamespace(no_speech_prob=0.93, avg_logprob=-0.8)
        ]

        response = self.client.post(
            "/transcribe",
            content=make_wav(b"\x10\x20"),
            headers={"Content-Type": "audio/wav"}
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(
            response.json(),
            {"detail": "No se detecto voz en el audio"}
        )

    def test_ask_limits_text_before_tts(self):
        self.fake_groq.chat_output = (
            "Esta es una respuesta larga para validar que el texto enviado "
            "al sistema de voz se recorta antes de superar el limite del "
            "modelo Orpheus de Groq y asi evitar errores BadRequest."
        )

        response = self.client.post(
            "/ask",
            content=make_wav(b"\x10\x20"),
            headers={"Content-Type": "audio/wav"}
        )

        self.assertEqual(response.status_code, 200)
        self.assertLessEqual(len(self.fake_groq.speech_kwargs["input"]), 190)

    def test_ask_reports_groq_error_stage(self):
        response = httpx.Response(
            400,
            request=httpx.Request("POST", "https://api.groq.com"),
            json={
                "error": {
                    "message": "Input must be at most 200 characters"
                }
            }
        )
        self.fake_groq.speech_error = groq.BadRequestError(
            "Bad request",
            response=response,
            body=response.json()
        )

        api_response = self.client.post(
            "/ask",
            content=make_wav(b"\x10\x20"),
            headers={"Content-Type": "audio/wav"}
        )

        self.assertEqual(api_response.status_code, 502)
        self.assertEqual(
            api_response.json(),
            {
                "detail": {
                    "provider": "groq",
                    "stage": "tts",
                    "error": "BadRequestError",
                    "message": "Input must be at most 200 characters"
                }
            }
        )

    def test_groq_terms_error_includes_corrective_action(self):
        action = server.get_groq_error_action(
            "The model `canopylabs/orpheus-v1-english` "
            "requires terms acceptance."
        )

        self.assertEqual(
            action,
            "Aceptar terminos del modelo en "
            "https://console.groq.com/playground?"
            "model=canopylabs%2Forpheus-v1-english"
        )

    def test_ask_rejects_empty_body(self):
        response = self.client.post(
            "/ask",
            content=b"",
            headers={"Content-Type": "audio/wav"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"detail": "No se recibio audio WAV"}
        )

    def test_transcribe_rejects_empty_body(self):
        response = self.client.post(
            "/transcribe",
            content=b"",
            headers={"Content-Type": "audio/wav"}
        )

        self.assertEqual(response.status_code, 400)
        self.assertEqual(
            response.json(),
            {"detail": "No se recibio audio WAV"}
        )


if __name__ == "__main__":
    unittest.main()
