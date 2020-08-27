from flask import Blueprint, jsonify, request, current_app
from ..helpers import database, thermostat, bme280
import logging

bp = Blueprint('api', __name__, url_prefix='/api')

@bp.route('/temp')
def get_current_temp():
  temp, pressure, humidity = bme280.readBME280All()

  if current_app.env != 'development' and not bme280.isValid():
    return 'No valid BME280 present', 500

  return jsonify({
    'success': True,
    'data': {
      'temp': temp,
      'pressure': pressure,
      'humidity': humidity
    }
  })

@bp.route('/state')
def get_current_state():
  db = database.get_db()

  state = db.execute('SELECT * FROM currentState').fetchone()
  state['rooms'] = db.execute('SELECT * FROM rooms').fetchall()

  return jsonify({
    'success': True,
    'data': state
  })

@bp.route('/state/set', methods=['POST'])
def set_state():
  db = database.get_db()

  db.execute('UPDATE overrides SET isEnabled = 1, endsAt = ?, ac = ?, heat = ?, fanLow = ?, fanHigh = ?, tempMin = ?, tempMax = ?, targetRoom = ?', [
    thermostat.get_current_timestamp() + (1000 * 60 * 60 * 6), # Valid for 6h
    request.form['ac'] == 'true',
    request.form['heat'] == 'true',
    request.form['fanLow'] == 'true',
    request.form['fanHigh'] == 'true',
    None,
    None,
    None
  ])
  db.commit()

  thermostat.update_thermostat()

  return get_current_state()

@bp.route('/state/resume')
def resume_schedule():
  db = database.get_db()

  db.execute('UPDATE overrides SET isEnabled = 0')
  db.commit()

  thermostat.update_thermostat()

  return get_current_state()

@bp.route('/state/temp', methods=['POST'])
def set_state_temp():
  db = database.get_db()

  db.execute('UPDATE overrides SET isEnabled = 1, endsAt = ?, ac = ?, heat = ?, fanLow = ?, fanHigh = ?, tempMin = ?, tempMax = ?, targetRoom = ?', [
    thermostat.get_current_timestamp() + (1000 * 60 * 60 * 6), # Valid for 6h
    None,
    None,
    None,
    None,
    request.form['tempMin'],
    request.form['tempMax'],
    request.form['targetRoom']
  ])
  db.commit()

  thermostat.update_thermostat()

  return get_current_state()

@bp.route('/rooms', methods=('GET', 'POST'))
def current_rooms():
  try:
    db = database.get_db()

    if request.method == 'POST':
      action = request.form['action']
      if action == 'DELETE':
        db.execute('DELETE FROM rooms WHERE ip = ?', [
          request.form['ip']
        ])
      elif action == 'UPDATE':
        db.execute('UPDATE rooms SET name = ? WHERE ip = ?', [
          request.form['name'],
          request.form['ip']
        ])
      elif action == 'CREATE':
        db.execute('INSERT INTO rooms (name, ip) VALUES (?, ?)', [
          request.form['name'],
          request.form['ip']
        ])
      else:
        raise Exception(f"Invalid action '{action}'")

      db.commit()
      return jsonify({
        'success': True
      })

    return jsonify({
      'success': True,
      'data': db.execute('SELECT * FROM rooms').fetchall()
    })
  except Exception as e:
    logging.exception('message')
    return jsonify({
      'success': False,
      'message': str(e)
    })
  except:
    logging.exception('message')
    return jsonify({
      'success': False,
      'message': 'Unknown exception'
    })

@bp.route('/modes', methods=('GET', 'POST'))
def current_modes():
  try:
    db = database.get_db()

    if request.method == 'POST':
      action = request.form['action']
      if action == 'DELETE':
        db.execute('DELETE FROM modes WHERE name = ?', [
          request.form['name']
        ])
      elif action == 'UPDATE':
        db.execute('UPDATE modes SET targetRoom = ?, tempMin = ?, tempMax = ?, defaultFan = ? WHERE name = ?', [
          request.form['targetRoom'],
          request.form['tempMin'],
          request.form['tempMax'],
          request.form['defaultFan'],
          request.form['name']
        ])
      elif action == 'CREATE':
        db.execute('INSERT INTO modes (targetRoom, tempMin, tempMax, defaultFan, name) VALUES (?, ?, ?, ?, ?)', [
          request.form['targetRoom'],
          request.form['tempMin'],
          request.form['tempMax'],
          request.form['defaultFan'],
          request.form['name']
        ])
      else:
        raise Exception(f"Invalid action '{action}'")

      db.commit()
      return jsonify({
        'success': True
      })

    return jsonify({
      'success': True,
      'data': db.execute('SELECT * FROM modes').fetchall()
    })
  except Exception as e:
    logging.exception('message')
    return jsonify({
      'success': False,
      'message': str(e)
    })
  except:
    logging.exception('message')
    return jsonify({
      'success': False,
      'message': 'Unknown exception'
    })
