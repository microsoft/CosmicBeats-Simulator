'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.
'''

#This is a quick script to generate the configuration file for the IoT application
#Usage: python3 create_iot_config.py tle_file gs_file iot_file start_time end_time delta output_file 
#I assume a 3 line TLE file
#I assume a GS file with lat, long 
#I assume an IoT file with lat, long, packets per day, packet size
#I assume start_time and end_time are YYYY-MM-DD HH:MM:SS

import os
import sys

def get_satellite_string(node_id, tle_line_1, tle_line_2):
    string = """
                {
                    "type": "SAT",
                    "iname": "SatelliteBasic",
                    "nodeid": %d,
                    "loglevel": "info",
                    "tle_1": "%s", 
                    "tle_2": "%s",
                    "additionalargs": "",
                    "models":[
                        {
                            "iname": "ModelOrbit"
                        },
                        {
                            "iname": "ModelFovTimeBased",
                            "min_elevation": 0
                        },
                        {
                            "iname": "ModelDownlinkRadio",
                            "self_ctrl": false,
                            "radio_physetup":{
                                "_frequency": 0.138e9,
                                "_bandwidth": 30e3,
                                "_sf": 11,
                                "_coding_rate": 5,
                                "_preamble": 8,
                                "_tx_power": 1.76,
                                "_tx_antenna_gain": 2.18,
                                "_tx_line_loss": 1,
                                "_rx_antenna_gain": -2.18,
                                "_rx_line_loss": 1,
                                "_gain_to_temperature": -30.1,
                                "_bits_allowed": 2
                            }
                        },
                        {
                            "iname": "ModelAggregatorRadio",
                            "self_ctrl": false,
                            "radio_physetup":{
                                "_frequency": 0.149e9,
                                "_bandwidth": 30e3,
                                "_sf": 11,
                                "_coding_rate": 5,
                                "_preamble": 8,
                                "_tx_power": 1.76,
                                "_tx_antenna_gain": 2.18,
                                "_tx_line_loss": 1,
                                "_rx_antenna_gain": -2.18,
                                "_rx_line_loss": 1,
                                "_gain_to_temperature": -30.1,
                                "_bits_allowed": 2
                            }
                        },
                        {
                            "iname": "ModelPower",
                            "power_consumption": {
                                "TXRADIO": 0.532,
                                "HEATER": 0.532,
                                "RXRADIO": 0.133,
                                "CONCENTRATOR": 0.266,
                                "GPS": 0.190
                            },
                            "power_configurations": {
                                "MAX_CAPACITY": 25308,
                                "MIN_CAPACITY": 15185,
                                "INITIAL_CAPACITY": 25308 
                            },
                            "power_generations":{
                                "SOLAR": 1.666667
                            },
                            "always_on": ["GPS", "CONCENTRATOR", "RXRADIO", "HEATER"],
                            "efficiency": 0.85,
                            "delta": 1
                        },
                        {
                            "iname": "ModelDataStore",
                            "self_ctrl": false
                        },
                        {
                            "iname": "ModelMACTTnC",
                            "beacon_interval":  60,
                            "beacon_backoff": 30,
                            "beacon_frequency": 0.128e9,
                            "downlink_frequency": 0.138e9
                        },
                        {
                            "iname": "ModelMACgateway"
                        }
                    ]
                    
                }""" % (node_id, tle_line_1, tle_line_2)
                
    return string

def get_groundstation_string(node_id, gs_lat, gs_lon):
    string = """
                {
                    "type": "GS",
                    "iname": "GSBasic",
                    "nodeid": %d,
                    "loglevel": "info",
                    "latitude": %f,
                    "longitude": %f,
                    "elevation": 0.0,
                    "additionalargs": "",
                    "models":[
                        {
                            "iname": "ModelFovTimeBased",
                            "min_elevation": 0
                        },
                        {
                            "iname": "ModelLoraRadio",
                            "self_ctrl": false,
                            "radio_physetup":{                                
                                "_frequency": 0.138e9,
                                "_bandwidth": 30e3,
                                "_sf": 11,
                                "_coding_rate": 5,
                                "_preamble": 8,
                                "_tx_power": 1.76,
                                "_tx_antenna_gain": 2.84,
                                "_tx_line_loss": 1,
                                "_rx_antenna_gain": -3.49,
                                "_rx_line_loss": 1,
                                "_gain_to_temperature": -30.1,
                                "_bits_allowed": 2
                            }
                        },
                        {
                            "iname": "ModelMACgs",
                            "num_packets": 10,
                            "timeout": 120,
                            "beacon_frequency": 0.128e9,
                            "downlink_frequency": 0.138e9
                        },
                        {
                            "iname": "ModelDataStore",
                            "queue_size": 1
                        }
                    ]
                }""" % (node_id, gs_lat, gs_lon)
    return string

def get_iot_string(node_id, iot_lat, iot_lon, iot_lambda, iot_data_size):
    string = """
                {
                    "type": "IoT",
                    "iname": "IoTBasic",
                    "nodeid": %d,
                    "loglevel": "info",
                    "latitude": %f,
                    "longitude": %f,
                    "elevation": 0.0,
                    "additionalargs": "",
                    "models":[
                        {
                            "iname": "ModelFovTimeBased",
                            "min_elevation": 0
                        },
                        {
                            "iname": "ModelLoraRadio",
                            "self_ctrl": false,
                            "radio_physetup":{
                                "_frequency": 0.149e9,
                                "_bandwidth": 30e3,
                                "_sf": 11,
                                "_coding_rate": 5,
                                "_preamble": 8,
                                "_tx_power": 22,
                                "_tx_antenna_gain": 2,
                                "_tx_line_loss": 1,
                                "_rx_antenna_gain": 2,
                                "_rx_line_loss": 1,
                                "_gain_to_temperature": -15.2,
                                "_bits_allowed": 2
                            }
                        },
                        {
                            "iname": "ModelDataGenerator",
                            "data_poisson_lambda": %f,
                            "data_size": %d,
                            "self_ctrl": false
                        },
                        {
                            "iname": "ModelMACiot",
                            "backoff_time": 50,
                            "retransmit_time": 60, 
                            "beacon_frequency": 0.128e9,
                            "uplink_frequency": 0.149e9
                        }
                        
                    ]
                }""" % (node_id, iot_lat, iot_lon, iot_lambda, iot_data_size)
    return string


if __name__ == "__main__":
    ##Usage: python3 create_iot_config.py tle_file gs_file iot_file start_time end_time delta output_file
    if len(sys.argv) != 8:
        print("Usage: python3 create_iot_config.py tle_file gs_file iot_file start_time end_time delta output_file")
        sys.exit(1)
        
    tle_file = sys.argv[1]
    gs_file = sys.argv[2]
    iot_file = sys.argv[3]
    start_time = sys.argv[4]
    end_time = sys.argv[5]
    delta = sys.argv[6]
    
    output_file = open(sys.argv[7], "w+")
    
    base_str = """
{
    "topologies":
    [
        {
            "name": "Constln1",
            "id": 0,
            "nodes":
            [
    """
    output_file.write(base_str)
    
    #add tle nodes
    node_id = 0
    
    with open(tle_file, "r") as f:
        lines = f.readlines()
        for i in range(0, len(lines), 3):
            tle_line_1 = lines[i][:-1]
            tle_line_2 = lines[i+1][:-1] #Ignore the newlines
            output_file.write(get_satellite_string(node_id, tle_line_1, tle_line_2))
            output_file.write(",\n")
            
            node_id += 1
            
    #add groundstations

    with open(gs_file, "r") as f:
        for line in f:
            gs_lat = float(line.split(",")[0])
            gs_lon = float(line.split(",")[1])
            output_file.write(get_groundstation_string(node_id, gs_lat, gs_lon))
            output_file.write(",\n")
            
            node_id += 1
            
    #add iot
    with open(iot_file, "r") as f:
        for line in f:
            iot_lat = float(line.split(",")[0])
            iot_lon = float(line.split(",")[1])
            iot_packets_per_day = float(line.split(",")[2])
            iot_lambda = iot_packets_per_day / 24 / 3600
            iot_data_size = int(line.split(",")[3])
            
            output_file.write(get_iot_string(node_id, iot_lat, iot_lon, iot_lambda, iot_data_size))
            output_file.write(",\n")
            node_id += 1
            
            
    #remove last comma
    output_file.seek(output_file.tell() - 2, os.SEEK_SET)
    
    
    #add end of file
    end_str = """
                ]
            }
        ],
        "simtime":
        {
            "starttime": "%s",
            "endtime": "%s",
            "delta": %s
        },
        "simlogsetup":
        {
            "loghandler": "LoggerFileChunkwise",
            "logfolder": "exampleLogs",
            "logchunksize": 1000000
        }
}
    """ % (start_time, end_time, delta)
    
    output_file.write(end_str)
    output_file.close()