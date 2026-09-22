import unittest
from unittest.mock import patch

try:
    import bridge
except ImportError:
    from bot import bridge


class FakeResponse:
    status = 200

    def __init__(self, payload=None):
        self.payload = payload or {"data": [{"id": "qwen/qwen3-vl-8b"}]}

    def read(self, limit=-1):
        import json
        return json.dumps(self.payload).encode()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False


class FakeHandler:
    brain = "http://brain/v1"
    brain_model = "qwen/qwen3-vl-8b"
    kokoro_url = "http://kokoro"
    life_store = object()
    life_coordinator = type("Coordinator", (), {"enabled": True})()


class HealthProbeTests(unittest.TestCase):
    def test_default_brain_model_is_available_for_life_autonomy(self):
        self.assertEqual(bridge.DEFAULT_BRAIN_MODEL, "qwen/qwen3-vl-8b")

    def test_deep_health_separates_brain_and_kokoro(self):
        with patch.object(bridge, "urlopen", side_effect=[FakeResponse(), OSError("offline")]):
            result = bridge.deep_health_snapshot(FakeHandler)
        self.assertTrue(result["ok"])
        self.assertEqual(result["dependencies"]["brain"]["status"], "ok")
        self.assertEqual(result["dependencies"]["kokoro"]["status"], "offline")
        self.assertEqual(result["dependencies"]["life_journal"]["status"], "ready")
        self.assertEqual(result["dependencies"]["life_journal"]["autonomy"], "enabled")

    def test_deep_health_rejects_embedding_only_model_list(self):
        embedding_only = FakeResponse({"data": [{"id": "text-embedding-nomic-embed-text-v1.5"}]})
        with patch.object(bridge, "urlopen", side_effect=[embedding_only, FakeResponse({"status": "ok"})]):
            result = bridge.deep_health_snapshot(FakeHandler)
        self.assertFalse(result["ok"])
        self.assertEqual(result["dependencies"]["brain"]["status"], "error")
        self.assertIn("not loaded", result["dependencies"]["brain"]["error"])

    def test_brain_health_accepts_lm_studio_instance_suffix(self):
        result = None
        with patch.object(bridge, "urlopen", return_value=FakeResponse({"data": [{"id": "qwen/qwen3-vl-8b:2"}]})):
            result = bridge.probe_brain_service("http://brain/v1", "qwen/qwen3-vl-8b")
        self.assertEqual(result["status"], "ok")

    def test_probe_http_service_reports_upstream_http_failure(self):
        from urllib.error import HTTPError
        with patch.object(bridge, "urlopen", side_effect=HTTPError("http://x", 503, "offline", {}, None)):
            result = bridge.probe_http_service("http://x")
        self.assertEqual(result, {"status": "error", "http": 503})


if __name__ == "__main__":
    unittest.main()
