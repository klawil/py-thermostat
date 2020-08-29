const GAUGE_RADIUS = (200 / 2) - 3;
const DOT_RADIUS = 12;

const CONTROLS = [
  'ac',
  'fanLow',
  'fanHigh',
  'heat'
];

let currentData = {};

function setCircle(degrees, elem) {
  elem.hidden = false;

  const MIN = 5;
  const MAX = 35;
  let percentage = (degrees - MIN) / (MAX - MIN);
  if (percentage > 1) {
    percentage = 1;
  }

  let degreeRange = 270;
  let radians = Math.PI * ((degreeRange * percentage) - 45) / 180;

  let x = GAUGE_RADIUS * Math.cos(radians);
  let y = GAUGE_RADIUS * Math.sin(radians);

  let starting = GAUGE_RADIUS - DOT_RADIUS - 2;

  elem.style.transform = `rotate(${90 + Math.round(radians * 180 / Math.PI)}deg)`;
  elem.style.top = `${starting - y}px`;
  elem.style.left = `${starting - x}px`;
}

function showData() {
  CONTROLS.forEach((item) => {
    let btn = document.getElementById(item);
    btn.isOn = currentData[item] === 1;

    if (currentData[item]) {
      btn.classList.remove('btn-secondary');
      btn.classList.add('btn-light');
    } else {
      btn.classList.remove('btn-light');
      btn.classList.add('btn-secondary');
    }
  });

  let btn = document.getElementById('override');
  if (currentData.name !== 'Override') {
    btn.classList.remove('btn-light');
    btn.classList.add('btn-secondary');
  } else {
    btn.classList.remove('btn-secondary');
    btn.classList.add('btn-light');
  }

  if (currentData.name !== 'Override' && currentData.name.indexOf('Schedule:') === -1) {
    currentData.name = `Schedule: ${currentData.name}`;
  }
  document.getElementById('mode').innerHTML = currentData.name;


  currentData.rooms.forEach((room, index) => {
    let currentTemp = (Math.round(room.currentTemp * 10) / 10).toFixed(1);
    if (
      room.currentTemp === null ||
      room.currentTempTimestamp === null ||
      Date.now() - room.currentTempTimestamp > (1000 * 60 * 10)
    ) {
      currentTemp = '??';
    }

    document.getElementById(`room-name-${index}`).innerHTML = room.name;
    document.getElementById(`room-current-text-${index}`).innerHTML = `${currentTemp}&deg;C`;
    let tempMarker = document.getElementById(`room-current-${index}`);
    if (currentTemp !== '??') {
      setCircle(room.currentTemp, tempMarker);
    } else {
      tempMarker.hidden = true;
    }

    document.getElementById(`room-current-target-${index}`).innerHTML = `${currentData.tempMin} - ${currentData.tempMax}`;

    let minMarker = document.getElementById(`room-min-${index}`);
    let maxMarker = document.getElementById(`room-max-${index}`);
    if (currentData.targetRoom === room.name) {
      setCircle(currentData.tempMin, minMarker);
      setCircle(currentData.tempMax, maxMarker);
    } else {
      minMarker.hidden = true;
      maxMarker.hidden = true;
    }
  });
}

function getData() {
  fetch('/api/state')
    .then((r) => r.json())
    .then((data) => {
      if (!data.success) {
        window.alert(data.message);
        return;
      }
      currentData = data.data;
      showData();
    })
    .then(() => setTimeout(getData, 1000));
}
getData();

function getOutsideTemp() {
  const query = 'SELECT last("value") FROM "temp" WHERE ("type" = \'5N1\') AND time >= now() - 10m'; 

  //  Encode and Interpolate the values
  let url = `http://server.klawil.net:8086/query?q=${encodeURIComponent(query)}&db=wunderground`;
  url = url.replace(/%20/g, "+");

  let headers = new Headers();

  // Set basic authorization header if neccessary
  const username = 'thermostat';
  const password = 'thermostat';
  headers.set('Authorization', 'Basic ' + btoa(username + ":" + password));
  
  startTime = new Date();

  return fetch(url,
  {
    mode: 'cors',
    method: 'get',
    headers: headers
  })
    .then((r) => r.json())
    .then((data) => {
      const temp = Math.round(data.results[0].series[0].values[0][1]);
      document.getElementById('outsideTemp').innerHTML = `${temp}&deg;C`;
    })
    .then(() => setTimeout(getOutsideTemp, 60000))
    .catch((e) => {
      console.error(e);
      setTimeout(getOutsideTemp, 60000)
    });
}
getOutsideTemp();

setInterval(() => {
  let time = `${new Date().getHours().toString().padStart(2, '0')}:${new Date().getMinutes().toString().padStart(2, '0')}`;
  let timeElem = document.getElementById('time');
  if (timeElem.innerHTML !== time) {
    timeElem.innerHTML = time;
  }
}, 100);

CONTROLS.forEach((id) => {
  let elem = document.getElementById(id);

  elem.addEventListener('click', () => {
    elem.blur();
    let newState = !elem.isOn;
    let otherControls = CONTROLS.filter((ctrl) => ctrl !== id);

    let newControls = new FormData()
    newControls.append(id, newState);

    const keepCurrent = () => otherControls.forEach((ctrl) => {
      newControls.append(ctrl, currentData[ctrl] === 1);
    });
    const allOff = () => otherControls.forEach((ctrl) => {
      newControls.append(ctrl, false);
    });

    if (
      (id === 'heat' && newState) ||
      (id !== 'heat' && !newState)
    ) {
      allOff();
    } else if (id.indexOf('fan') !== -1 && newState) {
      keepCurrent();
      if (id === 'fanHigh') {
        newControls.set('fanLow', false);
      } else {
        newControls.set('fanHigh', false);
      }
    } else {
      keepCurrent();
    }

    if (newControls.get('ac') === 'true' && newControls.get('fanHigh') === 'false') {
      newControls.set('fanLow', true);
    }

    if (id !== 'heat' && newState) {
      newControls.set('heat', false);
    }

    fetch('/api/state/set', {
      method: 'POST',
      body: newControls
    })
      .then((r) => r.json())
      .then((data) => {
        currentData = data.data;
        showData();
      });
  });
});

document.getElementById('override').addEventListener('click', () => fetch('/api/state/resume')
  .then((r) => r.json())
  .then((data) => {
    currentData = data.data;
    showData();
  }));

function changeTargetTemp(addValue, key, roomId) {
  let newTemps = new FormData();
  newTemps.append('targetRoom', currentData.rooms[roomId].name);
  [
    'tempMin',
    'tempMax'
  ].forEach((tempKey) => {
    let value = currentData[tempKey];
    if (tempKey === key) {
      value += addValue;
    }
    newTemps.append(tempKey, value);
  });

  fetch('/api/state/temp', {
    method: 'POST',
    body: newTemps
  })
    .then((r) => r.json())
    .then((data) => {
      currentData = data.data;
      showData();
    });
}

[
  0,
  1
].forEach((roomId) => {
  document.getElementById(`room-min-up-${roomId}`).addEventListener('click', changeTargetTemp.bind(null, 1, 'tempMin', roomId));
  document.getElementById(`room-min-down-${roomId}`).addEventListener('click', changeTargetTemp.bind(null, -1, 'tempMin', roomId));
  document.getElementById(`room-max-up-${roomId}`).addEventListener('click', changeTargetTemp.bind(null, 1, 'tempMax', roomId));
  document.getElementById(`room-max-down-${roomId}`).addEventListener('click', changeTargetTemp.bind(null, -1, 'tempMax', roomId));
});
