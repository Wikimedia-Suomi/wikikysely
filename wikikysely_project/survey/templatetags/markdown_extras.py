from django import template
from django.utils.html import escape
from django.utils.safestring import mark_safe
import markdown

register = template.Library()

@register.filter
def markdownify(value):
    """Render Markdown text to HTML with line breaks."""
    if not value:
        return ""
    escaped = escape(value)
    html = markdown.markdown(escaped, extensions=["nl2br"])
    return mark_safe(html)
