"""Localized strings for password-reset OTP email (must match app languages: en, tr, de, fr, es)."""

from __future__ import annotations

from typing import Any

SUPPORTED = frozenset({"en", "tr", "de", "fr", "es"})


def normalize_email_language(code: str | None) -> str:
    if not code or not isinstance(code, str):
        return "en"
    base = code.strip().lower().split("-")[0]
    return base if base in SUPPORTED else "en"


def otp_email_context(*, lang: str, first_name: str, plain_code: str) -> dict[str, Any]:
    """Context for ``auth/password_reset_otp_inner.html`` + meta (subject, preheader, …)."""
    L = normalize_email_language(lang)
    data = _STRINGS[L]
    greeting = data["greeting_named"].format(name=first_name) if first_name.strip() else data["greeting_generic"]
    return {
        "html_lang": L,
        "subject": data["subject"],
        "preheader": data["preheader"],
        "header_subtitle": data["header_subtitle"],
        "greeting": greeting,
        "body": data["body"],
        "code": plain_code,
        "footer": data["footer"],
        "plain_body": data["plain_body"].format(
            greeting=greeting,
            code=plain_code,
        ),
    }


_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "subject": "Centifi — Your password reset code",
        "preheader": "Your Centifi password reset code — valid 15 minutes.",
        "header_subtitle": "Password reset",
        "greeting_named": "Hello {name},",
        "greeting_generic": "Hello,",
        "body": "We received a request to reset the password for your Centifi account. Enter this 6-digit code in the app to set a new password. The code expires in 15 minutes.",
        "footer": "If you did not request a password reset, you can ignore this email.",
        "plain_body": "{greeting}\n\nWe received a request to reset your Centifi password.\nEnter this 6-digit code in the app (valid 15 minutes):\n\n{code}\n\nIf you did not request this, you can ignore this email.\n",
    },
    "tr": {
        "subject": "Centifi — Şifre sıfırlama kodunuz",
        "preheader": "Centifi şifre sıfırlama kodunuz — 15 dakika geçerlidir.",
        "header_subtitle": "Şifre sıfırlama",
        "greeting_named": "Merhaba {name},",
        "greeting_generic": "Merhaba,",
        "body": "Centifi hesabınız için şifre sıfırlama isteği aldık. Uygulamada yeni şifre belirlemek için bu 6 haneli kodu girin. Kod 15 dakika geçerlidir.",
        "footer": "Bu isteği siz yapmadıysanız bu e-postayı yok sayabilirsiniz.",
        "plain_body": "{greeting}\n\nCentifi şifrenizi sıfırlama talebi aldık.\nUygulamada kullanmak üzere 6 haneli kodunuz (15 dakika geçerli):\n\n{code}\n\nBu isteği siz yapmadıysanız bu e-postayı yok sayabilirsiniz.\n",
    },
    "de": {
        "subject": "Centifi — Ihr Passwort-Reset-Code",
        "preheader": "Ihr Centifi Passwort-Reset-Code — 15 Minuten gültig.",
        "header_subtitle": "Passwort zurücksetzen",
        "greeting_named": "Hallo {name},",
        "greeting_generic": "Hallo,",
        "body": "Wir haben eine Anfrage zum Zurücksetzen Ihres Centifi-Passworts erhalten. Geben Sie diesen 6-stelligen Code in der App ein, um ein neues Passwort festzulegen. Der Code ist 15 Minuten gültig.",
        "footer": "Wenn Sie diese Anfrage nicht gestellt haben, können Sie diese E-Mail ignorieren.",
        "plain_body": "{greeting}\n\nWir haben eine Anfrage zum Zurücksetzen Ihres Centifi-Passworts erhalten.\nGeben Sie diesen 6-stelligen Code in der App ein (15 Minuten gültig):\n\n{code}\n\nWenn Sie das nicht waren, ignorieren Sie diese E-Mail.\n",
    },
    "fr": {
        "subject": "Centifi — Votre code de réinitialisation",
        "preheader": "Votre code de réinitialisation Centifi — valide 15 minutes.",
        "header_subtitle": "Réinitialisation du mot de passe",
        "greeting_named": "Bonjour {name},",
        "greeting_generic": "Bonjour,",
        "body": "Nous avons reçu une demande de réinitialisation du mot de passe de votre compte Centifi. Saisissez ce code à 6 chiffres dans l’application pour définir un nouveau mot de passe. Le code expire dans 15 minutes.",
        "footer": "Si vous n’êtes pas à l’origine de cette demande, vous pouvez ignorer cet e-mail.",
        "plain_body": "{greeting}\n\nNous avons reçu une demande de réinitialisation de votre mot de passe Centifi.\nSaisissez ce code à 6 chiffres dans l’application (valide 15 minutes) :\n\n{code}\n\nSi vous n’avez pas demandé cela, ignorez cet e-mail.\n",
    },
    "es": {
        "subject": "Centifi — Tu código para restablecer la contraseña",
        "preheader": "Tu código de restablecimiento de Centifi — válido 15 minutos.",
        "header_subtitle": "Restablecer contraseña",
        "greeting_named": "Hola, {name}:",
        "greeting_generic": "Hola,",
        "body": "Recibimos una solicitud para restablecer la contraseña de tu cuenta Centifi. Introduce este código de 6 dígitos en la aplicación para establecer una nueva contraseña. El código caduca en 15 minutos.",
        "footer": "Si no solicitaste esto, puedes ignorar este correo.",
        "plain_body": "{greeting}\n\nRecibimos una solicitud para restablecer tu contraseña de Centifi.\nIntroduce este código de 6 dígitos en la app (válido 15 minutos):\n\n{code}\n\nSi no fuiste tú, ignora este correo.\n",
    },
}
