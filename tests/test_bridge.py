import unittest

from mavernix_greeter.bridge import Bridge

INFO = {"type": "auth_message", "auth_message_type": "info", "auth_message": "Please touch the device."}
SECRET = {"type": "auth_message", "auth_message_type": "secret", "auth_message": "Password: "}
OK = {"type": "success"}
AUTH_ERR = {"type": "error", "error_type": "auth_error", "description": "pam_authenticate: AUTH_ERR"}


class Talk(unittest.TestCase):
    def setUp(self):
        self.b = Bridge()

    def sent(self):
        out, self.b.sent = self.b.sent, []
        return [r["type"] for r in out]

    def events(self):
        out, self.b.events = self.b.events, []
        return [e["ev"] for e in out]

    def test_password_login(self):
        self.b.ui({"op": "create", "user": "ada"})
        self.assertEqual(self.sent(), ["create_session"])
        self.b.greetd(SECRET)
        self.assertEqual(self.events(), ["message"])
        self.b.ui({"op": "respond", "value": "pw"})
        self.assertEqual(self.b.sent[0], {"type": "post_auth_message_response", "response": "pw"})
        self.sent()
        self.b.greetd(OK)
        self.assertEqual(self.events(), ["ready"])
        self.b.ui({"op": "start", "cmd": ["x"], "env": []})
        self.assertEqual(self.sent(), ["start_session"])
        self.b.greetd(OK)
        self.assertEqual(self.events(), ["launched"])

    def test_info_is_acknowledged_once(self):
        self.b.ui({"op": "create", "user": "ada"})
        self.b.greetd(INFO)
        self.assertEqual(self.events(), ["message"])
        self.assertEqual(self.b.sent[-1], {"type": "post_auth_message_response", "response": None})

    def test_cancel_while_pam_waits_for_a_touch_never_reads_as_success(self):
        self.b.ui({"op": "create", "user": "ada"})
        self.b.greetd(INFO)
        self.sent()
        self.events()
        self.b.ui({"op": "cancel"})
        self.assertEqual(self.sent(), [], "nothing may be sent while greetd still owes an answer")
        self.b.ui({"op": "create", "user": "ada"})
        self.assertEqual(self.sent(), [])
        self.b.greetd(OK)
        self.assertEqual(self.events(), [], "the late answer belongs to the cancelled login")
        self.assertEqual(self.sent(), ["cancel_session"])
        self.b.greetd(OK)
        self.assertEqual(self.sent(), ["create_session"])
        self.assertEqual(self.events(), [])
        self.b.greetd(INFO)
        self.assertEqual(self.events(), ["message"])

    def test_error_message_is_acknowledged_like_info(self):
        self.b.ui({"op": "create", "user": "ada"})
        self.b.greetd({"type": "auth_message", "auth_message_type": "error", "auth_message": "expired"})
        self.assertEqual(self.b.sent[-1], {"type": "post_auth_message_response", "response": None})

    def test_cancel_drops_what_was_waiting_behind_it(self):
        self.b.ui({"op": "create", "user": "ada"})
        self.b.ui({"op": "create", "user": "bob"})
        self.b.ui({"op": "cancel"})
        self.sent()
        self.b.greetd(SECRET)
        self.b.greetd(OK)
        self.assertEqual(self.sent(), ["cancel_session"])

    def test_cancel_when_idle_after_prompt_is_sent_at_once(self):
        self.b.ui({"op": "create", "user": "ada"})
        self.b.greetd(SECRET)
        self.sent()
        self.events()
        self.b.ui({"op": "cancel"})
        self.assertEqual(self.sent(), ["cancel_session"])
        self.b.ui({"op": "respond", "value": "late"})
        self.b.greetd(OK)
        self.assertEqual(self.sent(), [], "a response after cancel goes nowhere")
        self.assertEqual(self.events(), [])

    def test_failure_cancels_before_the_next_login(self):
        self.b.ui({"op": "create", "user": "ada"})
        self.b.greetd(SECRET)
        self.b.ui({"op": "respond", "value": "bad"})
        self.sent()
        self.events()
        self.b.greetd(AUTH_ERR)
        self.assertEqual(self.events(), ["failure"])
        self.assertEqual(self.sent(), ["cancel_session"])
        self.b.ui({"op": "create", "user": "ada"})
        self.assertEqual(self.sent(), [])
        self.b.greetd({"type": "error", "error_type": "error", "description": "unable to send message: Connection refused"})
        self.assertEqual(self.sent(), ["create_session"])
        self.assertEqual(self.events(), [])

    def test_leftover_session_is_cancelled_then_created(self):
        self.b.ui({"op": "create", "user": "ada"})
        self.sent()
        self.b.greetd({"type": "error", "error_type": "error", "description": "a session is already being configured"})
        self.assertEqual(self.sent(), ["cancel_session"])
        self.b.greetd(OK)
        self.assertEqual(self.sent(), ["create_session"])
        self.assertEqual(self.events(), [])

    def test_failed_start_reports_and_cleans_up(self):
        self.b.ui({"op": "create", "user": "ada"})
        self.b.greetd(OK)
        self.events()
        self.b.ui({"op": "start", "cmd": ["x"], "env": []})
        self.sent()
        self.b.greetd({"type": "error", "error_type": "error", "description": "exec failed"})
        self.assertEqual(self.events(), ["error"])
        self.assertEqual(self.sent(), ["cancel_session"])

    def test_respond_without_a_prompt_is_ignored(self):
        self.b.ui({"op": "respond", "value": "x"})
        self.assertEqual(self.sent(), [])
        self.b.ui({"op": "create", "user": "ada"})
        self.b.greetd(INFO)
        self.sent()
        self.b.ui({"op": "respond", "value": "x"})
        self.assertEqual(self.sent(), [])

    def test_start_only_after_ready(self):
        self.b.ui({"op": "start", "cmd": ["x"], "env": []})
        self.assertEqual(self.sent(), [])
        self.assertEqual(self.events(), ["error"])

    def test_events_never_carry_a_response(self):
        self.b.ui({"op": "create", "user": "ada"})
        self.b.greetd(SECRET)
        self.b.ui({"op": "respond", "value": "hunter2"})
        self.b.greetd(OK)
        self.assertNotIn("hunter2", repr(self.b.events))

    def test_unknown_ops_ignored(self):
        self.b.ui({"op": "rm -rf"})
        self.assertEqual((self.sent(), self.events()), ([], []))


if __name__ == "__main__":
    unittest.main()
