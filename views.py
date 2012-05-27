"""
  $Id$
"""
# try:
    # from django.core.context_processors import csrf
# except ImportError:
    # continue
# from adform import AdForm
# from django.core.context_processors import csrf
from django import forms
from django.conf import settings
from django.contrib.auth import REDIRECT_FIELD_NAME
from django.contrib.auth.decorators import login_required
from django.core.mail import EmailMessage
from django.core.paginator import Paginator, InvalidPage
from django.core.urlresolvers import reverse
from django.forms.models import inlineformset_factory
from django.http import HttpResponseRedirect, HttpResponse, Http404, HttpResponseForbidden
from django.shortcuts import render_to_response, get_object_or_404
from django.template import Context, loader, RequestContext
from django.utils.datastructures import SortedDict
from django.utils.translation import ugettext as _
from forms import RecipeForm, RecipeCookmethodForm, RecipeIngredientForm
from models import user_uploadpath, Recipe, Ingredients, RecipeIngredients, RecipeCookmethods
import shutil
import os
from os import mkdir
# from search import *
import datetime
import random
# if settings.ENV == 'live':
  # from iportal.classifieds import *  
# else:
  # from classifieds import *

ITEM_PER_PAGE = getattr(settings, 'ITEM_PER_PAGE', 10)

from PIL import Image
import string

def activation_key(request):
    import random
    from django.utils.hashcompat import sha_constructor
    salt = sha_constructor(str(random.random())).hexdigest()[:5]
    return sha_constructor(salt+request.user.username).hexdigest()
    
def create_thumb(recipe):    
    size = 40
    if recipe.full_photo == None: return
    if recipe.full_photo.path.find(user_uploadpath(recipe, '')) > -1: return
    tpath, tname = os.path.split(recipe.full_photo.path)
    npath = 'user/%s/%s/' % (recipe.ruser.id, recipe.id)
    shutil.move(tpath, settings.MEDIA_ROOT + npath)
    recipe.full_photo = npath + tname
    image = Image.open(settings.MEDIA_ROOT + npath + tname)
    wsize, hsize = image.size
    ratio = max(wsize/size, hsize/size)
    if ratio > 1:
        if image.mode not in ('L', 'RGB', 'RGBA'):
            image = image.convert('RGB')
        image2 = image
        image2.thumbnail([wsize/ratio, hsize/ratio], Image.ANTIALIAS)
    else:
        image2 = image
        image2.thumbnail([wsize, hsize], Image.ANTIALIAS)
    format = 'JPEG'    
    nname = tname.split('.')[:-1]
    if not os.path.exists(settings.MEDIA_ROOT + npath + 'thumb/'):
        mkdir(settings.MEDIA_ROOT + npath + 'thumb/')
    image2.save(settings.MEDIA_ROOT + npath + 'thumb/' + nname[0] + '.jpg', format)
    recipe.thumb_photo = npath + 'thumb/' + nname[0] + '.jpg'
    recipe.save()

def context_sortable(request, obj, perpage=ITEM_PER_PAGE):
  order = '-'
  sort = 'modifyat'
  page = 1
  pagesetnum = 5

  perpage = int(request.GET.get('perpage', perpage))
  if request.GET.get('order', 'desc') == 'desc':
    order = '-'
  else:
    order = ''
  page = int(request.GET.get('page', page))
  if request.GET.get('sort', sort) in ['modifyat', 'name']:
    sort = request.GET.get('sort', sort)
  ads_sorted = obj.extra(order_by=[order + sort])

  pager = Paginator(ads_sorted, perpage)
  page_obj = {}
  try:
    page_obj['pagenum'] = min(page, pager.num_pages)
    pageset = int(page_obj['pagenum'] / pagesetnum)
    page_obj['pagelist'] = range((perpage*pageset+1),(min((perpage*(pageset+1)), pager.num_pages)+1))    
    page_obj['page'] = pager.page(page_obj['pagenum'])
    page_obj['sort'] = sort
    page_obj['order'] = request.GET.get('order', 'desc')
    page_obj['no_results'] = False
  except InvalidPage:
    page_obj['page'] = {'object_list': False}
    page_obj['no_results'] = True
  return page_obj

