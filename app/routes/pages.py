from flask import Blueprint, render_template

bp = Blueprint('pages', __name__, url_prefix='')

@bp.route('/')
def home_page():
  return render_template('index.html')
