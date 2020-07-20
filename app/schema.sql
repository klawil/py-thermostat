DROP TABLE IF EXISTS rooms;
DROP TABLE IF EXISTS modes;
DROP TABLE IF EXISTS schedule;
DROP TABLE IF EXISTS overrides;
DROP TABLE IF EXISTS currentState;
DROP TABLE IF EXISTS pins;

CREATE TABLE rooms (
  name TEXT PRIMARY KEY,
  ip TEXT UNIQUE NOT NULL,
  currentTemp INTEGER,
  currentTempTimestamp INTEGER,
  lastTemp INTEGER
);

CREATE TABLE modes (
  name TEXT PRIMARY KEY,
  targetRoom TEXT NOT NULL,
  tempMin INTEGER NOT NULL,
  tempMax INTEGER NOT NULL,
  defaultFan BOOLEAN NOT NULL
);

CREATE TABLE schedule (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  startTime INTEGER NOT NULL, -- Start time in minutes from midnight
  mode TEXT NOT NULL
);

CREATE TABLE overrides (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  isEnabled BOOLEAN NOT NULL,
  endsAt INTEGER,
  targetRoom TEXT,
  minTemp INTEGER,
  maxTemp INTEGER,
  defaultFan BOOLEAN
);

CREATE TABLE currentState (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  ac BOOLEAN NOT NULL,
  heat BOOLEAN NOT NULL,
  fanLow BOOLEAN NOT NULL,
  fanHigh BOOLEAN NOT NULL
);

CREATE TABLE pins (
  pin INTEGER PRIMARY KEY,
  name TEXT NOT NULL
);

INSERT INTO rooms (name, ip) VALUES
('Living Room', '127.0.0.1'),
('Bedroom', '192.168.85.8');

INSERT INTO modes (name, targetRoom, tempMin, tempMax, defaultFan) VALUES
('Sleeping', 'Bedroom', 16, 20, TRUE),
-- ('Awake', 'Bedroom', 16, 20, TRUE);
('Awake', 'Living Room', 16, 20, TRUE);

INSERT INTO schedule(startTime, mode) VALUES
(0, 'Sleeping'), -- Midnight
(330, 'Awake'), -- 0530
(1200, 'Sleeping'); -- 2000

INSERT INTO overrides (isEnabled) VALUES (FALSE);

INSERT INTO currentState (name, ac, heat, fanLow, fanHigh) VALUES
('Override', FALSE, FALSE, FALSE, FALSE);

INSERT INTO pins (pin, name) VALUES
(17, 'ac'),
(27, 'heat'),
(22, 'fanLow'),
(23, 'fanHigh');
