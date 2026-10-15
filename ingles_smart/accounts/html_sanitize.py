"""Sanitização do HTML dos posts do feed.

O conteúdo chega do editor Quill no navegador, mas o servidor aceita qualquer
POST — inclusive um `<script>` forjado. Por isso a limpeza acontece SEMPRE no
servidor, antes de gravar, e o template pode renderizar com `|safe` sem risco
de XSS armazenado.

A lista de tags abaixo é o que a toolbar do feed oferece (ver feed.html).
"""

import nh3

# Tags permitidas (o que o editor do feed produz)
TAGS_PERMITIDAS = {
    "p", "br", "div", "span",
    "strong", "b", "em", "i", "u", "s",
    "h1", "h2", "h3", "h4",
    "ul", "ol", "li",
    "a", "blockquote", "code", "pre", "hr",
}

# Atributos permitidos por tag (nh3 já bloqueia on* e javascript:)
ATRIBUTOS_PERMITIDOS = {
    "a": {"href", "title"},
}

ESQUEMAS_URL = {"http", "https", "mailto"}


def sanitizar_html(conteudo: str) -> str:
    """Devolve o HTML limpo, sem scripts/eventos/URLs perigosas."""
    if not conteudo:
        return ""
    return nh3.clean(
        conteudo,
        tags=TAGS_PERMITIDAS,
        attributes=ATRIBUTOS_PERMITIDOS,
        url_schemes=ESQUEMAS_URL,
        link_rel="noopener noreferrer",
    )
