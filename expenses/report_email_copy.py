"""Localized strings for expense report email (en, tr, de, fr, es — matches app)."""

from __future__ import annotations

from datetime import date
from typing import Any

from users.password_email_copy import normalize_email_language

BACKEND_DEFAULT_PRIVATE_LIST_NAME = "Private list"

_BUILTIN_CATEGORIES = frozenset(
    {"food", "transport", "shopping", "health", "entertainment", "utilities", "other"},
)

_CATEGORY_LABELS: dict[str, dict[str, str]] = {
    "en": {
        "food": "Food & Dining",
        "transport": "Transport",
        "shopping": "Shopping",
        "health": "Health",
        "entertainment": "Entertainment",
        "utilities": "Utilities",
        "other": "Other",
    },
    "tr": {
        "food": "Yemek & Restoran",
        "transport": "Ulaşım",
        "shopping": "Alışveriş",
        "health": "Sağlık",
        "entertainment": "Eğlence",
        "utilities": "Faturalar",
        "other": "Diğer",
    },
    "de": {
        "food": "Essen & Trinken",
        "transport": "Transport",
        "shopping": "Einkaufen",
        "health": "Gesundheit",
        "entertainment": "Unterhaltung",
        "utilities": "Rechnungen",
        "other": "Sonstiges",
    },
    "fr": {
        "food": "Alimentation",
        "transport": "Transport",
        "shopping": "Shopping",
        "health": "Santé",
        "entertainment": "Loisirs",
        "utilities": "Factures",
        "other": "Autre",
    },
    "es": {
        "food": "Comida",
        "transport": "Transporte",
        "shopping": "Compras",
        "health": "Salud",
        "entertainment": "Ocio",
        "utilities": "Facturas",
        "other": "Otros",
    },
}


def category_label(lang: str, slug: str) -> str:
    L = normalize_email_language(lang)
    key = (slug or "other").strip().lower()
    if key not in _BUILTIN_CATEGORIES:
        return slug or key
    return _CATEGORY_LABELS[L].get(key, _CATEGORY_LABELS["en"].get(key, key))


def display_list_name(lang: str, name: str) -> str:
    if not name or not str(name).strip():
        return ""
    if str(name).strip() == BACKEND_DEFAULT_PRIVATE_LIST_NAME:
        L = normalize_email_language(lang)
        return _STRINGS[L]["default_private_list"]
    return name


def type_label(lang: str, is_income: bool) -> str:
    L = normalize_email_language(lang)
    return _STRINGS[L]["type_income" if is_income else "type_expense"]


def report_email_context(
    *,
    lang: str,
    start: date,
    end: date,
    list_label: str,
    count: int,
) -> dict[str, Any]:
    L = normalize_email_language(lang)
    data = _STRINGS[L]
    period = f"{start.isoformat()} – {end.isoformat()}"
    list_suffix = f" — {list_label}" if list_label else ""
    subject = data["subject"].format(period=period, list_suffix=list_suffix)
    header_subtitle = data["header_subtitle"].format(period=period, list_suffix=list_suffix)
    preheader = data["preheader"].format(count=count)
    return {
        "html_lang": L,
        "subject": subject,
        "preheader": preheader,
        "header_subtitle": header_subtitle,
        "greeting": data["greeting"],
        "intro_prefix": data["intro_prefix"],
        "intro_suffix": data["intro_suffix"],
        "period": period,
        "list_label": list_label,
        "empty_message": data["empty_message"],
        "col_date": data["col_date"],
        "col_amount": data["col_amount"],
        "col_category": data["col_category"],
        "col_description": data["col_description"],
        "col_list": data["col_list"],
        "col_type": data["col_type"],
        "footer_sent_by": data["footer_sent_by"],
        "footer_tagline": data["footer_tagline"],
        "plain_body": data["plain_body"].format(
            period=period,
            list_part=f" ({list_label})" if list_label else "",
            count=count,
        ),
    }


