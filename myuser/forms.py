# from classifieds import gethash
# from django.core.mail import EmailMessage
# from django.core.urlresolvers import reverse
# from django.forms.widgets import PasswordInput
from django import forms
from django.conf import settings
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User
from django.contrib.sites.models import Site
# from django.core.exceptions import ImproperlyConfigured
from django.shortcuts import redirect, render_to_response
from django.template import RequestContext #, Context, loader
from django.utils.translation import ugettext_lazy as _
from django.views.decorators.cache import never_cache
from registration.models import RegistrationProfile, RegistrationManager

class SigninForm(UserCreationForm):
  email = forms.EmailField(label=_("E-mail"), max_length=75)
  tos = forms.BooleanField(widget=forms.CheckboxInput, #(attrs=attrs_dict)
                           label=_(u'I have read and agree to the Terms of Service'),
                           error_messages={ 'required': _("You must agreed the terms to register") })
  def clean_username(self):
    user = self.cleaned_data['username'].strip()
    if user.isspace():
      raise forms.ValidationError(_("User name could not be space only."))
    if len(user) < 5:
        raise forms.ValidationError(_("User name is too short. It should at least 5 characters"))
    if len(user) > 30:
        raise forms.ValidationError(_("User name is too long. Its maximum characters are 30."))
    try:
      user = User.objects.get(username__iexact=self.cleaned_data['username'])
    except User.DoesNotExist:
      return self.cleaned_data['username'].replace(' ', '')
    raise forms.ValidationError(_("This user name has been used."))

  def clean_password1(self):
    if self.cleaned_data['password1'].isspace():
      raise forms.ValidationError(_("Your password is not eligible."))
    else:
      return self.cleaned_data['password1'].replace(' ', '')

  def clean_password2(self):
    if self.cleaned_data['password2'].isspace():
      raise forms.ValidationError(_("Your password is not eligible."))
    else:
      return self.cleaned_data['password2'].replace(' ', '')

  def clean(self):
    if 'password1' in self.cleaned_data and 'password2' in self.cleaned_data:
      if self.cleaned_data['password1'] != self.cleaned_data['password2']:
        raise forms.ValidationError(_("The two password fields didn't match."))
    return self.cleaned_data



def signin(request, success_url='', base_template_name='', email_template_name=None):
  site = Site.objects.get(pk=-101)
  if request.method == 'POST':
    form = SigninForm(request.POST)
    if form.is_valid():
      useract = RegistrationProfile.objects.create_inactive_user(username = form.cleaned_data['username'],
        email = form.cleaned_data['email'],
        password = form.cleaned_data["password1"],
        send_email=True,
        email_template='email/activation_email.txt',
      )
      useract.save()
      return redirect(success_url) #reverse('classifieds.adposting.views.notify_post'))
  else:
    form = SigninForm()
  return render_to_response('signin.html', {'form': form, 'base_template': base_template_name, 'site': site}, context_instance=RequestContext(request))
signin = never_cache(signin)

def activate_account(request, activation_key, success_url='', failure_url=''):
  useract = RegistrationProfile.objects.activate_user(activation_key)
  if useract:
    return redirect(success_url)
  else:
    return redirect(failure_url)