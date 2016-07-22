import os
import jinja2
import webapp2
from google.appengine.ext import db
import hashlib, hmac
import random, string
import re

# Loading the templates into the Jinja environment
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

# Helper Function
def render_str(template, **params):
	t = jinja_env.get_template(template)
	return t.render(params)

# Signup validation functionalities
USER_RE = re.compile(r"^[a-zA-Z0-9_-]{3,20}$")
def valid_username(name):
	return name and USER_RE.match(name)

PASS_RE = re.compile(r"^.{3,20}$")
def valid_password(pw):
	return pw and PASS_RE.match(pw)

# Hashing functionalities
SECRET = 'wiki'

def make_salt():
	return "".join(random.choice(string.letters) for x in xrange(5))

def make_pw_hash(name, pw, salt = None):
	if not salt:
		salt = make_salt()
	h = hashlib.sha256(name + pw + salt).hexdigest()
	return "%s,%s" % (h,salt)

def valid_pw(name, pw, h):
	salt = h.split(',')[1]
	return h == make_pw_hash(name, pw, salt)

def make_secure_val(s):
	return '%s|%s' % (s, hmac.new(SECRET, s).hexdigest())

def check_secure_val(h):
	val = h.split('|')[0]
	if h == make_secure_val(val):
		return val

# Google DataStore database
class Entries(db.Model):
	title = db.StringProperty(required = True)
	body = db.TextProperty(required = True)
	created = db.DateTimeProperty(auto_now_add = True)

class User(db.Model):
	name = db.StringProperty(required = True)
	pw_hash = db.StringProperty(required = True)

	@classmethod
	def register(cls, username, password):
		pw_hash = make_pw_hash(username, password)
		return User(name = username, pw_hash = pw_hash)

	@classmethod
	def login(cls, name, pw):
		u = User.all().filter('name = ', name).get()
		if u and valid_pw(name, pw, u.pw_hash):
			return u

# Handler Functions
class MainPage(webapp2.RequestHandler):
	def get(self):
		self.response.write(render_str("mainpage.html"))

class SignUp(webapp2.RequestHandler):
	def get(self):
		self.response.write(render_str("signup.html"))

	def post(self):
		have_error = False
		username = self.request.get('username')
		password = self.request.get('password')
		verify = self.request.get('verify')

		params = dict(username = username)

		if not valid_username(username):
			params['error_username'] = "That's not a valid username"
			have_error = True
		if not valid_password(password):
			params['error_password'] = "That's not a valid password"
			have_error = True
		elif password != verify:
			params['error_verify'] = "The passwords do not match"
			have_error = True

		if have_error:
			self.response.write(render_str('signup.html', **params))
		else:
			u = User.all().filter('name =', username).get()
			if u:
				self.response.write(render_str('signup.html', error_username = "That username already exists"))
			else:
				u = User.register(username, password)
				u.put()
				cookie_val = make_secure_val(str(u.key().id()))
				self.response.headers.add_header('Set-cookie', 'uid=%s; Path=/' % cookie_val)
				self.redirect('/welcome')

class Welcome(webapp2.RequestHandler):
	def read_secure_cookie(self, name):
		cookie_val = self.request.cookies.get(name)
		return cookie_val and check_secure_val(cookie_val)

	def initialize(self, *a, **kw):
		webapp2.RequestHandler.initialize(self, *a, **kw)
		uid = self.read_secure_cookie('uid')
		self.user = uid and User.get_by_id(int(uid))

	def get(self):
		self.response.write(render_str('welcome.html', username = self.user.name))

class Login(webapp2.RequestHandler):
	def get(self):
		self.response.write(render_str('login.html'))

	def post(self):
		username = self.request.get('username')
		password = self.request.get('password')

		u = User.login(username, password)
		if u:
			cookie_val = make_secure_val(str(u.key().id()))
			self.response.headers.add_header('Set-cookie', 'uid=%s Path=/' % cookie_val)
			self.redirect('welcome')
		else:
			self.response.write(render_str('login.html', error = "Invalid login"))

class Logout(webapp2.RequestHandler):
	def get(self):
		self.response.delete_cookie('uid')
		self.redirect('/')

# App Handlers
app = webapp2.WSGIApplication([('/', MainPage),
								('/signup', SignUp),
								('/welcome', Welcome),
								('/login', Login),
								('/logout', Logout)
								], debug = True)