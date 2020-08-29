import click
from flask.cli import with_appcontext
from .database import get_db
from time import time
from datetime import datetime
from math import floor
import requests

# Return timestamp in ms floored to the nearest minute
def get_current_timestamp():
  return floor(time() / 60) * 60 * 1000

# Update the room temperatures in the DB
def update_rooms():
  db = get_db()
  rooms = db.execute('SELECT * FROM rooms').fetchall()
  room_data = {}

  updateTime = get_current_timestamp()

  for room in rooms:
    room_data[room['name']] = None

    try:
      r = requests.get(
        'http://{}:5000/api/temp'.format(room['ip']),
        timeout=0.5
      )

      resp = r.json()['data']
    except requests.exceptions.Timeout:
      print('Timeout on {}'.format(room['ip']))
      resp = {
        'temp': None
      }
    except:
      print('Error on {}'.format(room['ip']))
      resp = {
        'temp': None
      }

    # Set the temp in the DB to None if there was an error and there hasn't been a new temp in 2
    # minutes
    if (
      resp['temp'] is None and
      (
        room['currentTempTimestamp'] is not None and
        room['currentTempTimestamp'] <= updateTime - (2 * 60 * 1000)
      )
    ):
      print('Update {} to None (no data)'.format(room['ip']))
      db.execute('UPDATE rooms SET currentTemp = NULL, currentTempTimestamp = NULL, lastTemp = ? WHERE name = ?', (
        room['currentTemp'],
        room['name']
      ))
      db.commit()
    elif resp['temp'] is not None:
      print('Update {} to {} (with data)'.format(room['ip'], resp['temp']))
      db.execute('UPDATE rooms SET currentTemp = ?, currentTempTimestamp = ?, lastTemp = ? WHERE name = ?', (
        resp['temp'],
        updateTime,
        room['currentTemp'],
        room['name']
      ))
      db.commit()
      room_data[room['name']] = resp['temp']
    else:
      room_data[room['name']] = room['currentTemp']

  return room_data

def get_room_data():
  db = get_db()
  rooms = db.execute('SELECT * FROM rooms').fetchall()
  room_data = {}

  for room in rooms:
    room_data[room['name']] = room['currentTemp']

  return room_data

# Get the target temperature and room
def get_target_temp():
  db = get_db()
  currentTime = get_current_timestamp()

  # Check for an enabled override first
  override = db.execute('SELECT * FROM overrides').fetchone()
  if override is not None and override['isEnabled'] and override['endsAt'] >= currentTime:
    override['name'] = 'Override'
    return override

  # Get the current minutes from midnight
  now = datetime.now()
  minutesFromMidnight = floor((now - now.replace(hour=0, minute=0, second=0, microsecond=0)).total_seconds() / 60)

  # Check for a schedule
  schedules = db.execute('SELECT * FROM schedule ORDER BY startTime ASC').fetchall()
  schedule = None
  for potentialSchedule in schedules:
    if minutesFromMidnight < potentialSchedule['startTime']:
      break

    schedule = potentialSchedule

  if schedule is None:
    return None

  modeSettings = db.execute('SELECT * FROM modes WHERE name = ?', [
    schedule['mode']
  ]).fetchone()
  if modeSettings is None:
    return None

  return modeSettings

# Return the current state of the system
def get_current_state():
  db = get_db()
  return db.execute('SELECT * FROM currentState').fetchone()

# Get the desired state of the system
def get_desired_state(room_temps, target, current_state):
  desiredState = {
    'ac': False,
    'heat': False,
    'fanLow': True,
    'fanHigh': False,
    'tempMin': None,
    'tempMax': None,
    'targetRoom': None
  }
  if target is None:
    print('No target')
    return desiredState

  if target['name'] == 'Override' and target['tempMin'] is None:
    print('Override')
    target['tempMin'] = current_state['tempMin']
    target['tempMax'] = current_state['tempMax']
    target['targetRoom'] = None
    return target
  elif target['name'] == 'Override':
    target['defaultFan'] = False

  desiredState['tempMin'] = target['tempMin']
  desiredState['tempMax'] = target['tempMax']
  desiredState['targetRoom'] = target['targetRoom']

  if target['targetRoom'] not in room_temps or room_temps[target['targetRoom']] is None:
    for room in room_temps:
      if room_temps[room] is not None:
        print('Switching room from {} to {}'.format(target['targetRoom'], room))
        target['targetRoom'] = room
        break

  if target['targetRoom'] not in room_temps or room_temps[target['targetRoom']] is None:
    print('No rooms with data')
    return desiredState

  currentTemp = room_temps[target['targetRoom']]

  if not target['defaultFan']:
    desiredState['fanLow'] = False

  if currentTemp > (target['tempMax'] + 5):
    desiredState['ac'] = True
    desiredState['fanHigh'] = True
    desiredState['fanLow'] = False
  elif currentTemp > (target['tempMax'] + 1):
    desiredState['ac'] = True
    desiredState['fanLow'] = True
  elif currentTemp < (target['tempMin'] - 1):
    desiredState['heat'] = True
    desiredState['fanLow'] = False
  elif current_state['ac'] and currentTemp > (target['tempMax'] - 1):
    desiredState['ac'] = True
    desiredState['fanLow'] = True
  elif current_state['heat'] and currentTemp < (target['tempMin'] + 1):
    desiredState['heat'] = True
    desiredState['fanLow'] = False

  return desiredState

# Determine if there are changes to the current state
def are_changes_present(current_state, desired_state):
  return (
    current_state['ac'] == desired_state['ac'] and
    current_state['heat'] == desired_state['heat'] and
    current_state['fanLow'] == desired_state['fanLow'] and
    current_state['fanHigh'] == desired_state['fanHigh']
  )

# Implement the changes to the settings
def implement_state(new_state):
  db = get_db()

  # Save the state
  db.execute('UPDATE currentState SET name = ?, ac = ?, heat = ?, fanLow = ?, fanHigh = ?, tempMin = ?, tempMax = ?, targetRoom = ?', (
    new_state['name'],
    new_state['ac'],
    new_state['heat'],
    new_state['fanLow'],
    new_state['fanHigh'],
    new_state['tempMin'],
    new_state['tempMax'],
    new_state['targetRoom']
  ))
  db.commit()

  try:
    global GPIO
    import RPi.GPIO as GPIO
  except:
    print('Failed to import pi library')
    return

  GPIO.setmode(GPIO.BCM)
  GPIO.setwarnings(False)

  pins = db.execute('SELECT * FROM pins').fetchall()
  for pin in pins:
    if pin['name'] in new_state:

      GPIO.setup(pin['pin'], GPIO.OUT)
      if new_state[pin['name']]:
        GPIO.output(pin['pin'], GPIO.LOW)
      else:
        GPIO.output(pin['pin'], GPIO.HIGH)
    else:
      print('{} not found in new state'.format(pin['name']))

def update_thermostat():

  room_data = get_room_data()

  # Determine the target temperature
  target_temp = get_target_temp()

  # Get the current state
  current_state = get_current_state()

  # Determine the desired state of the system
  desired_state = get_desired_state(room_data, target_temp, current_state)
  desired_state['name'] = target_temp['name']

  # Implement the changes
  implement_state(desired_state)

@click.command('update')
@with_appcontext
def update_command():
  """Determine what state the thermostat should be in and update room temperatures"""

  # Update the room temperatures
  room_data = update_rooms()

  update_thermostat()

def init_app(app):
  app.cli.add_command(update_command)