def index(request):
  try:
    del request.session['manage']
    del request.session['search']
  except KeyError:
    pass
  rp = Recipe.objects.all()
  context = context_sortable(request, rp)
  # write_visitlog(request)
  return render_to_response('index.html', context, context_instance=RequestContext(request))

@login_required
def mine(request):
  try:
    del request.session['search']
  except KeyError:
    pass
  obj = Recipe.avaliable.user_recipe(request.user)
  context = context_sortable(request, obj)
  context['sortfields'] = ['id', 'category', 'created_on', 'posts_on']
  request.session['manage'] = 1
  context.update({'act_post_ad': True, 'act_manage_ad': 3, 'ismanage': True,
  })
  return render_to_response('index.html', context, context_instance=RequestContext(request))

@login_required
def delete(request, rpID):
    # find the ad, if available
    rp = get_object_or_404(Recipe, pk=rpID, ruser=request.user)
    rp.rstatus = -1
    rp.save()
    # create status message
    request.user.message_set.create(message='obj deleted.')
    temp = request.get_full_path()
    return HttpResponseRedirect(reverse('classifieds.adposting.views.mine') + temp.replace(request.path,''))

@login_required
def create(request):
  # the 1st step of 3 phases recipe creation
    if not request.user.is_active:
        HttpResponseForbidden()
    if request.method == 'POST':
        form = RecipeForm(request.POST, request.FILES)
        if form.is_valid():            
            rp = form.save(commit=False)
            data = form.cleaned_data
            rp.activation_key = activation_key(request)
            rp.ruser = request.user
            rp.save()
            create_thumb(rp)
            return HttpResponseRedirect(reverse('recipedia.views.create_edit', args=[rp.pk]))
    else:
        form = RecipeForm()
    return render_to_response('new_recipe.html', {'form': form}, context_instance=RequestContext(request))

@login_required
def edit(request, rpID):
  rp = get_object_or_404(Recipe, pk=rpID, ruser=request.user)
  if not request.user.is_active:
    HttpResponseForbidden()
  if request.method == 'POST':
    form = RecipeForm(request.POST, request.FILES)
    if form.is_valid():            
        rp = form.save()
        create_thumb(rp)
        return HttpResponseRedirect(reverse('recipedia.views.create_edit', args=[rp.pk]))
  else:
    form = RecipeForm()
  return render_to_response('new_recipe.html', {'form': form}, context_instance=RequestContext(request))

def view(request, rpID):
# find the ad, if available
# ismanage = request.session.has_key('manage')
# granteduser = request.user.is_authenticated() and request.user.is_active
# if ismanage:
# if granteduser:
    rp = get_object_or_404(Recipe, pk=rpID)
    ingrdset = RecipeIngredients.objects.filter(recipe=rp.id)
    mthdset = RecipeCookmethods.objects.filter(recipe=rp.id)
    # if rp.ruser != request.user:
    # raise HttpResponseForbidden()
    # else:
    # raise HttpResponseForbidden()
    context = {'ingrds': ingrdset, 'mthds': mthdset, 'recipe': rp, 'thum': settings.MEDIA_ROOT + 'user/'}
# if context['ismanage']:
# context.update({'act_manage_ad': 3})
# elif granteduser:
# context.update({'act_manage_ad': 2})
# write_visitlog(request, ad.id)
    return render_to_response('view_recipe.html', context, context_instance=RequestContext(request))

@login_required
def create_edit(request, rpID):
  # the 2nd step of 3 phases recipe creation
  rp = get_object_or_404(Recipe, pk=rpID, ruser=request.user)
  init_item = 5
  IngrdFormSet = inlineformset_factory(Recipe, RecipeIngredients, form=RecipeIngredientForm, extra=init_item, fields=('ingredient', 'quantity', 'measure'), can_delete=True)
  # IngrdFormSet.clean = clean_ing
  mthdFormSet = inlineformset_factory(Recipe, RecipeCookmethods, form=RecipeCookmethodForm, extra=init_item, can_delete=True)
  if request.method == 'POST':
    ingrdformset = IngrdFormSet(request.POST, instance=rp)
    mthdformset = mthdFormSet(request.POST, instance=rp)
    if ingrdformset.is_valid() and mthdformset.is_valid():
      ingrdformset.save()
      mthdformset.save()
      return HttpResponseRedirect(reverse('recipedia.views.view', args=[rp.pk]))
  else:
    ingrdformset = IngrdFormSet(instance=rp)
    mthdformset = mthdFormSet(instance=rp)
  gmedia = ingrdformset.forms[0].media + mthdformset.forms[0].media
  ingrdlist1 = Ingredients.objects.values('id','name','category','measure').extra(order_by=['category'])[:20]

  return render_to_response('edit_recipe.html', \
    {'ingrds': ingrdformset, 'mthds': mthdformset, 'recipe': rp, 'ingrdlist1': ingrdlist1, 'grpmedia': gmedia}, context_instance=RequestContext(request))

