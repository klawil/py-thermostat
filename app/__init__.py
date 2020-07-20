import os
from flask import Flask, render_template, jsonify
from .helpers import database, thermostat, bme280

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

  @app.route('/api/temp')
  def get_current_temp():
    temp, pressure, humidity = bme280.readBME280All()

    if app.env != 'development' and not bme280.isValid():
      return 'No valid BME280 present', 500

    return jsonify({
      'temp': temp,
      'pressure': pressure,
      'humidity': humidity
    })

  @app.route('/api/state')
  def get_current_state():
    db = database.get_db()

    state = db.execute('SELECT * FROM currentState').fetchone()
    state['rooms'] = db.execute('SELECT * FROM rooms').fetchall()

    return jsonify(state)

  return app
