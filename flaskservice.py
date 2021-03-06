#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# Title           : flaskservice.py
# Description     : This script is a Flask Service
# Created By      : Tim Owings
# Created Date    : Mon January 26 2020
# Usage           : /home/pi/flask/flaskservice.sh
# Python          : 3.9.2
# http://192.168.1.74:5000/getSCDData
# http://192.168.1.74:5000/getSCDPlotByDate
# http://192.168.1.74:5000/getSCDPlotLast24
# http://192.168.1.74:5000/getSGPData   good
# http://192.168.1.74:5000/getSGPBase   good
# http://192.168.1.74:5000/getSGPPlotLast24
# missing getSGPPlotByDate
# http://192.168.1.74:5000/getSDSPlotByDate
# http://192.168.1.74:5000/getSDSXData
# http://192.168.1.74:5000/getSDSData
# http://192.168.1.74:5000/getSDSPlotLast24
# =============================================================================
import socket
import datetime
import os
import sys
import time
import io
import RPi.GPIO as GPIO
from PIL import Image
import prctl
from matplotlib import pyplot as plt
import sqlite3
sys.path.append("/home/pi/sdr/")

import paho.mqtt.client as mqtt
from flask_socketio import SocketIO, emit
from flask import send_file
from flask import session
from flask import request
from flask import render_template
from flask import jsonify
from flask import json
from flask import Flask
import datastruct
import utilities
# =============================================================================
app = Flask(__name__)
app.secret_key = 'super_secret_key'
socketio = SocketIO(app, logger=True, engineio_logger=True)

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


@app.route('/sendPush', methods=['GET'])
def sendPush():
    """sendPush """

    global CFG
    global utility

    utility.pushErrorMsg()

    
@app.route('/sendSMS', methods=['GET'])
def sendSMS():
    """sendSMS """

    global CFG
    global utility


    msg = request.args.get('msg')

    datestr = datetime.now()
    msgstr = msg + ' ' + datestr.strftime("%m/%d/%Y, %H:%M:%S") + '\n'

    utility.smssend(msg, msgstr, False, CFG)


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


@app.route('/getWeatherData', methods=['GET'])
def getWeatherData():
    """ getWeatherData """

    global CFG
    global utility
    conn = None
    cur = None
    sql = "SELECT datetime(MAX(ts), 'localtime'), temperature, humidity, windspeed, gust, winddirection, cumulativerain, light, uv, battery FROM weather"

    try:

        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()

        logStatus("getWeatherData: row is {}\n".format(row))

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
        logStatus("Exception in getWeatherData {}\n".format(e))
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

    sql = "select max(cumulativerain) - min(cumulativerain) as difference FROM weather where ts >= ? and ts <= ?"

    start = datetime.datetime.now().strftime("%Y-%m-%d 00:00:00")
    end = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    args = (start, end)
    logStatus("start is {} end is {}\n".format(start, end))

    try:
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql, args)
        row = cur.fetchone()

        if row:
            rc = row[0]
            jsonObj = json.dumps({'rainfall': round(rc)})

        else:
            rc = "getRainfall failed"
            logStatus("getRainfall failed {}\n".format(rc))

        
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
    ws = getWeatherData()
    session.pop('internal', None)
    return render_template('index.html', ds=ds, ts=ts, ws=ws)

# ***************************************** SDS/SGP/SCD Insert code below *************************************************************************


@app.route('/insertSDS', methods=['POST'])
def insertSDS():
    """insertSDS """

    conn = None
    global CFG
    global utility

    try:
        pm10 = request.args.get('pm10')
        pm25 = request.args.get('pm25')
        aqi10 = request.args.get('aqi10')
        aqi25 = request.args.get('aqi25')
        
        args = (pm25, pm10, aqi25, aqi10)
        sql = "INSERT INTO sds(pm25, pm10, aqi25, aqi10) VALUES (?, ?, ?, ?)"
        conn = utility.getConnection(CFG.database_path)
        conn.execute(sql, args)

        conn.commit()

        logStatus("insertSDS: pm25 {} pm10 {} aqi25 {} aqi10 {}\n".format(pm25, pm10, aqi25, aqi10))

        return "OK"

    except Exception as e:
        logStatus("Exception in insertSDS {}\n".format(e))
        return "insertSDS Failed!"

    finally:
        if conn is not None:
            conn.close()


