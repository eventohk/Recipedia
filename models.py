import random
import re
from datetime import datetime, date
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.db import models
from django.utils.translation import ugettext_lazy as _
from tagging.fields import TagField
from tagging.models import Tag, TaggedItem
from tempfile import mkdtemp

SHA1_RE = re.compile('^[a-f0-9]{40}$')

# Drop-down selection
EDU_CHOICES = (
    ('611', 'Post Grad'),
    ('511', 'University'),
    ('411', 'Poly'),
    ('311', 'High School'),
    ('211', 'Primary School'),
    ('111', 'Pre-school'),
)
PAYMHD_CHOICES = (
    ('1', 'Cash'),
    ('2', 'EPS'),
    ('3', 'Octopus'),
    ('4', 'Visa'),
    ('5', 'Master'),
    ('6', 'Dinner'),
    ('7', 'American Exp'),
)
RATE_CHOICES = (
    ('1', 'Good'),
    ('2', 'Average'),
    ('3', 'Bad'),
)
REGION_CHOICES = (
    ('10101', 'Central'),
    ('10102', 'Sheung Wan'),
    ('10201', 'Wan Chai'),
    ('10301', 'Chai Wan'),
    ('10401', 'Aberdeen'),
    ('20501', 'Lantau Island'),
    ('20601', 'Kwai Fong'),
    ('20602', 'Kwai Shing'),
    ('20701', 'Tsuen Wan'),
    ('20801', 'Tuen Man'),
    ('20901', 'Sha Tin'),
    ('21001', 'Yuen Long'),
    ('21101', 'Tai Po'),
    ('21201', 'Northern District'),
    ('21301', 'Shai Kwun'),
    ('21401', 'Yau Tsim Mong'),
    ('21601', 'Kowloon Shing'),
    ('21501', 'Sham Shui Po'),
    ('21701', 'Wong Tai Shin'),
    ('21801', 'Kwun Tong'),
)
REPORT_CHOICES = (
    ('1', 'Infrigement'),
    ('2', 'Abuse'),
    ('3', 'illegal'),
)
CONTACT_CHOICES = (
    ('11', 'Technical Problem'),
    ('12', 'Report Error'),
    ('13', 'Broken Link'),
    ('14', 'Suggestion'),
)

# Model manager section
import StringIO
ACTIVATED = u"ALREADY_ACTIVATED"

def user_uploadpath(instance, filename):
  temp = mkdtemp(dir=settings.MEDIA_ROOT + 'user/temp')
  return temp.replace(settings.MEDIA_ROOT, '') + '/' + filename

def user_uploadthumbnailpath(instance, filename):
  temp = mkdtemp(dir=settings.MEDIA_ROOT + 'user/temp')
  return temp.replace(settings.MEDIA_ROOT, '') + '/' + filename

class AvaliableRecipe(models.Manager):
    def get_query_set(self):
        return super(AvaliableRecipe, self).get_query_set().filter(rstatus__gt=0)

    def user_recipe(self, user):
        return super(AvaliableRecipe, self).get_query_set().filter(ruser=user, rstatus__gt=-1)

class RecipeMgr(models.Manager):
    def get_query_set(self):
        return super(RecipeMgr, self).get_query_set().filter(rstatus__lt=1)

    def activate_recipe(self, user, activation_key):
        """
        borrow from generic registration
        """
        # Make sure the key we're trying conforms to the pattern of a
        # SHA1 hash; if it doesn't, no point trying to look it up in
        # the database.
        if SHA1_RE.search(activation_key):
            try:
                recipe = self.get(activation_key=activation_key)
            except self.model.DoesNotExist:
                return False
            recipe.rstatus = 1
            recipe.activation_key = ACTIVATED
            recipe.modifyat = datetime.datetime.now()
            recipe.save()
            return recipe
        return False

    def with_counts(self , model, limit=None):
        slimit = ''
        if limit is not None:
            slimit = 'limit %s' % limit
        query = """
            SELECT t.id, t.name, COUNT(*)
            FROM %(T_Table)s t, %(TI_Table)s ti
            WHERE t.id = ti.tag_id and ti.content_type_id=%(cType_id)s
            GROUP BY 1, 2
            ORDER BY 3 DESC
            %(setlimit)s""" % {
            'T_Table' : Tag._meta.db_table,
            'TI_Table' : TaggedItem._meta.db_table,
            'cType_id' : ContentType.objects.get(model__exact=model._meta.db_table).pk,
            'setlimit' : slimit
            }
        from django.db import connection
        cursor = connection.cursor()
        cursor.execute(query)
        result_list = []
        for row in cursor.fetchall():
            p = self.model(id=row[0], name=row[1])
            p.count = row[2]
            result_list.append(p)
        return result_list

    def set_share_level(self, sharelevel):
        pass

