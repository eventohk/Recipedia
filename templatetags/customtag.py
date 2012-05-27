from django import template
from types import *

register = template.Library()

#register.filter('parse_edu', parseedu)
@register.filter(name='split')
def split_item(value, arg):
    if value:
        return value.split(arg)
    else:
        return value