@app.route('/insertSGPBase', methods=['POST'])
def insertSGPBase():
    """insertSGPBase """

    conn = None
    global CFG
    global utility

    try:
        eco2 = request.args.get('eco2')
        tvoc = request.args.get('tvoc')

        logStatus("insertSGPBase: eco2 {} tvoc {}\n".format(eco2, tvoc))
        args = (eco2, tvoc)
        sql = "INSERT INTO sgpbase (eco2, tvoc) VALUES(?, ?)"
        conn = utility.getConnection(CFG.database_path)
        conn.execute(sql, args)

        conn.commit()

        return "OK"

    except Exception as e:
        logStatus("Exception in insertSGPBase {}\n".format(e))
        return "insertSGPBase Failed!"

    finally:
        if conn is not None:
            conn.close()


@app.route('/insertSCD', methods=['POST'])
def insertSCD():
    """insertSCD """

    conn = None
    global CFG
    global utility

    try:

        co2 = request.args.get('co2')
        temp = request.args.get('temp')
        hum = request.args.get('hum')
        logStatus("insertSCD: co2: {} temp: {} hum: {}\n".format(co2, temp, hum))
        sql = "INSERT INTO scd(co2, temp, hum) VALUES (?, ?, ?)"
        conn = utility.getConnection(CFG.database_path)
        args = (co2, temp, hum)
        conn.execute(sql, args)

        conn.commit()

        return "OK"

    except Exception as e:
        logStatus("Exception in insertSCD {}\n".format(e))
        return "insertSCD Failed!"

    finally:
        if conn is not None:
            conn.close()


@app.route('/insertSGP', methods=['POST'])
def insertSGP():
    """insertSGP """

    conn = None
    global CFG
    global utility

    try:

        eco2 = request.args.get('eco2')
        tvoc = request.args.get('tvoc')
        rawh2 = request.args.get('rawh2')
        raweth = request.args.get('raweth')

        logStatus("insertSGP: eco2 {} tvoc {} rawh2 {} raweth {}\n".format(eco2, tvoc, rawh2, raweth))
        args = (eco2, tvoc, rawh2, raweth)

        sql = "INSERT INTO sgp(eco2, tvoc, rawh2, raweth) VALUES (?, ?, ?, ?)"
        conn = utility.getConnection(CFG.database_path)
        conn.execute(sql, args)

        conn.commit()

        return "OK"

    except Exception as e:
        logStatus("Exception in insertSGP {}\n".format(e))
        return "insertSGP Failed!"

    finally:
        if conn is not None:
            conn.close()

# ***************************************** SDS/SGP/SCD Insert code above *************************************************************************

# ***************************************** SGP code above *************************************************************************
@app.route('/getSGPData', methods=['GET'])
def getSGPData():
    """getSGPData """

    conn = None
    global CFG
    global utility

    try:

        sql = "SELECT datetime(MAX(ts), 'localtime'), tvoc, rawh2, raweth FROM sgp"
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()

        sgp = datastruct.SGPStruct()

        if ((row[1] is None) or (row[2] is None) or (row[3] is None)):

            sgp.tvoc = 9
            sgp.rawh2 = 9
            sgp.raweth = 9
            jsonObj = json.dumps(sgp)
            logStatus("getSGPData No data returned\n")
            if 'internal' in session:
                rc = sgp
            else:
                jsonObj = json.dumps(sgp.__dict__)
                rc = jsonObj

        else:

            sgp.tvoc = row[1]
            sgp.rawh2 = row[2]
            sgp.raweth = row[3]
            jsonObj = json.dumps(sgp.__dict__)
            logStatus("getSGPData Request Processed Successfully\n")
            if 'internal' in session:
                rc = sgp
            else:
                jsonObj = json.dumps(sgp.__dict__)
                rc = jsonObj

        return rc

    except Exception as e:
        logStatus("Exception in getSGPData {}\n".format(e))
        return "getSGPData Failed!"

    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


