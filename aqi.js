var blynkLib = require('blynk-library');
var XMLHttpRequest = require("xmlhttprequest").XMLHttpRequest;
const SDS011Client = require("sds011-client");
const sensor = new SDS011Client("/dev/ttyUSB0");
process.setMaxListeners(20);

var elasticsearch = require('elasticsearch');
var client = new elasticsearch.Client({
  host: '172.104.235.199:9200',
  log: 'error'
});

var AUTH = 'aef3d80fe84d4dc2a3c0f1d3c14bdd2b';
var blynk = new blynkLib.Blynk(AUTH);

var aqi10val = 0
var aqi25val = 0
		
function Get(yourUrl){
    var Httpreq = new XMLHttpRequest(); // a new request
    Httpreq.open("GET",yourUrl,false);
    Httpreq.send(null);
    return Httpreq.responseText;
}

let canQuit = false;
let aqibot = require('aqi-bot');

function listenForReading() {
    sensor.on('reading', r => {
        console.log('Got reading');
        console.log(r);
        blynk.virtualWrite(2, r.pm2p5)
        blynk.virtualWrite(3, r.pm10)
		
		
		aqibot.AQICalculator.getAQIResult("PM10", r.pm10).then((result) => {
    		console.log(result.aqi)
    		aqi10val = result.aqi;
  		}).catch(err => {
    		console.log(err);
  		})
		
		aqibot.AQICalculator.getAQIResult("PM2.5", r.pm2p5).then((result) => {
    		console.log(result.aqi)
    		aqi25val = result.aqi;
  		}).catch(err => {
    		console.log(err);
  		})
  		
        var json_obj = JSON.parse(Get('http://api.weatherlink.com/v1/NoaaExt.json?user=001D0A0100EE&pass=2Ellbelt!&apiToken=B1A41C82525B4BB7AB170F5915D7C316'));
        var inTemp = json_obj.davis_current_observation.temp_in_f
        var inHum = json_obj.davis_current_observation.relative_humidity_in

        blynk.virtualWrite(1, inTemp);
        blynk.virtualWrite(4, inHum);
		
		blynk.virtualWrite(5, aqi10val);
        blynk.virtualWrite(6, aqi25val);
        
		client.create({
  		index: 'sds011',
  		id: 'sds011'+Date.now().toString(),
  		type: 'sensor',
  		
  		body: {
  			timestamp: new Date(),
    		pm25: r.pm2p5,
    		pm10: r.pm10,
    		aqi10: aqi10val,
    		aqi25: aqi25val
  }
});
        canQuit = true;
    });
}

Promise
    .all([sensor.setReportingMode('active'), sensor.setWorkingPeriod(3)])
    .catch(err => {
            console.log(err);
        })
    .then(() => {
        // everything's set
        listenForReading();
    });

let waitCount = 0;
function waitToQuit() {

    waitCount++;

    if (canQuit || waitCount > 10)
        return;

    console.log('Waiting for reading');
    setTimeout(() => {
        waitToQuit();
    },1000);
}

waitToQuit();