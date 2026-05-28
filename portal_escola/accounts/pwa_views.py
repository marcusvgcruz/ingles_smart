"""Serve PWA assets from site root so the service worker scope covers the whole app."""

import json
from pathlib import Path

from django.conf import settings
from django.http import HttpResponse
from django.shortcuts import render
from django.templatetags.static import static
from django.views.decorators.cache import cache_control
from django.views.decorators.http import require_GET


def _icon_url(request, name: str) -> str:
    return request.build_absolute_uri(static(f"accounts/icons/{name}"))


@require_GET
@cache_control(max_age=3600, public=True)
def web_manifest(request):
    manifest = {
        "name": f"{settings.SCHOOL_DISPLAY_NAME} — Portal",
        "short_name": settings.SCHOOL_DISPLAY_NAME,
        "description": f"Academic portal — {settings.SCHOOL_DISPLAY_NAME}",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "any",
        "lang": "en",
        "background_color": "#0b0b0b",
        "theme_color": "#ff7a00",
        "icons": [
            {
                "src": _icon_url(request, "icon-192.png"),
                "sizes": "192x192",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": _icon_url(request, "icon-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "any",
            },
            {
                "src": _icon_url(request, "icon-512.png"),
                "sizes": "512x512",
                "type": "image/png",
                "purpose": "maskable",
            },
        ],
    }
    return HttpResponse(
        json.dumps(manifest, ensure_ascii=False),
        content_type="application/manifest+json; charset=utf-8",
    )


@require_GET
@cache_control(max_age=0, must_revalidate=True)
def service_worker(request):
    sw_path = Path(__file__).resolve().parent / "static" / "accounts" / "js" / "sw.js"
    content = sw_path.read_text(encoding="utf-8")
    response = HttpResponse(content, content_type="application/javascript; charset=utf-8")
    return response


@require_GET
def offline_page(request):
    return render(request, "accounts/offline.html")
