#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Title           : flaskservice.py
# Description     : This script is a Flask Service
# Created By      : Tim Owings
# Created Date    : Mon January 26 2020
# Usage           : /home/pi/flask/flaskservice.sh
# Python          : 3.9.2
# =============================================================================
import datetime
import os
import sys
import time
import RPi.GPIO as GPIO
sys.path.append("/home/pi/sdr/")
import datastruct
from flask import Flask
from flask import json
from flask import jsonify
from flask import render_template
from flask import request
from flask import session
from flask_socketio import SocketIO, emit
import paho.mqtt.client as mqtt
import utilities
import socket 
# =============================================================================
app = Flask(__name__)
app.secret_key = 'super_secret_key'
socketio = SocketIO(app,logger=True, engineio_logger=True)

RELAY_CH1 = 26
CONNECTED = False
CFG = None
utility = None
       
@socketio.on('connect')
def test_connect():
    logStatus("Client Connected\n")
    emit("my response", {"data": "Connected"})

@socketio.on("disconnect")
def test_disconnect():
    logStatus("Client disconnected\n")
    
@socketio.on('message')
def handle_message(data):
    logStatus('received message: ' + data)

def sendData(data):
    socketio.emit('new data', data, broadcast=True)

def logStatus(msg):
    """ Function to write logs to a file. Never could get Flask logging to a file to work.... """
    try:
        fhandle = open('/home/pi/flask/flaskservice.log', 'a')
        fhandle.write(msg)
        fhandle.close()
        
    except Exception as e:
        logStatus("Exception in logStatus {}\n".format(e))


def on_connect(client, userdata, rc, properties=None):
    """ on_connect """
    
    global CFG
    
    client.subscribe(CFG.changed_topic)
    logStatus("on_connect: Subscribed\n")


def on_message(client, userdata, msg):
    """ on_message """    
    
    data = json.loads(msg.payload.decode())

    sendData(data)
    
        
@app.route('/getLogs', methods=['GET'])
def getLogs():
    """getLogs """    
    
    file = open("/home/pi/sdr/sdrsensor.log")

    lines = file.readlines()
    
    return jsonify(lines)


@app.route('/registerDeviceToken', methods=['GET'])
def registerDeviceToken():
    """registerDeviceToken """    
    
    conn = None
    global CFG
    global utility

    try:

        token = request.args.get('token')
        device = request.args.get('device')
        args = (token, device)
        logStatus("Token is {} Device is {}\n".format(token, device))   

        sql = "INSERT INTO tokens(token, device) VALUES (?, ?) ON CONFLICT(device) DO UPDATE SET token = EXCLUDED.token"

        conn = utility.getConnection(CFG.database_path)
        conn.execute(sql, args)
        
        conn.commit()

        return "registerDeviceToken success"

    except Exception as e:
        logStatus("Exception in registerDeviceToken {}\n".format(e))
        return "registerDeviceToken Failed!"

    finally:
        if conn is not None:
            conn.close() 


@app.route('/getProcs/<name>', methods=['GET'])
def getProcs(name):
    """ API to get process ids """

    cmd = "ps -ef | grep -v grep | grep -Hsi " + name

    try:

        proclist = os.popen(cmd).read()

        return proclist

    except Exception as e:
        logStatus("Exception in getProcs {}\n".format(e))


@app.route('/shutdown', methods=['GET'])
def shutdown():
    """ API to shutdown Pi """

    os.system("sudo poweroff")


@app.route('/moveDoor', methods=['GET'])
def moveDoor():
    """ API to open/close Garage Door """

    try:
        GPIO.setwarnings(False)
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(RELAY_CH1, GPIO.OUT)
        GPIO.output(RELAY_CH1, GPIO.LOW)
        time.sleep(1)
        GPIO.cleanup()
        return "moveDoor Request Processed Successfully"

    except Exception as e:
        logStatus("Exception in moveDoor {}\n".format(e))         
                       
            
