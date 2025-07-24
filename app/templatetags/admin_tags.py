from django import template

register = template.Library()

@register.filter
def class_name(value):
    """Mengembalikan nama kelas dari sebuah objek dalam huruf kecil."""
    return value.__class__.__name__.lower()

