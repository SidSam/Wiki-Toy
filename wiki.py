import os
import jinja2
import webapp2

# Loading the templates into the Jinja environment
template_dir = os.path.join(os.path.dirname(__file__), 'templates')
jinja_env = jinja2.Environment(loader = jinja2.FileSystemLoader(template_dir), autoescape = True)

# Helper Function
def render_str(template, **params):
	t = jinja_env.get_template(template)
	return t.render(params)

# Handler Functions
class MainPage(webapp2.RequestHandler):
	def get(self):
		self.response.write(render_str("mainpage.html"))

# App Handlers
app = webapp2.WSGIApplication([('/', MainPage)
								], debug = True)