@app.route('/getSGPBase', methods=['GET'])
def getSGPBase():
    """getSGPBase """

    conn = None
    global CFG
    global utility

    try:

        sql = "SELECT datetime(MAX(ts), 'localtime'), eco2, tvoc FROM sgpbase"
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()

        sgp = datastruct.SGPStruct()

        if ((row[1] is None) or (row[2] is None)):

            sgp.type = "SGP"
            sgp.eco2 = 9
            sgp.tvoc = 9
            jsonObj = json.dumps(sgp)
            logStatus("getSGPBase No data returned\n")
            if 'internal' in session:
                rc = sgp
            else:
                jsonObj = json.dumps(sgp.__dict__)
                rc = jsonObj

        else:

            sgp.type = "SGP"
            sgp.eco2 = row[1]
            sgp.tvoc = row[2]
            jsonObj = json.dumps(sgp.__dict__)
            logStatus("getSGPBase Request Processed Successfully\n")
            if 'internal' in session:
                rc = sgp
            else:
                jsonObj = json.dumps(sgp.__dict__)
                rc = jsonObj

        return rc

    except Exception as e:
        logStatus("Exception in getSGPBase {}\n".format(e))
        return "getSGPBase Failed!"

    finally:
        if cur is not None:
            cur.close()
        if conn is not None:
            conn.close()


@app.route('/getSGPPlotLast24', methods=['GET'])
def getSGPPlotLast24():
    """ getSGPPlotLast24 """

    global CFG
    global utility
    conn = None
    cur = None
    ts = []
    eco2 = []
    tvoc = []
    rawh2 = []
    raweth = []

    #sql = "SELECT datetime(ts, 'localtime'), eco2, tvoc, rawh2, raweth FROM sgp where ts >= ? and ts <= ? order by ts asc"
    sql = "SELECT datetime(ts, 'localtime'), tvoc FROM sgp where ts >= ? and ts <= ? order by ts asc"

    end = datetime.datetime.now()
    start = end - datetime.timedelta(hours=24)
    args = (start, end)

    try:
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql, args)
        rows = cur.fetchall()

        if (rows):
            for row in rows:

                dt = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                ts.append(dt)
                tvoc.append(row[1])

        else:
               logStatus("getSGPPlotLast24: No rows returned\n")   
               return "getSGPPlotLast24: No rows returned"  
                

        plt.title('SGP Data')
        plt.ylabel('Y axis')
        plt.xlabel('X axis')

        # plt.plot(ts, eco2, 'r', label='eco2', linewidth=2)
        plt.plot(ts, tvoc, 'b', label='tvoc', linewidth=2)
        # plt.plot(ts, rawh2, 'b', label='rawh2', linewidth=2)
        # plt.plot(ts, raweth, 'r', label='raweth', linewidth=2)

        plt.legend(loc="best")
        plt.xticks(rotation=90)

        bytes_image = io.BytesIO()
        plt.savefig(bytes_image, format='png')
        bytes_image.seek(0)
        plt.close()
        return send_file(bytes_image, mimetype='image/png')

    except Exception as e:
        logStatus("Exception in getSGPPlotLast24 {}\n".format(e))
        return e

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()


@app.route('/getRawSGPPlotLast24', methods=['GET'])
def getRawSGPPlotLast24():
    """ getRawSGPPlotLast24 """

    global CFG
    global utility
    conn = None
    cur = None
    ts = []
    rawh2 = []
    raweth = []

    sql = "SELECT datetime(ts, 'localtime'), rawh2, raweth FROM sgp where ts >= ? and ts <= ? order by ts asc"

    end = datetime.datetime.now()
    start = end - datetime.timedelta(hours=24)
    args = (start, end)

    try:
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql, args)
        rows = cur.fetchall()

        if (rows):
            for row in rows:

                dt = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                ts.append(dt)
                rawh2.append(row[1])
                raweth.append(row[2])

        else:
               logStatus("getRawSGPPlotLast24: No rows returned\n")    
               return "getRawSGPPlotLast24: No rows returned"                

        plt.title('Raw SGP Data')
        plt.ylabel('Y axis')
        plt.xlabel('X axis')

        plt.plot(ts, rawh2, 'b', label='rawh2', linewidth=2)
        plt.plot(ts, raweth, 'r', label='raweth', linewidth=2)

        #plt.legend(loc="upper left")
        plt.legend(loc="best")
        plt.xticks(rotation=90)

        bytes_image = io.BytesIO()
        plt.savefig(bytes_image, format='png')
        bytes_image.seek(0)
        plt.close()
        return send_file(bytes_image, mimetype='image/png')

    except Exception as e:
        logStatus("Exception in getRawSGPPlotLast24 {}\n".format(e))
        return e

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()

# ***************************************** SGP code above *************************************************************************

# ***************************************** SCD code below *************************************************************************

