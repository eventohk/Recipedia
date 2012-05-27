from django.conf.urls.defaults import *
import settings
# from recipedia.myuser.forms import signin

# Uncomment the next two lines to enable the admin:
# from django.contrib import admin
# admin.autodiscover()

# It handle serveral views through jQuery dialog interface
dialogurl = patterns('',
    url(r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'dialog/login.html'}, name="d_login"),
    url(r'^ingredient/insert\.html$', 'recipedia.forms.add_ingredient', name="add_ingredient_dlg"),
)
authurl = patterns('',
    (r'^$', 'recipedia.myuser.forms.signin', {'base_template_name': 'basepage.html'}),
    #url(r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}, name="n_login"),
    url(r'^logout/$', 'django.contrib.auth.views.logout', {'template_name': 'registration/logout.html', 'next_page': '/'}, name="n_logout"),
)
urlpatterns = patterns('',
    (r'^$', 'recipedia.views.index'),
    (r'^i18n/', include('django.conf.urls.i18n')),
    (r'^accounts/login/$', 'django.contrib.auth.views.login', {'template_name': 'login.html'}),
    (r'^accounts/', include(authurl)),
    (r'^dialog/', include(dialogurl)),
    (r'^recipe/insert\.html$', 'recipedia.views.create'),
    (r'^recipe/mine\.html$', 'recipedia.views.mine'),
    (r'^recipe/(?P<rpID>[0-9]+)/edit\.html$', 'recipedia.views.edit'),
    (r'^recipe/(?P<rpID>[0-9]+)/contentedit\.html$', 'recipedia.views.create_edit'),
    (r'^recipe/(?P<rpID>[0-9]+)/delete\.html$', 'recipedia.views.delete'),
    (r'^recipe/(?P<rpID>.*)/$', 'recipedia.views.view'),
    (r'^ingredient/insert\.html$', 'recipedia.forms.add_ingredient', {'nondialog': True}),
    url(r'^search/tag$', 'recipedia.views.search',{'lookup': 'tag'} , name="tag_search"),
    (r'^scrp/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT + 'default/js/'}),
    url(r'^media1/images/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT + 'classifieds/default/images/'}, name="c_media"),
    (r'^media1/(?P<path>.*)$', 'django.views.static.serve', {'document_root': settings.MEDIA_ROOT}),
)
