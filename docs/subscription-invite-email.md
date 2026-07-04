# Subscription Invite Email — Broadcast

Kullanıcılara abonelik daveti maili gönderir. Her kullanıcıya ayrı ayrı, kendi dil tercihine göre (`user.language`) gider.

**Desteklenen diller:** `en` · `tr` · `de` · `fr` · `es`

---

## Dosyalar

| Dosya | Açıklama |
|---|---|
| `users/subscription_email_copy.py` | 5 dil için subject, body, CTA string'leri + `subscription_email_context()` |
| `email_templates/subscription_inner.html` | HTML inner template (checkmark liste + mor CTA butonu) |
| `users/management/commands/send_subscription_invite.py` | Django management command |

---

## Kullanım

```bash
# Dry-run — kimseye göndermeden kimi etkileyeceğini listeler
python manage.py send_subscription_invite --dry-run

# Tüm aktif kullanıcılara gönder
python manage.py send_subscription_invite

# Sadece belirli bir dildeki kullanıcılara
python manage.py send_subscription_invite --lang tr
python manage.py send_subscription_invite --lang en

# Premium olmayanlar (User modelinde is_premium alanı varsa)
python manage.py send_subscription_invite --non-premium-only

# Batch — ilk 500 kullanıcı
python manage.py send_subscription_invite --limit 500

# Batch — 2. 500'ü (offset ile devam)
python manage.py send_subscription_invite --limit 500 --offset 500

# Gönderimler arası bekleme süresini ayarla (default 0.1s)
python manage.py send_subscription_invite --delay 0.5
```

---

## Önerilen Akış (Tüm DB'ye Gönderim)

1. Önce dry-run ile kaç kullanıcıya gideceğini gör:
   ```bash
   python manage.py send_subscription_invite --dry-run
   ```
2. Küçük bir batch ile test et:
   ```bash
   python manage.py send_subscription_invite --limit 10
   ```
3. Kademeli olarak tüm kullanıcılara gönder:
   ```bash
   python manage.py send_subscription_invite --limit 500 --offset 0
   python manage.py send_subscription_invite --limit 500 --offset 500
   # ...
   ```

---

## Tek Kullanıcıya Test Maili

```bash
python manage.py shell -c "
from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from core.email_branding import attach_centifi_logo_inline_if_needed, wrap_branded_email_html
from users.subscription_email_copy import subscription_email_context

ctx = subscription_email_context(lang='tr', first_name='Ufuk')
inner = render_to_string('subscription_inner.html', ctx)
html = wrap_branded_email_html(inner_html=inner, document_title=ctx['subject'],
    header_subtitle=ctx['header_subtitle'], preheader=ctx['preheader'],
    html_lang='tr', footer_tagline=ctx['footer_tagline'])
msg = EmailMultiAlternatives(ctx['subject'], ctx['plain_body'], settings.DEFAULT_FROM_EMAIL, ['test@example.com'])
msg.attach_alternative(html, 'text/html')
attach_centifi_logo_inline_if_needed(msg)
msg.send()
print('Gönderildi.')
"
```

---

## Yeni Dil Eklemek

`users/subscription_email_copy.py` dosyasındaki `_STRINGS` dict'ine yeni bir dil bloğu ekle ve `normalize_email_language()` içindeki `SUPPORTED` set'ine dahil et.