@app.route('/getSCDPlotByDate', methods=['GET'])
def getSCDPlotByDate():
    """ getSCDPlotByDate """

    global CFG
    global utility
    conn = None
    cur = None
    ts = []
    co2 = []

    sql = "SELECT datetime(ts, 'localtime'), co2 FROM scd where ts >= ? and ts <= ? order by ts asc"

    start = request.args.get('start')
    end = request.args.get('end')
    args = (start, end)
    logStatus("getSCDPlotByDate start: {} end: {}\n".format(start, end))

    try:
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql, args)
        rows = cur.fetchall()

        if (rows):
            for row in rows:

                dt = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                ts.append(dt)
                co2.append(row[1])

        else:
               logStatus("getSCDPlotByDate: No rows returned\n")
               return "getSCDPlotByDate: No rows returned"

        plt.title('SCD Data')
        plt.ylabel('Y axis')
        plt.xlabel('X axis')

        plt.plot(ts, co2, 'b', label='co2', linewidth=2)

        plt.legend(loc="best")
        plt.xticks(rotation=90)

        bytes_image = io.BytesIO()
        plt.savefig(bytes_image, format='png')
        bytes_image.seek(0)
        plt.close()
        return send_file(bytes_image, mimetype='image/png')

    except Exception as e:
        logStatus("Exception in getSCDPlotByDate {}\n".format(e))
        return e

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()


@app.route('/getSCDPlotLast24', methods=['GET'])
def getSCDPlotLast24():
    """ getSCDPlotLast24 """

    global CFG
    global utility
    conn = None
    cur = None
    ts = []
    co2 = []

    sql = "SELECT datetime(ts, 'localtime'), co2 FROM scd where ts >= ? and ts <= ? order by ts asc"

    end = datetime.datetime.now()
    start = end - datetime.timedelta(hours=24)

    logStatus("getSCDPlotLast24 start: {} end: {}\n".format(start, end))
    args = (start, end)

    try:
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql, args)
        rows = cur.fetchall()

        if (rows):
            for row in rows:

                dt = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                ts.append(dt)
                co2.append(row[1])
        else:
               logStatus("getSCDPlotLast24: No rows returned\n") 
               return "getSCDPlotLast24: No rows returned"               

        plt.title('SCD Data')
        plt.ylabel('Y axis')
        plt.xlabel('X axis')

        plt.plot(ts, co2, 'b', label='co2', linewidth=2)

        plt.legend(loc="best")
        plt.xticks(rotation=90)

        bytes_image = io.BytesIO()
        plt.savefig(bytes_image, format='png')
        bytes_image.seek(0)
        plt.close()
        return send_file(bytes_image, mimetype='image/png')

    except Exception as e:
        logStatus("Exception in getSGPPlotLast24 {}\n".format(e))
        return e

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()


@app.route('/getSCDData', methods=['GET'])
def getSCDData():
    """ getSCDData - gets latest row"""

    global CFG
    global utility
    conn = None
    cur = None

    sql = "SELECT datetime(max(ts), 'localtime'), co2 FROM scd"

    try:
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()

        if ((row is None) or (row[0] is None)):

            scd = datastruct.SCDStruct()
            scd.type = "SCD"
            scd.ts = 9
            scd.co2 = 9

            logStatus("getSCDData No data returned\n")
            if 'internal' in session:
                rc = scd
            else:
                jsonObj = json.dumps(scd.__dict__)
                rc = jsonObj
        else:

            scd = datastruct.SCDStruct()
            scd.type = "SCD"
            scd.ts = row[0]
            scd.co2 = row[1]

            logStatus("getSCDData Processed Successfully\n")
            if 'internal' in session:
                rc = scd
            else:
                jsonObj = json.dumps(scd.__dict__)
                rc = jsonObj

        return rc

    except Exception as e:
        logStatus("Exception in getSCDData {}\n".format(e))
        return e

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()

# ***************************************** SCD code above *************************************************************************

# ***************************************** SDS code below *************************************************************************

