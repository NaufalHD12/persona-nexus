from django import template
from django.urls import reverse
from django.utils.safestring import mark_safe
from app.models import UserProfile
import re

register = template.Library()

@register.filter(name='render_mentions')
def render_mentions(value):
    """
    Finds all @username patterns in a text and replaces them with a link
    to the user's profile page, but only if the user exists.
    """
    # Temukan semua username yang di-mention
    mentioned_usernames = set(re.findall(r'@(\w+)', value))
    
    if not mentioned_usernames:
        return value

    # Dapatkan daftar username yang benar-benar ada di database
    existing_users = set(UserProfile.objects.filter(
        username__in=mentioned_usernames
    ).values_list('username', flat=True))

    # Ganti setiap username yang valid dengan tautan
    for username in existing_users:
        profile_url = reverse('profile_detail', kwargs={'username': username})
        link = f'<a href="{profile_url}" class="font-bold text-secondary-accent hover:underline">@{username}</a>'
        
        # Gunakan regex untuk memastikan kita hanya mengganti kata utuh
        value = re.sub(r'(?<!\w)@' + re.escape(username) + r'(?!\w)', link, value)

    return mark_safe(value)
