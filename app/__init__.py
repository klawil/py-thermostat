import os
from flask import Flask, render_template, jsonify, request
from .helpers import database, thermostat, bme280
from .routes import api, pages

def create_app(test_config=None):
  # Create and configure the app
  app = Flask(__name__, instance_relative_config=True)
  app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=os.path.join(app.instance_path, 'flask.sqlite')
  )

  # Load the configuration
  if test_config is None:
    app.config.from_pyfile('config.py', silent=True)
  else:
    app.config.from_mapping(test_config)

  # Ensure the instance folder exists
  try:
    os.makedirs(app.instance_path)
  except OSError:
    pass

  database.init_app(app)
  thermostat.init_app(app)

  app.register_blueprint(api.bp)
  app.register_blueprint(pages.bp)

  return app
