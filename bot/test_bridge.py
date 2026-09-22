import json
import unittest

try:
    import bridge
except ImportError:
    from bot import bridge


class BridgeBrainOwnershipTests(unittest.TestCase):
    def test_prepare_brain_body_forces_lm_studio_compatible_json_schema(self):
        body = json.dumps({"model": "qwen/qwen3-vl-8b", "response_format": {"type": "json_object"}}).encode()
        payload = json.loads(bridge.prepare_brain_body(body))
        self.assertEqual(payload["response_format"]["type"], "json_schema")
        self.assertTrue(payload["response_format"]["json_schema"]["schema"]["additionalProperties"])

    def test_prepare_brain_body_preserves_app_schema(self):
        schema = {"type": "json_schema", "json_schema": {"name": "growbot", "schema": {"type": "object"}}}
        payload = json.loads(bridge.prepare_brain_body(json.dumps({"response_format": schema}).encode()))
        self.assertEqual(payload["response_format"], schema)

    def test_reasoning_and_vision_requests_get_a_longer_local_deadline(self):
        body = json.dumps({
            "model": "qwen/qwen3-vl-8b",
            "messages": [{"role": "user", "content": [{"type": "image_url", "image_url": {"url": "data:image/png;base64,x"}}]}],
        }).encode()
        self.assertGreaterEqual(bridge.brain_timeout_seconds(body, autonomous=True), 90)

    def test_human_cancellation_advances_generation(self):
        before = bridge.brain_cancel_generation()
        bridge.cancel_active_brain()
        self.assertGreater(bridge.brain_cancel_generation(), before)
        self.assertTrue(bridge.brain_request_superseded(before))

    def test_autonomous_slot_does_not_compete_with_an_existing_generation(self):
        acquired = bridge._brain_lock.acquire()
        try:
            self.assertFalse(bridge.acquire_brain_slot(True))
        finally:
            if acquired:
                bridge._brain_lock.release()

    def test_superseded_human_turn_is_not_reported_as_success(self):
        generation = bridge.brain_cancel_generation()
        bridge.cancel_active_brain()
        payload, status = bridge.brain_transport_failure(OSError("closed"), False, generation)
        self.assertEqual(status, 409)
        self.assertTrue(payload["retryable"])
        self.assertNotIn("skipped", payload)

    def test_superseded_autonomous_turn_can_be_skipped(self):
        generation = bridge.brain_cancel_generation()
        bridge.cancel_active_brain()
        payload, status = bridge.brain_transport_failure(OSError("closed"), True, generation)
        self.assertEqual(status, 200)
        self.assertTrue(payload["skipped"])


if __name__ == "__main__":
    unittest.main()
