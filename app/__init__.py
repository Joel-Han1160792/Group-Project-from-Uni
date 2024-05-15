from flask import Flask

from app.config.helpers import format_date, format_time




app = Flask(__name__)

from app import views_all
from app import views_manager
from app import views_tutor
from app import views_member
app.jinja_env.filters['format_date'] = format_date
app.jinja_env.filters['format_time'] = format_time
