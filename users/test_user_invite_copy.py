"""Localized strings for test-user invite emails (en, tr, de, fr, es)."""

from __future__ import annotations

from typing import Any

SUPPORTED = frozenset({"en", "tr", "de", "fr", "es"})


def normalize_email_language(code: str | None) -> str:
    if not code or not isinstance(code, str):
        return "en"
    base = code.strip().lower().split("-")[0]
    return base if base in SUPPORTED else "en"


def invite_email_context(*, lang: str, platform_label: str, invite_url: str) -> dict[str, Any]:
    L = normalize_email_language(lang)
    data = _STRINGS[L]
    return {
        "html_lang": L,
        "subject": data["subject"],
        "preheader": data["preheader"].format(platform=platform_label),
        "header_subtitle": data["header_subtitle"],
        "greeting": data["greeting"],
        "body": data["body"].format(platform=platform_label),
        "cta": data["cta"],
        "invite_url": invite_url,
        "footer": data["footer"],
        "plain_body": data["plain_body"].format(
            greeting=data["greeting"],
            body=data["body"].format(platform=platform_label),
            invite_url=invite_url,
            footer=data["footer"],
        ),
    }


_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "subject": "Centifi — You're invited to test the app",
        "preheader": "Your {platform} test access link for Centifi.",
        "header_subtitle": "Beta invite",
        "greeting": "Hello,",
        "body": "Thanks for signing up to test Centifi on {platform}. Use the button below to install or open the app. If the button does not work, copy the link into your browser.",
        "cta": "Open Centifi ({platform})",
        "footer": "Questions? Reply to this email or write to info@centifi.app.",
        "plain_body": "{greeting}\n\n{body}\n\n{invite_url}\n\n{footer}\n",
    },
    "tr": {
        "subject": "Centifi — Test kullanıcısı davetiniz",
        "preheader": "Centifi {platform} test erişim bağlantınız.",
        "header_subtitle": "Beta daveti",
        "greeting": "Merhaba,",
        "body": "Centifi’yi {platform} üzerinde test etmek için başvurduğunuz için teşekkürler. Uygulamayı yüklemek veya açmak için aşağıdaki düğmeyi kullanın. Düğme çalışmazsa bağlantıyı tarayıcınıza yapıştırın.",
        "cta": "Centifi’yi aç ({platform})",
        "footer": "Sorularınız mı var? Bu e-postayı yanıtlayın veya info@centifi.app adresine yazın.",
        "plain_body": "{greeting}\n\n{body}\n\n{invite_url}\n\n{footer}\n",
    },
    "de": {
        "subject": "Centifi — Einladung zum App-Test",
        "preheader": "Ihr Centifi-Testzugang für {platform}.",
        "header_subtitle": "Beta-Einladung",
        "greeting": "Hallo,",
        "body": "Danke für Ihre Bewerbung, Centifi auf {platform} zu testen. Nutzen Sie die Schaltfläche unten, um die App zu installieren oder zu öffnen. Funktioniert sie nicht, kopieren Sie den Link in den Browser.",
        "cta": "Centifi öffnen ({platform})",
        "footer": "Fragen? Antworten Sie auf diese E-Mail oder schreiben Sie an info@centifi.app.",
        "plain_body": "{greeting}\n\n{body}\n\n{invite_url}\n\n{footer}\n",
    },
    "fr": {
        "subject": "Centifi — Invitation à tester l’application",
        "preheader": "Votre lien d’accès test Centifi pour {platform}.",
        "header_subtitle": "Invitation bêta",
        "greeting": "Bonjour,",
        "body": "Merci pour votre candidature pour tester Centifi sur {platform}. Utilisez le bouton ci-dessous pour installer ou ouvrir l’application. Si le bouton ne fonctionne pas, copiez le lien dans votre navigateur.",
        "cta": "Ouvrir Centifi ({platform})",
        "footer": "Des questions ? Répondez à cet e-mail ou écrivez à info@centifi.app.",
        "plain_body": "{greeting}\n\n{body}\n\n{invite_url}\n\n{footer}\n",
    },
    "es": {
        "subject": "Centifi — Invitación para probar la app",
        "preheader": "Tu enlace de acceso de prueba de Centifi para {platform}.",
        "header_subtitle": "Invitación beta",
        "greeting": "Hola,",
        "body": "Gracias por solicitar probar Centifi en {platform}. Usa el botón de abajo para instalar o abrir la app. Si no funciona, copia el enlace en tu navegador.",
        "cta": "Abrir Centifi ({platform})",
        "footer": "¿Preguntas? Responde a este correo o escribe a info@centifi.app.",
        "plain_body": "{greeting}\n\n{body}\n\n{invite_url}\n\n{footer}\n",
    },
}