# -----------------------------------------------------------------------------------
# backup code for possible usage
def clean_adimageformset(self):
    max_size = self.instance.category.images_max_size
    logocount = 0
    for form in self.forms:
      try:
        if not hasattr(form.cleaned_data['full_photo'], 'file'):
          continue
        if form.cleaned_data['logo']:
          logocount += 1
      except:
        continue

      if form.cleaned_data['full_photo'].size > max_size:
        raise forms.ValidationError(_('Maximum image size is ' + str(max_size/1024) + ' KB'))
      if logocount > 1:
        raise forms.ValidationError(_(u'Only ONE logo could be defined.'))

      im = Image.open(form.cleaned_data['full_photo'].file)
      basepath = 'd:/uploadtest/'
      destination = open(basepath + 'log.txt', 'ab+')
      destination.write('%s (%s)\n' % (im.size,im.format))
      destination.close()
      if self.instance.category.images_allowed_formats.filter(format=im.format.lower()).count() == 0:
        raise forms.ValidationError(_('Your image must be in one of the following formats: ') + string.join(self.instance.category.images_allowed_formats.values_list('format', flat=True), ','))

@login_required
def create_preview(request, adId):
  ad = get_object_or_404(Ad, pk=adId, active=False, user=request.user)

  return render_to_response('adposting/category/' + ad.category.template_prefix + '/preview.html', {'ad': ad, 'create': True}, context_instance=RequestContext(request))

@login_required
def view_bought(request, adId):
  request.user.message_set.create(message='Your ad has been successfully posted. Thank You for Your Order!')
  return view(request, adId)

@login_required
def create_in_category(request, categoryId):
  # validate categoryId
  category = get_object_or_404(Category, pk=categoryId)
  ad = Ad.objects.create(category=category, user=request.user, expires_on=datetime.datetime.now(), active=False)
  ad.save()
  return create_edit(request, ad.pk)

def search(request):
  # list categories available and send the user to the search_in_category view
  if request.method == 'GET':
    if request.GET.has_key('latest'):
      param = {'active': 1, 'status__gt': 0, 'posts_on__gte': datetime.datetime.now() - datetime.timedelta(days=2)}
      searchp = '&latest'
    elif request.GET.has_key('query') and request.GET.get('query', '') != '':
      param = {'active': 1, 'status__gt': 0, 'title__icontains': request.GET.get('query')}
      # ads = Ad.objects.filter(active=1, status__gt=0, title__icontains=request.GET.get('query')) #, active=True
      searchp = '&query=%s' % request.GET.get('query')
    else:
      return render_to_response('adposting/category_choice.html', {'categories': Category.objects.all(), 'type': 'search'}, context_instance=RequestContext(request))
    if request.session.has_key('manage'):
      param.pop('active')
    ads = Ad.objects.filter(**param)
    context = context_sortable(request, ads)
    if request.session.has_key('manage'):
      context['sortfields'] = ['ad_id', 'title', 'category', 'posts_on', 'create_on']
      context.update({'act_post_ad': True, 'act_manage_ad': 2,
      'searchparam': searchp,
      })
      return render_to_response('adposting/manage.html', context, context_instance=RequestContext(request))
    else:
      context['sortfields'] = ['title', 'category', 'posts_on']
      context.update({'act_post_ad': True, 'act_manage_ad': 2,
      'searchparam': searchp,
      })
      return render_to_response('adposting/index.html', context, context_instance=RequestContext(request))
  return render_to_response('adposting/category_choice.html', {'categories': Category.objects.all(), 'type': 'search'}, context_instance=RequestContext(request))