@app.route('/getSDSData', methods=['GET'])
def getSDSData():
    """ getSDSData - gets latest row"""

    global CFG
    global utility
    conn = None
    cur = None

    sql = "SELECT datetime(max(ts), 'localtime'), pm25, pm10, aqi25, aqi10 FROM sds"

    try:
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql)
        row = cur.fetchone()

        if ((row[1] is None) or (row[2] is None) or (row[3] is None) or (row[4] is None)):

            sd = datastruct.SDSStruct()
            sd.type = "SDS"
            sd.ts = 9
            sd.pm25 = 9
            sd.pm10 = 9
            sd.aqi25 = 9
            sd.aqi10 = 9

            logStatus("getSDSData No data returned\n")
            if 'internal' in session:
                rc = sd
            else:
                jsonObj = json.dumps(sd.__dict__)
                rc = jsonObj
        else:

            sd = datastruct.SDSStruct()
            sd.type = "SDS"
            sd.ts = row[0]
            sd.pm25 = row[1]
            sd.pm10 = row[2]
            sd.aqi25 = row[3]
            sd.aqi10 = row[4]

            logStatus("getSDSData Processed Successfully\n")
            if 'internal' in session:
                rc = sd
            else:
                jsonObj = json.dumps(sd.__dict__)
                rc = jsonObj

        return rc

    except Exception as e:
        logStatus("Exception in getSDSData {}\n".format(e))
        return e

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()


@app.route('/getSDSDataByDate', methods=['GET'])
def getSDSDataByDate():
    """ getSDSDataByDate """

    global CFG
    global utility
    conn = None
    cur = None
    arr = []

    sql = "SELECT datetime(ts, 'localtime'), pm25, pm10, aqi25, aqi10 FROM sds where ts >= ? and ts <= ? order by ts asc"

    start = request.args.get('start')
    end = request.args.get('end')
    args = (start, end)
    logStatus("getSDSDataByDate: start {} and end {} dates: \n".format(start, end))

    try:
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql, args)
        rows = cur.fetchall()

        if (rows):
            for row in rows:

                if ((row[1] is None) or (row[2] is None) or (row[3] is None) or (row[4] is None)):

                    sd = datastruct.SDSStruct()

                    sd.ts = 9
                    sd.pm25 = 9
                    sd.pm10 = 9
                    sd.aqi25 = 9
                    sd.aqi10 = 9

                    logStatus("getSDSDataByDate No data returned\n")
                    if 'internal' in session:
                        arr.append(sd)
                    else:
                        jsonObj = json.dumps(sd.__dict__)
                        arr.append(jsonObj)

                else:

                    sd = datastruct.SDSStruct()

                    sd.ts = row[0]
                    sd.pm25 = row[1]
                    sd.pm10 = row[2]
                    sd.aqi25 = row[3]
                    sd.aqi10 = row[4]

                    logStatus("getSDSDataByDate Processed Successfully\n")
                    if 'internal' in session:
                        arr.append(sd)
                    else:
                        jsonObj = json.dumps(sd.__dict__)
                        arr.append(jsonObj)

            jsonArr = json.dumps(arr)
            return jsonArr
        else:
            logStatus("getSDSDataByDate No rows returned\n")

    except Exception as e:
        logStatus("Exception in getSDSDataByDate {}\n".format(e))
        return e

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()


@app.route('/getSDSPlotLast24', methods=['GET'])
def getSDSPlotLast24():
    """ getSDSPlotLast24 """

    global CFG
    global utility
    conn = None
    cur = None
    arr = []
    ts = []
    pm25 = []
    pm10 = []
    aqi25 = []
    aqi10 = []

    sql = "SELECT datetime(ts, 'localtime'), pm25, pm10 FROM sds where ts >= ? and ts <= ? order by ts asc"

    end = datetime.datetime.now()
    start = end - datetime.timedelta(hours=24)
    args = (start, end)

    try:
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql, args)
        rows = cur.fetchall()

        if (rows):
            for row in rows:

                dt = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                ts.append(dt)
                pm25.append(row[1])
                pm10.append(row[2])
        else:
            logStatus("getSDSPlotLast24: No rows returned\n")
            return "getSDSPlotLast24: No rows returned"

        plt.title('SDS Data')
        plt.ylabel('Y axis')
        plt.xlabel('X axis')

        plt.plot(ts, pm25, 'r', label='PM25', linewidth=2)
        plt.plot(ts, pm10, 'b', label='PM10', linewidth=2)
        plt.legend(loc="best")
        plt.xticks(rotation=90)
        bytes_image = io.BytesIO()
        plt.savefig(bytes_image, format='png')
        bytes_image.seek(0)
        plt.close()
        return send_file(bytes_image, mimetype='image/png')

    except Exception as e:
        logStatus("Exception in getSDSPlotLast24 {}\n".format(e))
        return e

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()


