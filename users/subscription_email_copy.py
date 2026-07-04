"""Localized strings for the subscription-invite broadcast email (en, tr, de, fr, es)."""

from __future__ import annotations

from typing import Any

from .password_email_copy import normalize_email_language


def subscription_email_context(*, lang: str, first_name: str, store_url_ios: str = "", store_url_android: str = "") -> dict[str, Any]:
    """Context for ``subscription_inner.html`` + meta (subject, preheader, …)."""
    L = normalize_email_language(lang)
    data = _STRINGS[L]
    greeting = data["greeting_named"].format(name=first_name) if first_name.strip() else data["greeting_generic"]
    return {
        "html_lang": L,
        "subject": data["subject"],
        "preheader": data["preheader"],
        "header_subtitle": data["header_subtitle"],
        "greeting": greeting,
        "body_intro": data["body_intro"],
        "features": data["features"],
        "body_cta": data["body_cta"],
        "cta_label": data["cta_label"],
        "store_url_ios": store_url_ios,
        "store_url_android": store_url_android,
        "footer": data["footer"],
        "plain_body": data["plain_body"].format(greeting=greeting),
        # layout_base.html overrides
        "footer_tagline": data["footer_tagline"],
    }


_STRINGS: dict[str, dict[str, Any]] = {
    "en": {
        "subject": "Unlock Centifi Premium — take control of your finances",
        "preheader": "Start your Centifi subscription and get full access to smart expense tracking.",
        "header_subtitle": "Your premium upgrade is waiting",
        "greeting_named": "Hi {name},",
        "greeting_generic": "Hi there,",
        "body_intro": "Thank you for using Centifi! You're currently on the free plan. Upgrade to <strong>Centifi Premium</strong> to unlock everything:",
        "features": [
            "Unlimited expense lists & categories",
            "Recurring expense automation",
            "AI-powered spending insights",
            "CSV & PDF export",
            "Priority support",
        ],
        "body_cta": "Ready to take full control of your finances? Subscribe in seconds directly from the app.",
        "cta_label": "Start My Subscription",
        "footer": "You're receiving this because you have a Centifi account. If you've already subscribed, thank you — enjoy Premium!",
        "footer_tagline": "smart expense tracking",
        "plain_body": (
            "{greeting}\n\n"
            "Thank you for using Centifi! You're on the free plan.\n"
            "Upgrade to Centifi Premium to unlock unlimited lists, recurring expenses, AI insights, and more.\n\n"
            "Open the app and tap Upgrade to get started.\n\n"
            "If you've already subscribed, thank you and enjoy Premium!"
        ),
    },
    "tr": {
        "subject": "Centifi Premium'u Aç — finanslarının kontrolünü ele al",
        "preheader": "Centifi aboneliğini başlat ve akıllı harcama takibine tam erişim kazan.",
        "header_subtitle": "Premium yükseltmen seni bekliyor",
        "greeting_named": "Merhaba {name},",
        "greeting_generic": "Merhaba,",
        "body_intro": "Centifi'yi kullandığın için teşekkürler! Şu an ücretsiz plandayken, <strong>Centifi Premium</strong>'a geçerek her şeyin kilidini açabilirsin:",
        "features": [
            "Sınırsız harcama listesi ve kategori",
            "Tekrarlayan harcama otomasyonu",
            "Yapay zeka destekli harcama analizleri",
            "CSV ve PDF dışa aktarma",
            "Öncelikli destek",
        ],
        "body_cta": "Finanslarını tam anlamıyla kontrol etmeye hazır mısın? Uygulamadan saniyeler içinde abone ol.",
        "cta_label": "Aboneliğimi Başlat",
        "footer": "Bu e-postayı Centifi hesabın olduğu için alıyorsun. Zaten abone olduysan teşekkürler — Premium'un tadını çıkar!",
        "footer_tagline": "akıllı harcama takibi",
        "plain_body": (
            "{greeting}\n\n"
            "Centifi'yi kullandığın için teşekkürler! Şu an ücretsiz plandayken,\n"
            "Centifi Premium'a geçerek sınırsız liste, tekrarlayan harcamalar, yapay zeka analizleri ve daha fazlasına erişebilirsin.\n\n"
            "Uygulamayı aç ve Yükselt butonuna dokun.\n\n"
            "Zaten abone olduysan teşekkürler — Premium'un tadını çıkar!"
        ),
    },
    "de": {
        "subject": "Centifi Premium freischalten — deine Finanzen im Griff",
        "preheader": "Starte dein Centifi-Abo und erhalte vollen Zugriff auf smarte Ausgabenverfolgung.",
        "header_subtitle": "Dein Premium-Upgrade wartet",
        "greeting_named": "Hallo {name},",
        "greeting_generic": "Hallo,",
        "body_intro": "Danke, dass du Centifi nutzt! Du befindest dich aktuell im kostenlosen Plan. Upgrade auf <strong>Centifi Premium</strong> und schalte alles frei:",
        "features": [
            "Unbegrenzte Ausgabenlisten & Kategorien",
            "Automatisierung wiederkehrender Ausgaben",
            "KI-gestützte Ausgabenanalysen",
            "CSV- & PDF-Export",
            "Prioritäts-Support",
        ],
        "body_cta": "Bereit, deine Finanzen vollständig zu kontrollieren? Abonniere direkt in der App in Sekunden.",
        "cta_label": "Mein Abo starten",
        "footer": "Du erhältst diese E-Mail, weil du ein Centifi-Konto hast. Falls du bereits abonniert hast, danke dir — genieße Premium!",
        "footer_tagline": "smarte Ausgabenverfolgung",
        "plain_body": (
            "{greeting}\n\n"
            "Danke, dass du Centifi nutzt! Du bist im kostenlosen Plan.\n"
            "Upgrade auf Centifi Premium für unbegrenzte Listen, wiederkehrende Ausgaben, KI-Analysen und mehr.\n\n"
            "Öffne die App und tippe auf Upgrade.\n\n"
            "Falls du bereits abonniert hast, vielen Dank — genieße Premium!"
        ),
    },
    "fr": {
        "subject": "Débloquez Centifi Premium — prenez le contrôle de vos finances",
        "preheader": "Lancez votre abonnement Centifi et accédez à toutes les fonctionnalités.",
        "header_subtitle": "Votre mise à niveau Premium vous attend",
        "greeting_named": "Bonjour {name},",
        "greeting_generic": "Bonjour,",
        "body_intro": "Merci d'utiliser Centifi ! Vous êtes actuellement sur le plan gratuit. Passez à <strong>Centifi Premium</strong> pour tout débloquer :",
        "features": [
            "Listes de dépenses et catégories illimitées",
            "Automatisation des dépenses récurrentes",
            "Analyses de dépenses pilotées par l'IA",
            "Export CSV & PDF",
            "Support prioritaire",
        ],
        "body_cta": "Prêt à prendre le contrôle total de vos finances ? Abonnez-vous en quelques secondes depuis l'application.",
        "cta_label": "Démarrer mon abonnement",
        "footer": "Vous recevez cet e-mail car vous possédez un compte Centifi. Si vous êtes déjà abonné, merci et profitez de Premium !",
        "footer_tagline": "suivi intelligent des dépenses",
        "plain_body": (
            "{greeting}\n\n"
            "Merci d'utiliser Centifi ! Vous êtes sur le plan gratuit.\n"
            "Passez à Centifi Premium pour des listes illimitées, les dépenses récurrentes, les analyses IA et plus encore.\n\n"
            "Ouvrez l'application et appuyez sur Mettre à niveau.\n\n"
            "Si vous êtes déjà abonné, merci et profitez de Premium !"
        ),
    },
    "es": {
        "subject": "Desbloquea Centifi Premium — toma el control de tus finanzas",
        "preheader": "Inicia tu suscripción a Centifi y obtén acceso completo al seguimiento inteligente de gastos.",
        "header_subtitle": "Tu mejora Premium te espera",
        "greeting_named": "Hola {name},",
        "greeting_generic": "Hola,",
        "body_intro": "¡Gracias por usar Centifi! Actualmente estás en el plan gratuito. Actualiza a <strong>Centifi Premium</strong> para desbloquear todo:",
        "features": [
            "Listas de gastos y categorías ilimitadas",
            "Automatización de gastos recurrentes",
            "Análisis de gastos con inteligencia artificial",
            "Exportación CSV y PDF",
            "Soporte prioritario",
        ],
        "body_cta": "¿Listo para tomar el control total de tus finanzas? Suscríbete en segundos directamente desde la app.",
        "cta_label": "Iniciar mi suscripción",
        "footer": "Recibes este correo porque tienes una cuenta en Centifi. Si ya estás suscrito, ¡gracias y disfruta de Premium!",
        "footer_tagline": "seguimiento inteligente de gastos",
        "plain_body": (
            "{greeting}\n\n"
            "¡Gracias por usar Centifi! Estás en el plan gratuito.\n"
            "Actualiza a Centifi Premium para listas ilimitadas, gastos recurrentes, análisis de IA y más.\n\n"
            "Abre la app y pulsa Mejorar plan.\n\n"
            "Si ya estás suscrito, ¡gracias y disfruta de Premium!"
        ),
    },
}
