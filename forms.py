# from django.core.context_processors import csrf
# from django.core.files.uploadedfile import SimpleUploadedFile
# from django.core.urlresolvers import reverse
# from django.forms.models import inlineformset_factory
# from os import remove, path, mkdir
# from PIL import Image
# from tagging.forms import TagField
import shutil
# import tempfile
from datetime import datetime, date, timedelta
from django import forms
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.forms import ModelForm, Textarea
from django.forms.widgets import RadioSelect, HiddenInput, Select
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import render_to_response, get_object_or_404
from django.template import Context, loader, RequestContext
from recipedia.models import Recipe, Ingredients, RecipeIngredients, RecipeCookmethods
from tagging.forms import TagField
# Hidden required fields should override it as "required=False" first and fill up custom value in views or unlying model
# To pass form validation, required field(s) in derived model shoul override as "required=False" here and set custom data in form save or model save method

class TermAndConditionForm(forms.Form):
    Agreed = forms.BooleanField()

class RecipeForm(ModelForm):
    name = forms.CharField(max_length=75)
    tag = TagField()
    full_photo = forms.ImageField(required=False)
    thumb_photo = forms.ImageField(required=False)
    activation_key = forms.CharField(max_length=40,required=False)
    # privacy =  models.PositiveSmallIntegerField(default=PRIVATE)
    class Meta:
        model = Recipe
        fields = ('name', 'tag','full_photo', 'thumb_photo', 'activation_key')
    class Media:
        js = (
            '/scrp/jquery.js',
            # 'scrp/tiny_mce/tiny_mce.js',
        )

class IngredientForm(ModelForm):
    name = forms.CharField(max_length=75)
    category = forms.CharField(max_length=75)
    measure = forms.CharField(max_length=15)
    full_photo = forms.ImageField(required=False)
    thumb_photo = forms.ImageField(required=False)
    class Meta:
        model = Ingredients
        fields = ('name','category','measure','full_photo', 'thumb_photo')
    class Media:
        js = (
            '/scrp/jquery.js',
        )

class RecipeCookmethodForm(ModelForm):
    recipe = forms.IntegerField()
    cookmethod = forms.CharField(max_length=250, widget = \
            Textarea(attrs={'class': 'cooking', 'cols': 50, 'rows': 1})
            )
    class Meta:
        model = RecipeCookmethods
    class Media:
        js = (
            '/scrp/jquery.js',
        )

class RecipeIngredientForm(ModelForm):
    recipe = forms.IntegerField()
    ingredient = forms.IntegerField(widget=HiddenInput())
    ingrdname = forms.CharField(max_length=75)
    quantity = forms.DecimalField(max_digits=9,decimal_places=2)
    measure = forms.CharField(max_length=15)
    class Meta:
        model = RecipeIngredients
    class Media:
        js =  ('/scrp/jquery.js', '/scrp/jquery-ui.js', '/scrp/inc/jquery.hoverIntent.min.js', '/scrp/inc/jquery.metadata.js', '/scrp/inc/jquery.mb.flipText.js', '/scrp/inc/mbExtruder.js',
        )
        css = {'all': ('/scrp/css/mbExtruder.css',            
        ), 'screen': (settings.MEDIA_URL + 'theme/ui-lightness/ui-lightness.css', )}
    def clean_ingredient(self):
        data = self.cleaned_data['ingredient']
        return Ingredients.objects.get(pk=data)
    
#@login_required(login_url='/dialog/accounts/login/')
def add_ingredient(request, nondialog = False):
    if request.method == 'POST':
        form = IngredientForm(request.POST)
        if form.is_valid():
            form.save()
            form = Ingredients.objects.get(name=form.cleaned_data['name'])
            return render_to_response('view_ingredient.html', {'form': form}, context_instance=RequestContext(request))
    else:
        form = IngredientForm()
    return render_to_response('new_ingredient.html', {'form': form}, context_instance=RequestContext(request))

# -----------------------------------------------------------------------------------
# backup code for possible usage
@login_required
def add_recipe(request):
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES)
        if form.is_valid():            
            rp = form.save(commit=False)
            data = form.cleaned_data
            rp.activation_key = activation_key(request)
            rp.ruser = request.user
            rp.save()
            create_thumb(rp)
            return HttpResponseRedirect(reverse('recipedia.views.edit', args=[rp.pk]))
    else:
        form = RecipeForm()
    return render_to_response('new_recipe.html', {'form': form}, context_instance=RequestContext(request))