@app.route('/getSDSPlotByDate', methods=['GET'])
def getSDSPlotByDate():
    """ getSDSPlotByDate """

    global CFG
    global utility
    conn = None
    cur = None
    arr = []
    ts = []
    pm25 = []
    pm10 = []
    aqi25 = []
    aqi10 = []

    sql = "SELECT datetime(ts, 'localtime'), pm25, pm10, aqi25, aqi10 FROM sds where ts >= ? and ts <= ? order by ts asc"

    start = request.args.get('start')
    end = request.args.get('end')
    args = (start, end)
    logStatus("getSDSPlotByDate: start {} and end {} dates: \n".format(start, end))

    try:
        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql, args)
        rows = cur.fetchall()

        logStatus("getSDSPlotByDate: data returned {}\n".format(rows))

        if (rows):
            for row in rows:

                dt = datetime.datetime.strptime(row[0], '%Y-%m-%d %H:%M:%S')
                logStatus("getSDSPlotByDate: dt is {}\n".format(dt))
                ts.append(dt)
                pm25.append(row[1])
                pm10.append(row[2])
        else:
               logStatus("getSDSPlotByDate: No rows returned\n")  
               return "getSDSPlotByDate: No rows returned"

        plt.title('SDS Data')
        plt.ylabel('Y axis')
        plt.xlabel('X axis')

        plt.plot(ts, pm25, 'r', label='PM25', linewidth=2)
        plt.plot(ts, pm10, 'b', label='PM10', linewidth=2)
        # plt.plot(ts, aqi25,'g', label='aqi25', linewidth=2)
        # plt.plot(ts, aqi10,'y', label='aqi10', linewidth=2)
        plt.legend(loc="best")
        plt.xticks(rotation=90)
        # plt.grid(False,color='k')
        # plt.show()

        bytes_image = io.BytesIO()
        plt.savefig(bytes_image, format='png')
        bytes_image.seek(0)
        # plt.savefig('/home/pi/flask/plot.png')
        plt.close()
        return send_file(bytes_image, mimetype='image/png')

    except Exception as e:
        logStatus("Exception in getSDSPlotByDate {}\n".format(e))
        return e

    finally:
        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()


@app.route('/getSDSXData/<rowcnt>', methods=['GET'])
def getSDSXData(rowcnt):
    """ getSDSXData """

    global CFG
    global utility
    conn = None
    cur = None
    arr = []

    sql = "SELECT datetime(ts, 'localtime'), pm25, pm10, aqi25, aqi10 FROM sds order by ts asc LIMIT ?"

    try:

        conn = utility.getConnection(CFG.database_path)
        cur = conn.cursor()
        cur.execute(sql, (rowcnt,))
        rows = cur.fetchall()
        cnt = len(rows)

        if (rows):
            for row in rows:

                if ((row[1] is None) or (row[2] is None) or (row[3] is None) or (row[4] is None)):

                    sd = datastruct.SDSStruct()

                    sd.ts = 9
                    sd.pm25 = 9
                    sd.pm10 = 9
                    sd.aqi25 = 9
                    sd.aqi10 = 9

                    logStatus("getSDSXData No data returned\n")
                    if 'internal' in session:
                        arr.append(sd)
                    else:
                        jsonObj = json.dumps(sd.__dict__)
                        arr.append(jsonObj)

                else:

                    sd = datastruct.SDSStruct()

                    sd.ts = row[0]
                    sd.pm25 = row[1]
                    sd.pm10 = row[2]
                    sd.aqi25 = row[3]
                    sd.aqi10 = row[4]

                    logStatus("getSDSXData Processed Successfully\n")
                    if 'internal' in session:
                        arr.append(sd)
                    else:
                        jsonObj = json.dumps(sd.__dict__)
                        arr.append(jsonObj)

            logStatus("getSDSXData: arr is {}\n".format(arr))
            jsonArr = json.dumps(arr)
            logStatus("getSDSXData: jsonArr is {}\n".format(jsonArr))
            return jsonArr
        else:
            logStatus("getSDSXData No rows returned\n")

    except Exception as e:
        logStatus("Exception in getSDSXData {}\n".format(e))
        return e

    finally:

        if cur is not None:
            cur.close()

        if conn is not None:
            conn.close()

# ***************************************** SDS code above *************************************************************************


try:
    # logStatus("In main initstuff...\n")
    prctl.set_name("flaskservice")
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