class ProfileMgr(models.Manager):
    def create_profile(self, user):
        salt = sha_constructor(str(random.random())).hexdigest()[:5]
        activation_key = sha_constructor(salt+user.username).hexdigest()
        return self.create(user=user, receives_newsletter=0,
                           activation_key=activation_key)
    def activate_user(self, activation_key):
        if SHA1_RE.search(activation_key):
            try:
                profile = self.get(activation_key=activation_key)
            except self.model.DoesNotExist:
                return False
            profile.activation_key = ACTIVATED
            profile.save()
            return True
        return False
# Database model section

class Recipe(models.Model):
    PRIVATE = 1
    SHARE_FRIEND = 2
    SHARE_ALL = 3

    name = models.CharField(max_length=75)
    full_photo = models.ImageField(upload_to=user_uploadpath, blank=True)
    thumb_photo = models.ImageField(upload_to=user_uploadthumbnailpath, blank=True)
    tag = TagField()
    rstatus = models.PositiveSmallIntegerField(default=0)
    activation_key = models.CharField(max_length=40, blank=True)
    privacy =  models.PositiveSmallIntegerField(default=SHARE_ALL)
    ruser = models.ForeignKey(User)
    createat = models.DateTimeField(null=True,auto_now_add=True)
    modifyat = models.DateTimeField(null=True,auto_now=True)

    objects = models.Manager()
    avaliable = AvaliableRecipe()
    inactives = RecipeMgr()
    class Admin:
        pass
    class Meta:
        pass
    def __str__(self):
        return self.name
    def rate_recipe(self, rate):
        degree = ['rategoodcount', 'rateavgcount', 'ratebadcount']
        rating = Rating.objects.get(pk=self.id)
        if rating == None:
            data = {'rid': self, degree[rate - 1]: 1}
            rating = Rating.objects.create(**data)
        else:
            if rate == 1:
                rating.rategoodcount = rating.rategoodcount + 1
            elif rate == 2:
                rating.rateavgcount = rating.rateavgcount + 1
            elif rate == 3:
                rating.ratebadcount = rating.ratebadcount + 1
        rating.save()
    def log_visit(self, request):
        if request.user == self.ruser: return
        vl = VisitLog.objects.create(domain = request.META['HTTP_HOST'],
            url = request.get_full_path(),
            user = request.user.username,
            rid = self,
            remotehost = request.META['REMOTE_ADDR'],
            useragent = request.META['HTTP_USER_AGENT'],
            debug = settings.DEBUG
        )
        vl.save()

class Ingredients(models.Model):
    name = models.CharField(max_length=75, unique=True)
    category = models.CharField(max_length=75)
    measure = models.CharField(max_length=15)
    full_photo = models.ImageField(upload_to=user_uploadpath, blank=True)
    thumb_photo = models.ImageField(upload_to=user_uploadthumbnailpath, blank=True)
    createat = models.DateTimeField(null=True,auto_now_add=True)
    modifyat = models.DateTimeField(null=True,auto_now=True)
    class Admin:
        pass
    class Meta:
        pass
    def __str__(self):
        return self.name

class RecipeIngredients(models.Model):
    recipe = models.ForeignKey(Recipe)
    ingredient = models.ForeignKey(Ingredients)
    quantity = models.DecimalField(max_digits=9,decimal_places=2)
    measure = models.CharField(max_length=15)
    class Admin:
        pass
    class Meta:
        pass
    def __str__(self):
        return self.ingredient