def search_in_category(request, categoryId):
  try:
    del request.session['search']
  except KeyError:
    pass

  return search_results(request, categoryId)

def prepare_sforms(fields, fields_left, post=None):
  sforms = []
  select_fields = {}
  for field in fields:
    if field.field_type == Field.SELECT_FIELD:  # is select field
      # add select field
      options = field.options.split(',')
      choices = zip(options, options)
      choices.insert(0, ('', 'Any',))
      form_field = forms.ChoiceField(label=field.label, required=False, help_text=field.help_text + u'\nHold ctrl or command on Mac for multiple selections.', choices=choices, widget=forms.SelectMultiple)
      # remove this field from fields_list
      fields_left.remove( field.name )
      select_fields[field.name] = form_field

  sforms.append(SelectForm.create(select_fields, post))

  for sf in searchForms:
    f = sf.create(fields, fields_left, post)
    if f != None:
      sforms.append(f)

  return sforms

def search_results(request, categoryId):
  cat = get_object_or_404(Category, pk=categoryId)
  fields = list(cat.field_set.all())
  fields += list(Field.objects.filter(category=None))
  fieldsLeft = [field.name for field in fields]
  ismanage = request.session.has_key('manage')
  if request.method == "POST" or request.session.has_key('search'):
    if ismanage and request.user.is_authenticated() and request.user.is_active:
      adfilter = {'user': request.user, 'status__gt': 0}
    else:
      adfilter = {'active': True, 'status__gt': 0, 'expires_on__gt': datetime.datetime.now()}
    ads = cat.ad_set.filter(**adfilter)
    # A request dictionary with keys defined for all
    # fields in the category.
    post = {}
    if request.session.has_key('search'):
      post.update(request.session['search'])
    else:
      post.update(request.POST)

    sforms = prepare_sforms(fields, fieldsLeft, post)

    isValid = True
    #validErrors = {}
    for f in sforms:
      #TODO: this assumes the form is not required (it's a search form after all)
      if not f.is_valid() and not f.is_empty():
        isValid = False
        #validErrors.update(f.errors)

    if isValid:
      if request.method == 'POST':
        request.session['search'] = {}
        request.session['search'].update(request.POST)
        return HttpResponseRedirect(reverse('classifieds.adposting.views.search_results', args=[categoryId]))

      for f in sforms:
        ads = f.filter(ads)

      if ads.count() == 0:
        return render_to_response('adposting/list.html', {'no_results':True, 'category':cat}, context_instance=RequestContext(request))
      else:
        context = context_sortable(request, ads)
        if ismanage:
          context['sortfields'] = ['id', 'title', 'created_on', 'posts_on']
        else:
          context['sortfields'] = ['title', 'posts_on']
        context['category'] = cat
        return render_to_response('adposting/list.html', context, context_instance=RequestContext(request))
  else:
    sforms = prepare_sforms(fields, fieldsLeft)

  return render_to_response('adposting/search.html', {'forms':sforms, 'category':cat}, context_instance=RequestContext(request))

# from forms import CheckoutForm, SubscribeForm, UserContactForm, UserReportForm
# from paypal.standard.forms import PayPalPaymentsForm