_STRINGS: dict[str, dict[str, str]] = {
    "en": {
        "subject": "Centifi expense report ({period}){list_suffix}",
        "preheader": "Centifi expense report: {count} row(s) in this period. CSV attached.",
        "header_subtitle": "Expense report · {period}{list_suffix}",
        "greeting": "Hello,",
        "intro_prefix": "Here is your expense report for",
        "intro_suffix": "A CSV file is attached if you want to import or archive the data.",
        "empty_message": "No expenses in this period.",
        "col_date": "Date",
        "col_amount": "Amount",
        "col_category": "Category",
        "col_description": "Description",
        "col_list": "List",
        "col_type": "Type",
        "type_expense": "Expense",
        "type_income": "Income",
        "default_private_list": "Private list",
        "footer_sent_by": "Sent by",
        "footer_tagline": "smart expense tracking",
        "plain_body": (
            "Hello,\n\n"
            "Your Centifi expense report for {period}{list_part} is in the HTML part "
            "of this message as a table ({count} row(s)). A CSV file is attached for download.\n\n"
            "— Centifi\n"
        ),
    },
    "tr": {
        "subject": "Centifi harcama raporu ({period}){list_suffix}",
        "preheader": "Centifi harcama raporu: bu dönemde {count} kayıt. CSV eklendi.",
        "header_subtitle": "Harcama raporu · {period}{list_suffix}",
        "greeting": "Merhaba,",
        "intro_prefix": "Harcama raporunuz:",
        "intro_suffix": "Verileri dışa aktarmak veya arşivlemek için CSV dosyası ekte.",
        "empty_message": "Bu dönemde harcama yok.",
        "col_date": "Tarih",
        "col_amount": "Tutar",
        "col_category": "Kategori",
        "col_description": "Açıklama",
        "col_list": "Liste",
        "col_type": "Tür",
        "type_expense": "Harcama",
        "type_income": "Gelir",
        "default_private_list": "Özel liste",
        "footer_sent_by": "Gönderen",
        "footer_tagline": "akıllı harcama takibi",
        "plain_body": (
            "Merhaba,\n\n"
            "Centifi harcama raporunuz ({period}{list_part}) HTML bölümünde tablo "
            "olarak yer alıyor ({count} kayıt). İndirmek için CSV dosyası ekte.\n\n"
            "— Centifi\n"
        ),
    },
    "de": {
        "subject": "Centifi Ausgabenbericht ({period}){list_suffix}",
        "preheader": "Centifi Ausgabenbericht: {count} Eintrag/Einträge in diesem Zeitraum. CSV im Anhang.",
        "header_subtitle": "Ausgabenbericht · {period}{list_suffix}",
        "greeting": "Hallo,",
        "intro_prefix": "Hier ist Ihr Ausgabenbericht für",
        "intro_suffix": "Eine CSV-Datei ist im Anhang, falls Sie die Daten importieren oder archivieren möchten.",
        "empty_message": "Keine Ausgaben in diesem Zeitraum.",
        "col_date": "Datum",
        "col_amount": "Betrag",
        "col_category": "Kategorie",
        "col_description": "Beschreibung",
        "col_list": "Liste",
        "col_type": "Typ",
        "type_expense": "Ausgabe",
        "type_income": "Einnahme",
        "default_private_list": "Private Liste",
        "footer_sent_by": "Gesendet von",
        "footer_tagline": "intelligente Ausgabenverfolgung",
        "plain_body": (
            "Hallo,\n\n"
            "Ihr Centifi-Ausgabenbericht für {period}{list_part} steht im HTML-Teil "
            "als Tabelle ({count} Eintrag/Einträge). Eine CSV-Datei ist zum Download im Anhang.\n\n"
            "— Centifi\n"
        ),
    },
    "fr": {
        "subject": "Centifi rapport de dépenses ({period}){list_suffix}",
        "preheader": "Rapport Centifi : {count} ligne(s) sur cette période. CSV en pièce jointe.",
        "header_subtitle": "Rapport de dépenses · {period}{list_suffix}",
        "greeting": "Bonjour,",
        "intro_prefix": "Voici votre rapport de dépenses pour",
        "intro_suffix": "Un fichier CSV est joint si vous souhaitez importer ou archiver les données.",
        "empty_message": "Aucune dépense sur cette période.",
        "col_date": "Date",
        "col_amount": "Montant",
        "col_category": "Catégorie",
        "col_description": "Description",
        "col_list": "Liste",
        "col_type": "Type",
        "type_expense": "Dépense",
        "type_income": "Revenu",
        "default_private_list": "Liste privée",
        "footer_sent_by": "Envoyé par",
        "footer_tagline": "suivi intelligent des dépenses",
        "plain_body": (
            "Bonjour,\n\n"
            "Votre rapport Centifi pour {period}{list_part} se trouve dans la partie HTML "
            "sous forme de tableau ({count} ligne(s)). Un fichier CSV est joint.\n\n"
            "— Centifi\n"
        ),
    },
    "es": {
        "subject": "Centifi informe de gastos ({period}){list_suffix}",
        "preheader": "Informe Centifi: {count} fila(s) en este periodo. CSV adjunto.",
        "header_subtitle": "Informe de gastos · {period}{list_suffix}",
        "greeting": "Hola,",
        "intro_prefix": "Aquí tienes tu informe de gastos para",
        "intro_suffix": "Se adjunta un archivo CSV si quieres importar o archivar los datos.",
        "empty_message": "No hay gastos en este periodo.",
        "col_date": "Fecha",
        "col_amount": "Importe",
        "col_category": "Categoría",
        "col_description": "Descripción",
        "col_list": "Lista",
        "col_type": "Tipo",
        "type_expense": "Gasto",
        "type_income": "Ingreso",
        "default_private_list": "Lista privada",
        "footer_sent_by": "Enviado por",
        "footer_tagline": "seguimiento inteligente de gastos",
        "plain_body": (
            "Hola,\n\n"
            "Tu informe Centifi para {period}{list_part} está en la parte HTML "
            "como tabla ({count} fila(s)). Hay un archivo CSV adjunto.\n\n"
            "— Centifi\n"
        ),
    },
}
