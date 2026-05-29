from django.test import RequestFactory, TestCase

from core.request_language import resolve_email_language


class ResolveEmailLanguageTests(TestCase):
    def setUp(self):
        self.factory = RequestFactory()

    def test_body_wins_over_user_profile(self):
        req = self.factory.post("/", HTTP_X_CENTIFI_LANGUAGE="de")
        user = type("U", (), {"language": "en"})()
        lang = resolve_email_language(request=req, body_language="tr", user=user)
        self.assertEqual(lang, "tr")

    def test_header_when_body_empty(self):
        req = self.factory.post("/", HTTP_X_CENTIFI_LANGUAGE="tr")
        lang = resolve_email_language(request=req, body_language="", user=None)
        self.assertEqual(lang, "tr")

    def test_user_profile_fallback(self):
        req = self.factory.post("/")
        user = type("U", (), {"language": "tr"})()
        lang = resolve_email_language(request=req, body_language="", user=user)
        self.assertEqual(lang, "tr")