def checkout(request, adId):
  ad = get_object_or_404(Ad, pk=adId)
  if request.method == 'POST':
    form = CheckoutForm(request.POST)
    if form.is_valid():
      total = 0
      pricing = Pricing.objects.get(pk=form.cleaned_data["pricing"])
      total += pricing.price
      pricing_options = []
      for pk in form.cleaned_data["pricing_options"]:
        option = PricingOptions.objects.get(pk=pk)
        pricing_options.append(option)
        total += option.price

      # create Payment object
      billId = gen_billid(adId)
      confirmhash = gethash(billId)
      payment = Payment.objects.create(ad=ad, pricing=pricing, bill_id=billId, confirmhash=confirmhash)
      
      for option in pricing_options:
        payment.options.add(option)

      payment.save()

      ad.save()
      # send email when done
      # 1. render context to email template
      email_template = loader.get_template('adposting/email/posting.txt')
      context = Context({'ad': ad, 'payment': payment, 'site': Site.objects.get(pk=APP_ENV['SITE_ID'])})
      email_contents = email_template.render(context)
      # 2. send email
      send_mail(_('Your ad will be posted shortly.'), email_contents, settings.FROM_EMAIL, [ad.user.email], fail_silently=False)

      # item_name = _('Your ad on ') + Site.objects.get(pk=SITE_ID).name
      # paypal_values = {'amount': total, 'item_name': item_name, 'item_number': payment.pk, 'quantity': 1}
      # if settings.DEBUG:
        # paypal_form = PayPalPaymentsForm(initial=paypal_values).sandbox()
      # else:
        # paypal_form = PayPalPaymentsForm(initial=paypal_values).rander()
      return HttpResponseRedirect(reverse('classifieds_post_complete'))
      # return render_to_response('adposting/paypal.html', {'form': paypal_form}, context_instance=RequestContext(request))
  else:
    form = CheckoutForm()

  return render_to_response('adposting/checkout.html', {'ad': ad, 'form': form}, context_instance=RequestContext(request))

def pricing(request):
  return render_to_response('adposting/pricing.js', {'prices': Pricing.objects.all(), 'options': PricingOptions.objects.all()}, context_instance=RequestContext(request))

# def notify_complete(request):
  # return render_to_response('adposting/notify_complete.html', {}, context_instance=RequestContext(request))

# def notify(request):
  # if request.method == 'POST': #form was submitted
    # form = SubscribeForm(request.POST)
    # if form.is_valid():
      # create user profile
      # user = User.objects.create_user(form.cleaned_data["email_address"], form.cleaned_data["email_address"])
      # user.first_name = form.cleaned_data["first_name"]
      # user.last_name = form.cleaned_data["last_name"]
      # user.is_active = False
      # user.save()
      # profile = UserProfile.objects.create(user=user, receives_new_posting_notices=True, receives_newsletter=True)
      # profile.save()

      # return HttpResponseRedirect(reverse(notify_complete))
  # else:
    # form = SubscribeForm()

  # return render_to_response('adposting/notify.html', {'form': form}, context_instance=RequestContext(request))

# def notify_post(request):
  # return render_to_response('adposting/newpostnotice.html', context_instance=RequestContext(request))

#--- custome veiw and function ---#

def confirm(request, adid, hashcode):
  payment = get_object_or_404(Payment, ad=adid, confirmhash=hashcode)
  if payment.paypal_id == None:
    ad = get_object_or_404(Ad, pk=adid)
    pricing = Pricing.objects.get(pk=payment.pricing_id)
    postperiod = datetime.timedelta(days=pricing.length)
    ad.posts_on = payment.startat = datetime.datetime.now()
    payment.endat = datetime.datetime.now() + postperiod
    if (ad.expires_on == None) or (ad.expires_on < datetime.datetime.now()):
      ad.expires_on = datetime.datetime.now() + postperiod
      # datetime.datetime.now()
      Msg = notice(noticetype='activate')
    else:
      # paystart = ad.expire
      # ad.expire = ad.expire + postperiod
      ad.expires_on = ad.expires_on + postperiod
      # payment.startat = paystart
      # payment.endat = paystart + postperiod
      Msg = notice(noticetype='renew')
    ad.active = 1
    ad.save()
    payId = random.randint(-2147483648,2147483647)
    # for p in payment:
    payment.paypal_id = payId
    payment.save()
  else:
    Msg = notice(noticetype='reactivate')
  # return HttpResponseRedirect(reverse(notify_complete))
  Msg.update({'act_post_ad': True})
  if request.user.is_authenticated() and request.user.is_active:
    Msg.update({'act_manage_ad': 3})
  return render_to_response('adposting/notify_confirmposting.html', Msg, context_instance=RequestContext(request))

def info(request, pagename):
  if request.user.is_authenticated() and request.user.is_active:
    act_manage_ad = 2
  else:
    act_manage_ad = 0
  return render_to_response('adposting/%s' % pagename, {'act_manage_ad': act_manage_ad, 'act_post_ad': True}, context_instance=RequestContext(request))

