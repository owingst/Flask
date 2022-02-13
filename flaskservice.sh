#!/bin/bash 

###################################################################
#Script Name	:  flaskservice.sh                                                                                            
#Description	:  Shell script to launch Flask Service                                                                             
#Args           :                                                                                           
#Author       	:  Tim Owings                                                
#Email         	:  owingst@gmail.com                                           
###################################################################
export FLASK_DEBUG=true
export FLASK_APP=/home/pi/flask/flaskservice.py 
flask run --host="192.168.1.74" --port=5000
