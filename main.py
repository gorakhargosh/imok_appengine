import os, datetime

from google.appengine.api import users
from google.appengine.ext import webapp
from google.appengine.ext.webapp import template, util
from google.appengine.ext.webapp.util import login_required
from google.appengine.api import mail

# must import template before importing django stuff
from google.appengine.ext.db import djangoforms

import settings as s
from datastore import *

class IntroHandler(webapp.RequestHandler):
  def get(self):
    template_path = s.template_path('intro.html')
    self.response.headers['Content-Type'] = 'text/html'
    self.response.out.write(template.render(template_path, locals()))

class UserProfileForm(djangoforms.ModelForm):
  phone = db.StringProperty()
  class Meta:
    model = ImokUser
    exclude = ['account']

class RequestHandlerPlus(webapp.RequestHandler):
  def render(self, tmplName, tmplValues, contentType='text/html'):
    self.response.headers['Content-Type'] = contentType
    self.response.out.write(template.render(s.template_path(tmplName), tmplValues))

class CreateProfileHandler(RequestHandlerPlus):
  def getProfile(self):
    # Annoying that we can't use django get_or_create() idiom here.  the
    # appengine equivalent get_or_insert() seems to allow querying by
    # key only.  I also ran into problems trying to wrap this in a
    # transaction.
    user = users.get_current_user()
    profiles = ImokUser.all().filter('account =', user).fetch(1)
    if profiles:
      profile = profiles[0]
    else:
      profile = ImokUser(account=user)
    return profile

  @login_required
  def get(self):
    user = users.get_current_user()
    username = user.nickname()
    logout_url = users.create_logout_url("/")
    profile = self.getProfile()
    form = UserProfileForm(instance=profile)
    self.render('createProfile.html', locals())

  def post(self):
    profile = self.getProfile()
    form = UserProfileForm(data=self.request.POST, instance=profile)
    if form.is_valid():
      # Save the data and redirect to home
      entity = form.save(commit=False)
      entity.added_by = users.get_current_user()
      entity.put()
      self.redirect('/home')
    else:
      # Reprint the form
      user = users.get_current_user()
      username = user.nickname()
      logout_url = users.create_logout_url("/")
      profile = self.getProfile()
      self.render('createProfile.html', locals())

class HomeHandler(webapp.RequestHandler):
  @login_required
  def get(self):

    user = users.get_current_user()
    username = user.nickname()
    logout_url = users.create_logout_url("/")

    template_path = s.template_path('main.html')
    self.response.headers['Content-Type'] = 'text/html'
    self.response.out.write(template.render(template_path, locals()))


class RegisterEmailHandler(webapp.RequestHandler):
  @login_required
  def get(self):
    registeredEmailQuery = RegisteredEmail.all().filter('userName =', users.get_current_user()).order('emailAddress')
    registeredEmailList = registeredEmailQuery.fetch(100)
    
    logout_url = users.create_logout_url("/")

    template_path = s.template_path('register_email.html')
    self.response.headers['Content-Type'] = 'text/html'
    self.response.out.write(template.render(template_path, locals()))


class AddRegisteredEmailHandler(webapp.RequestHandler):
  def post(self):
    if users.get_current_user():
      newEmail = RegisteredEmail()
      newEmail.userName = users.get_current_user()
      success = True
      try:
        # can't not remember to validate email
        tempEmailString = self.request.get('emailAddress')
        newEmail.emailAddress = tempEmailString
        # WHY DOESN'T THIS WORK? I SUCK. -OTAVIO
        if not mail.is_email_valid(tempEmailString):
          success = False
      except:
        success = False
      else:
        if success:
          newEmail.put()
    self.redirect('/email')


class RemoveRegisteredEmailHandler(webapp.RequestHandler):
  def post(self):
    if users.get_current_user():
      removeEmail = self.request.get('emailAddress')
      removeEmailQuery = RegisteredEmail.all().filter('userName =', users.get_current_user()).filter('emailAddress =', removeEmail)
      removeEmailList = removeEmailQuery.get()
      if removeEmailList:
        removeEmailList.delete()
        
    self.redirect('/email')


class SpamAllRegisteredEmailsHandler(webapp.RequestHandler):
  def post(self):
    if users.get_current_user():
      registeredEmailQuery = RegisteredEmail.all().filter('userName =', users.get_current_user()).order('emailAddress')
      addresses = []
      for registeredEmail in registeredEmailQuery:
        addresses.append(registeredEmail.emailAddress)
      
      if (len(addresses) > 0):
        mail.send_mail(sender=users.get_current_user().email(),
                      to=users.get_current_user().email(),
                      bcc=addresses,
                      subject="I'm OK",
                      body="""
Dear Registered User:

This is an auto generated email please do not reply. You are registered to receive emails
regarding the status of USER. This email lets you know they are OK.

Please let us know if you have any questions.

The ImOK.com Team
""")
    self.redirect('/email')
    
    
def main():
  application = webapp.WSGIApplication([
    ('/', IntroHandler),
    ('/home', HomeHandler),
    ('/email', RegisterEmailHandler),
    ('/email/add', AddRegisteredEmailHandler),
    ('/email/remove', RemoveRegisteredEmailHandler),
    ('/email/spam', SpamAllRegisteredEmailsHandler),
    ('/profile/create', CreateProfileHandler),
                                        
  ], debug=True)
  util.run_wsgi_app(application)


if __name__ == '__main__':
  main()
