import json
from urllib.parse import urlencode

from django.http import HttpResponse
from django.utils.html import escape


def health(_request):
    return HttpResponse("ok", content_type="text/plain; charset=utf-8")


def app_password_reset_bridge(request):
    """
    GET ?uid=&token= — E-postadaki **https** linki (Gmail güvenilir açar); sayfa ``centifi://reset-password`` ile
    Expo uygulamasına yönlendirir. Doğrudan ``centifi://`` e-postada çoğu istemcide çalışmaz.
    """
    if request.method != "GET":
        return HttpResponse("Method not allowed", status=405, content_type="text/plain; charset=utf-8")
    uid = (request.GET.get("uid") or "").strip()
    token = (request.GET.get("token") or "").strip()
    if not uid or not token:
        body = (
            "<!DOCTYPE html><html><head><meta charset='utf-8'/><title>Centifi</title></head>"
            "<body style='font-family:system-ui;padding:24px;'><p>Invalid or incomplete reset link.</p></body></html>"
        )
        return HttpResponse(body, status=400, content_type="text/html; charset=utf-8")

    deep = "centifi://reset-password?" + urlencode({"uid": uid, "token": token})
    href = escape(deep, quote=True)
    deep_json = json.dumps(deep)
    html = f"""<!DOCTYPE html>
<html lang="en"><head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Centifi</title>
</head>
<body style="font-family:system-ui,-apple-system,BlinkMacSystemFont,sans-serif;background:#0b1326;color:#dee2f1;margin:0;padding:28px 16px;text-align:center;">
  <p style="font-size:17px;line-height:1.5;margin:0 0 8px;">Open the Centifi app to choose a new password.</p>
  <p style="font-size:14px;color:#9ca3af;margin:0 0 20px;">If the app does not open automatically, tap the button.</p>
  <p style="margin:16px 0 24px;">
    <a id="open" href="{href}" style="display:inline-block;background:#6C63FF;color:#fff;text-decoration:none;font-weight:700;padding:14px 26px;border-radius:12px;font-size:16px;">Open Centifi</a>
  </p>
  <p style="font-size:12px;color:#6b7280;line-height:1.45;">Install Centifi from the App Store or Play Store on this phone if you have not already.</p>
  <script>
    setTimeout(function () {{
      try {{ window.location = {deep_json}; }} catch (e) {{}}
    }}, 400);
  </script>
</body></html>"""
    return HttpResponse(html, content_type="text/html; charset=utf-8")
