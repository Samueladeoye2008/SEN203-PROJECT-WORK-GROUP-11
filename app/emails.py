"""Branded HTML email layout (inline CSS, because email clients ignore stylesheets)."""
from markupsafe import escape


def build_html(name, logo_url, heading, paragraphs, button=None):
    body = "".join(
        f'<p style="margin:0 0 14px;font-size:15px;line-height:1.5;color:#202124">{escape(p)}</p>'
        for p in paragraphs)
    cta = ""
    if button:
        label, url = button
        cta = (f'<p style="margin:22px 0"><a href="{escape(url)}" style="background:#1a73e8;'
               f'color:#ffffff;text-decoration:none;padding:12px 22px;border-radius:999px;'
               f'font-weight:600;display:inline-block">{escape(label)}</a></p>')
    return (
        '<div style="background:#f1f3f4;padding:24px 12px;font-family:Arial,Helvetica,sans-serif">'
        '<div style="max-width:520px;margin:0 auto;background:#ffffff;border-radius:16px;padding:28px">'
        f'<img src="{escape(logo_url)}" width="44" height="44" alt="" style="border-radius:10px;vertical-align:middle">'
        f'<span style="font-size:18px;font-weight:700;vertical-align:middle;margin-left:10px;color:#202124">{escape(name)}</span>'
        f'<h1 style="font-size:22px;margin:22px 0 14px;color:#202124">{escape(heading)}</h1>'
        f'{body}{cta}'
        f'<p style="margin:24px 0 0;font-size:12px;color:#5f6368">Sent by {escape(name)}. '
        'If you did not expect this email you can ignore it.</p></div></div>')
