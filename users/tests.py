from django.test import TestCase

from users.serializers import SocialAuthSerializer


class SocialAuthSerializerTests(TestCase):
    def test_apple_empty_email_accepted(self):
        ser = SocialAuthSerializer(
            data={
                "provider": "apple",
                "token": "header.payload.sig",
                "name": "",
                "email": "",
                "language": "tr",
            },
        )
        self.assertTrue(ser.is_valid(), ser.errors)

    def test_apple_null_email_accepted(self):
        ser = SocialAuthSerializer(
            data={
                "provider": "apple",
                "token": "header.payload.sig",
                "email": None,
            },
        )
        self.assertTrue(ser.is_valid(), ser.errors)
        self.assertEqual(ser.validated_data["email"], "")

    def test_missing_token_rejected(self):
        ser = SocialAuthSerializer(data={"provider": "apple", "token": "   "})
        self.assertFalse(ser.is_valid())
        self.assertIn("token", ser.errors)
