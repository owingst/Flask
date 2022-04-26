/**
 * weather.js
 *
 * @summary avascript code to support Home Weather Station Web front-end
 * @author Tim Owings
 *
 * Created at     : 2022-01-18 15:00:31 
 * Last modified  : 2022-04-26 14:22:41
 */

 function fetchPMTData() {
  fetch("http://192.168.1.74:5000/getPMTPlotLast24")
  .then(function (response) {
      return response.content()
  }).then(function (text) {
      // document.getElementById("doorStatus").innerHTML = (text['status'] === 1) ?  "<span style='color: red;'>Closed</span>" : "<span style='color: green;'>Open</span>";
      // document.getElementById("doorBattery").innerHTML = (text['battery'] === 1) ? "<span style='color: red;'>Low</span>" : "<span style='color: green;'>OK</span>";
  });
}

function fetchDscData() {
  fetch("http://192.168.1.74:5000/getDscData")
  .then(function (response) {
      return response.json();
  }).then(function (text) {
      document.getElementById("doorStatus").innerHTML = (text['status'] === 1) ?  "<span style='color: red;'>Closed</span>" : "<span style='color: green;'>Open</span>";
      document.getElementById("doorBattery").innerHTML = (text['battery'] === 1) ? "<span style='color: red;'>Low</span>" : "<span style='color: green;'>OK</span>";
  });
}

function fetchF007Data() {
  fetch("http://192.168.1.74:5000/getF007thData")
  .then(function (response) {
      return response.json();
  }).then(function (text) {
      document.getElementById("indoorTemp").innerHTML = text['temperature'];
      document.getElementById("indoorHumidity").innerHTML = text['humidity'];
      document.getElementById("indoorBattery").innerHTML = text['battery === 1'] ? "<span style='color: red;'>Low</span>" : "<span style='color: green;'>OK</span>";
  });
}

function fetchWeatherData() {
  fetch("http://192.168.1.74:5000/getWeathersenseData")
  .then(function (response) {
      return response.json();
  }).then(function (text) {

     if (text['light'] > 10000) {
        getCurrentTemp()
     } else {
      document.getElementById("outdoorTemp").innerHTML = text['temperature'];
     }
      document.getElementById("outdoorHumidity").innerHTML = text['humidity'];
      document.getElementById("outdoorWindspeed").innerHTML = text['avewindspeed'];
      document.getElementById("outdoorWindGustspeed").innerHTML = text['gustwindspeed'];
      document.getElementById("outdoorRain").innerHTML = text['cumulativerain'];
      document.getElementById("outdoorWinddirection").innerHTML = text['winddirection'];
      document.getElementById("outdoorLight").innerHTML = text['light'];
      document.getElementById("outdoorUV").innerHTML = text['uv'];
      document.getElementById("outdoorBattery").innerHTML = text['battery === 1'] ? "<span style='color: red;'>Low</span>" : "<span style='color: green;'>OK</span>";
  });
}

function fetchSDSData() {
  
  fetch("http://192.168.1.74:5000/getPMTData")
  .then(function (response) {
      return response.json();
  }).then(function (text) {
    document.getElementById("pm25").innerHTML = text['pm25'];
    document.getElementById("pm10").innerHTML = text['pm10'];
    document.getElementById("aqi25").innerHTML = text['aqi25'];
    document.getElementById("aqi10").innerHTML = text['aqi10'];
  });
}

function moveDoor() {
  fetch("http://192.168.1.74:5000/moveDoor")
}

function getCurrentTemp() {
  fetch("http://api.openweathermap.org/data/2.5/weather?id=4705708&units=imperial&appid=00eacef6cd8f876a8e305ac16faf1756")
    .then(function (response) {
      return response.json();
    }).then(function (text) {
      var temp = Math.round(text.main['temp']) + " *";
      document.getElementById("outdoorTemp").innerHTML = temp;
    });
}

function getButtonValue() {
  var status = document.getElementById("doorStatus").innerHTML;

  if (status === "<span style='color: red;'>Closed</span>") {
    return "Open";
  } else {
    return "Close";
  }
}

$(document).ready(function () {

  var showDoor = false
  fetchDscData();
  fetchF007Data();
  fetchWeatherData();
  fetchSDSData();
  fetchPMTData();

  var socket = io.connect("http://192.168.1.74:5000");

  socket.on("connect", function () {
    console.log("client connected to server");
    socket.emit("my event", {
      data: "I am connected!",
    });
  });

  socket.on("new data", function (msg) {
    
    //document.getElementById("msgArrived").innerHTML = msg.type;
    console.log("msg arrived: ", msg);
    if (msg.type == "DSC") {
      ds = msg;
      document.getElementById("doorStatus").innerHTML = (ds.status === 1) ? "<span style='color: red;'>Closed</span>" : "<span style='color: green;'>Open</span>";
      document.getElementById("doorBattery").innerHTML = (ds.battery === 1) ? "<span style='color: red;'>Low</span>" : "<span style='color: green;'>OK</span>";
    } else if (msg.type == "SDS") {
      sd = msg;
      document.getElementById("pm25").innerHTML = sd.pm25;
      document.getElementById("pm10").innerHTML = sd.pm10;
      document.getElementById("aqi25").innerHTML = sd.aqi25;
      document.getElementById("aqi10").innerHTML = sd.aqi10;

    } else if (msg.type == "F007th") {
      ts = msg;
      document.getElementById("indoorTemp").innerHTML = ts.temperature;
      document.getElementById("indoorHumidity").innerHTML = ts.humidity;
      document.getElementById("indoorBattery").innerHTML = (ts.battery === 1) ? "<span style='color: red;'>Low</span>" : "<span style='color: green;'>OK</span>";
    } else {
      ws = msg;
      if (ws.light > 10000) {
        getCurrentTemp();
     } else {
      document.getElementById("outdoorTemp").innerHTML = ws.temperature;
     }
      document.getElementById("outdoorHumidity").innerHTML = ws.humidity;
      document.getElementById("outdoorWindspeed").innerHTML = ws.avewindspeed;
      document.getElementById("outdoorWindGustspeed").innerHTML = ws.gustwindspeed;
      document.getElementById("outdoorWinddirection").innerHTML = ws.winddirection;
      document.getElementById("outdoorRain").innerHTML = ws.cumulativerain;
      document.getElementById("outdoorLight").innerHTML = ws.light;
      document.getElementById("outdoorUV").innerHTML = ws.uv;
      document.getElementById("outdoorBattery").innerHTML = (ws.battery === 1) ? "<span style='color: red;'>Low</span>" : "<span style='color: green;'>OK</span>";
    }
  });
});