class RecipeCookmethods(models.Model):
    recipe = models.ForeignKey(Recipe)
    cookmethod = models.CharField(max_length=250)
    class Admin:
        pass
    class Meta:
        pass
    def __str__(self):
        return self.cookmethod

# from django.contrib.localflavor.us.models import USStateField, PhoneNumberField
class UserProfile(models.Model):
    user = models.OneToOneField(User, primary_key=True)
    receives_newsletter = models.BooleanField()
    activation_key = models.CharField(max_length=40)

class Rating(models.Model):
    rid = models.OneToOneField(Recipe,primary_key=True)
    rategoodcount = models.IntegerField(default=0)
    rateavgcount = models.IntegerField(default=0)
    ratebadcount = models.IntegerField(default=0)
    createat = models.DateTimeField(null=True,auto_now_add=True)
    modifyat = models.DateTimeField(null=True,auto_now=True)
    class Admin:
        pass
    class Meta:
        # db_table = 'rating'
        pass
    def getRateCount(self):
        return self.rategoodcount + self.rateavgcount + self.ratebadcount
    total_rate_count = property(getRateCount)
    def __str__(self):
        return '%s has %d polled with %d good; %d average; %d bad' % (self.adid, self.rategoodcount + self.rateavgcount + self.ratebadcount, self.rategoodcount, self.rateavgcount, self.ratebadcount)

class Comment(models.Model):
    rid = models.ForeignKey(Recipe)
    comment = models.TextField()
    rating = models.PositiveSmallIntegerField(default=0)
    parentid = models.ManyToManyField("self")
    # rstatus = models.PositiveSmallIntegerField(null=True,default=0)
    # confirmhash = models.CharField(max_length=128)
    ruser = models.ForeignKey(User)
    createat = models.DateTimeField(null=True,auto_now_add=True)
    modifyat = models.DateTimeField(null=True,auto_now=True)
    def Rate_str(seif):
        p = ['Not Rate Yet','Good','Average','Bad']
        return p[self.rating]
    class Admin:
        pass
    class Meta:
        # db_table = 'comment'
        pass
    def __str__(self):
        return '%s comment' % self.rid
    def save(self, force_insert=False, force_update=False):
        if ((self.rating > 0) and (self.rating < 4)): #and (self.rstatus > 0):
            # from datetime import datetime
            serialrec = Rating.objects.get(pk=self.rid)
            if self.rating == 1:
                serialrec.rategoodcount += 1
            elif self.rating == 2:
                serialrec.rateavgcount += 1
            elif self.rating == 3:
                serialrec.ratebadcount += 1
            serialrec.modifyat = datetime.datetime.now()
            serialrec.save()
        # if self.rstatus == 0:
            # send_confirmation(self.ruser, '/Confirm/?type=cm&id=' + self.adid + '&prx=' + self.confirmhash, '/Confirm/?type=cm&id=' + self.adid + '&prx=' + self.confirmhash)
        super(Comment, self).save(force_insert, force_update)

class VisitLog(models.Model):
    domain = models.CharField(max_length=100)
    url = models.CharField(max_length=2048)
    user = models.CharField(max_length=2048)
    rid = models.IntegerField()
    remotehost = models.CharField(max_length=100)
    useragent = models.CharField(max_length=1000)
    debug = models.BooleanField()
    createat = models.DateField(auto_now_add=True)

class UserReport(models.Model):
    reporttype = models.PositiveSmallIntegerField()
    comment = models.TextField()
    rstatus = models.PositiveSmallIntegerField(null=True,default=0)
    ruser = models.CharField(max_length=75)
    createat = models.DateTimeField(null=True,auto_now_add=True)
    modifyat = models.DateTimeField(null=True,auto_now=True)
    class Admin:
        pass
    class Meta:
        # db_table = 'userreport'
        pass
    def __str__(self):
        return '%s comment' % self.comment