@app.route('/getWeathersenseData', methods=['GET'])              
def getWeathersenseData():
    """ getWeathersenseData """    

    global CFG
    global utility
    conn = None
    cur = None
    sql = "SELECT datetime(MAX(ts), 'localtime'), temperature, humidity, windspeed, gust, winddirection, cumulativerain, light, uv, battery FROM weathersense"

    try:

        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()

        ws = datastruct.WeatherStruct()
        if ((row[1] is None) or (row[2] is None) or (row[3] is None) or (row[4] is None) or (row[5] is None) or (row[6] is None) or (row[7] is None) or (row[8] is None) or (row[9] is None)):             

            ws.temperature = 1000
            ws.humidity = 1000
            ws.avewindspeed = 1000
            ws.gustwindspeed = 1000
            ws.winddirection = 1000
            ws.cumulativerain = 1000
            ws.light = 1000
            ws.uv = 1000
            ws.battery = 9
            if 'internal' in session:
                rc = ws
            else:   
                jsonObj = json.dumps(ws.__dict__)
                rc = jsonObj
                
        else:

            ws.temperature = row[1]
            ws.humidity = row[2]
            ws.avewindspeed = row[3]
            ws.gustwindspeed = row[4]
            ws.winddirection = row[5]
            ws.cumulativerain = row[6]
            ws.light = row[7]
            ws.uv = row[8]
            ws.battery = row[9]
            if 'internal' in session:
                rc = ws
            else:   
                jsonObj = json.dumps(ws.__dict__)
                rc = jsonObj
            
        return rc
  
    except Exception as e:
        logStatus("Exception in getData {}\n".format(e))   
        return e

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()   
                        
            
@app.route('/getF007thData', methods=['GET']) 
def getF007thData():
    """ getF007thData """
           
    global CFG      
    global utility 
    conn = None
    cur = None
    sql = "SELECT datetime(MAX(ts), 'localtime'), temperature, humidity, battery FROM f007th"

    try:

        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()

        if ((row[1] is None) or (row[2] is None) or (row[3] is None)): 
            fs = datastruct.F007thStruct
            fs.temperature = row[1]
            fs.humidity = row[2]
            fs.battery = row[3]
            jsonObj = json.dumps(fs)
            logStatus("getF007thData No data returned\n")
            if 'internal' in session:
                rc = fs
            else:   
                jsonObj = json.dumps(fs.__dict__)
                rc = jsonObj

        else:
            fs = datastruct.F007thStruct()
            fs.temperature = row[1]
            fs.humidity = row[2]
            fs.battery = row[3]
            jsonObj = json.dumps(fs.__dict__)
            logStatus("getF007thData Request Processed Successfully\n")
            if 'internal' in session:
                rc = fs
            else:   
                jsonObj = json.dumps(fs.__dict__)
                rc = jsonObj
            
        return rc
    
    except Exception as e:
        logStatus("Exception in getData {}\n".format(e))   
        return e

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()   
                       
                        
@app.route('/getDscData', methods=['GET']) 
def getDscData():
    """ API to get latest DoorStatus from DB """
    
    global CFG
    global utility
    conn = None
    cur = None

    sql = "select datetime(MAX(ts), 'localtime'), esn, status, battery from dsc"

    try: 
   
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()
        
        if ((row[1] is None) or (row[2] is None) or (row[3] is None)): 
            ds = datastruct.DscStruct()
            ds.type = "DSC"
            ds.esn = 9
            ds.status = 9
            ds.battery = 9
            jsonObj = json.dumps(ds.__dict__)
            logStatus("getDscData No data returned\n")
            if 'internal' in session:
                rc = ds
            else:   
                jsonObj = json.dumps(ds.__dict__)
                rc = jsonObj
        else:    
            ds = datastruct.DscStruct()
            ds.type = "DSC"
            ds.esn = row[1]
            ds.status = row[2]
            ds.battery = row[3]
            jsonObj = json.dumps(ds.__dict__)
            logStatus("getDscData Request Processed Successfully\n")
            if 'internal' in session:
                rc = ds
            else:   
                jsonObj = json.dumps(ds.__dict__)
                rc = jsonObj
            
        return rc

    except Exception as e:
        logStatus("Exception in getDscData {}\n".format(e))   
        return e

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()
                   

@app.route('/getRainfall', methods=['GET']) 
def getRainfall():
    """ getRainfall """    
        
    global CFG    
    global utility
    conn = None
    cur = None

    sql = "select max(cumulativerain) - min(cumulativerain) as difference FROM weathersense where ts >= ? and ts <= ?"
    
    start = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
    end = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    args = (start, end)
    logStatus("getRainfall: start {} and end {} dates: \n".format(start, end))  

    try:
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql, args)
        row = cur.fetchone()    

        if row:
            rc = row[0]
            jsonObj = json.dumps({'rainfall': rc})
        else:
            rc = "getRainfall failed"
       
        logStatus("returning rainfall {}\n".format(rc)) 
        return jsonObj

    except Exception as e: 
        logStatus("Exception in getRainfall {}\n".format(e)) 
        return e

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()

                 
@app.route('/ping/<value>', methods=['GET'])
def ping(value):
    """ API to test if server is up """
    
    return value

@app.route('/getConfig', methods=['GET'])
def getConfig():
    """ API to get Config values """
    jsonObj = json.dumps(CFG.__dict__)
    return jsonObj

 
@app.route("/web")
def index():
    """ Web App entry point """
    logStatus("Flask Service Web entry called\n")   
    session['internal'] = 1 
    ds = getDscData()
    ts = getF007thData()
    ws = getWeathersenseData()
    session.pop('internal', None)
    return render_template('index.html', ds=ds, ts=ts, ws=ws)      


try:
    logStatus("In main initstuff...\n")
    utility = utilities.Utility()
    CFG = utility.getCFG()
    client = mqtt.Client()
    client.on_connect = on_connect
    client.on_message = on_message
    client.connect(CFG.broker_address, 1883, 60)
    client.loop_start()

except Exception as e:
    logStatus("Exception in init {}\n".format(e))


if __name__ == '__main__':

    socketio.run(host="192.168.1.74", port=5000, threaded=False, debug=True)

    
