"""
  $Id$
"""
from django.contrib.sites.models import Site
from django.conf import settings

def sites(request):
  return {
    #'site': Site.objects.get(pk=settings.SITE_ID),
    'site': 1,
    'authorised': (request.user.is_authenticated() and request.user.is_active),
    'USER_MEDIA_ROOT': settings.MEDIA_ROOT,
    'document_root': settings.MEDIA_ROOT + 'classifieds/default/images/',
    }
