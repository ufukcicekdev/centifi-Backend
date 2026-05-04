from django.http import HttpResponse


def health(_request):
    return HttpResponse("ok", content_type="text/plain; charset=utf-8")


def app_password_reset_bridge(request):
    """
    Legacy HTTPS URL from older emails. Password reset is now: open the app → Forgot password → enter the 6-digit code from email.
    """
    if request.method != "GET":
        return HttpResponse("Method not allowed", status=405, content_type="text/plain; charset=utf-8")
    html = """<!DOCTYPE html>
<html lang="en"><head>
  <meta charset="utf-8"/>
  <meta name="viewport" content="width=device-width, initial-scale=1"/>
  <title>Centifi</title>
</head>
<body style="font-family:system-ui,-apple-system,BlinkMacSystemFont,sans-serif;background:#0b1326;color:#dee2f1;margin:0;padding:28px 16px;text-align:center;">
  <p style="font-size:17px;line-height:1.5;margin:0 0 12px;">Password reset is done in the Centifi app.</p>
  <p style="font-size:14px;color:#9ca3af;margin:0;line-height:1.55;">Open Centifi, tap <strong>Forgot password</strong>, then enter the <strong>6-digit code</strong> we sent to your email.</p>
</body></html>"""
    return HttpResponse(html, content_type="text/html; charset=utf-8")
