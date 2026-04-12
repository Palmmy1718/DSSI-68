from django import template
from django.urls import NoReverseMatch, reverse
from django.utils.translation import override

register = template.Library()

@register.simple_tag(takes_context=True)
def switch_lang_url(context, lang_code: str) -> str:
    request = context.get("request")
    if request is None:
        return "/"

    match = getattr(request, "resolver_match", None)
    if match is None:
        return request.get_full_path()

    try:
        with override(lang_code):
            return reverse(match.view_name, args=match.args, kwargs=match.kwargs)
    except NoReverseMatch:
        return request.get_full_path()