@login_required
def contactus(request):
  site_email = {u'l1': 'notify@skyreal.com', u'l2': 'notify@skyreal.com', u'l3': 'notify@skyreal.com', u'l4': 'notify@skyreal.com'}
  if request.method == 'POST':
    form = UserContactForm(request.POST)
    if form.is_valid():
      email_template = loader.get_template('adposting/email/usercontact.html')
      a = dict(form.CONTACT_CHOICES)
      context = Context({'type': a[form.cleaned_data["reporttype"]], 'content' : form.cleaned_data["content"], 'request' : request})
      email_contents = email_template.render(context)
      email = EmailMessage('User Report - %s' % context['type'], email_contents, settings.FROM_EMAIL, [site_email[form.cleaned_data["reporttype"]]])
      email.content_subtype = "html"
      email.send()
      Msg = notice(noticetype='reportus')
      return render_to_response('adposting/notify_confirmposting.html', Msg, context_instance=RequestContext(request))
  else:
    form = UserContactForm()
  if request.user.is_authenticated() and request.user.is_active:
    act_manage_ad = 2
  else:
    act_manage_ad = 0
  return render_to_response('adposting/usercontact.html', {'form': form,'act_manage_ad': act_manage_ad, 'act_post_ad': True}, context_instance=RequestContext(request))

@login_required
def reportus(request, adId):
  site_email = {u'1': 'notify@skyreal.com', u'2': 'notify@skyreal.com', u'3': 'notify@skyreal.com'}
  if request.method == 'POST':
    form = UserReportForm(request.POST)
    if form.is_valid():
      email_template = loader.get_template('adposting/email/usercontact.html')
      a = dict(form.REPORT_CHOICES)
      context = Context({'complaint': True, 'adid': adId, 'type': a[form.cleaned_data["reporttype"]], 'content' : form.cleaned_data["content"], 'request' : request})
      email_contents = email_template.render(context)
      email = EmailMessage('User Complaint - %s' % context['type'], email_contents, settings.FROM_EMAIL, [site_email[form.cleaned_data["reporttype"]]])
      email.content_subtype = "html"
      email.send()
      Msg = notice(noticetype='reportus')
      return render_to_response('adposting/notify_confirmposting.html', Msg, context_instance=RequestContext(request))
  else:
    form = UserReportForm()
  if request.user.is_authenticated() and request.user.is_active:
    act_manage_ad = 2
  else:
    act_manage_ad = 0
  return render_to_response('adposting/usercontact.html', {'form': form,'act_manage_ad': act_manage_ad, 'act_post_ad': True}, context_instance=RequestContext(request))

def notice(noticetype, Message=''):
  MsgList = {
    'account_fail': {'type' : 1031, 'content' : _(u'Your registration was failed.<br>Please contact our customer service for assisstance.')},
    'account_register': {'type' : 1001, 'content' : _(u'Thanks for joining us. <br>Please follow the instruction on confirmation email to activate your account.')},
    'account_success': {'type' : 1001, 'content' : _(u'Thanks for joining us. <br>Your account has been activated.<br>Please login for your new posting.')},
    'activate': {'type' : 1001, 'content' : _('Your ad has been confirmed and activated.')},
    'confirm_delete': {'type' : 1001, 'content' : _(u'Your recipe has been deleted!.')},
    'forbiden_action': {'type' : 1031, 'content' : _(u'Your action is forbiden!.')},
    'post_complete': {'type' : 1001, 'content' : _(u'Thanks for using our service. <br>Please follow the instruction on confirmation email to activate your post.')},
    'reactivate': {'type' : 1011, 'content' : _('Your ad has been confirmed. Please check your ad content to detect any possible infringement.')},
    'renew': {'type' : 1001, 'content' : _('Your ad has been confirmed and renewed.')},
    'reportus': {'type' : 1001, 'content' : _(u'Thanks for your invalue comment on our service.')},
  }
  Msg = MsgList[noticetype]
  if Message != '': Msg['content'] = Message
  return Msg

def gen_billid(adId):
  return 'B%02d%02d-%d-%03d' % (datetime.date.today().year - 2000, datetime.date.today().month, int(adId), random.randint(1,999))
  