"""
This is a quick script to generate the configuration file for the IoT application
Usage: python3 create_config.py tle_file gs_file start_time end_time delta output_file 
I assume a 3LE file. 
I assume a GS file with lat, long. 
I assume start_time and end_time are YYYY-MM-DD HH:MM:SS
"""

#The tles can be found at: The tles can be found from: 
#    https://celestrak.org/NORAD/elements/gp.php?GROUP=planet&FORMAT=tle
#The current gs locations are approximated from: 
#    Kiruthika Devaraj, Ryan Kingsbury, Matt Ligon, Joseph Breu, Vivek
#    Vittaldev, Bryan Klofas, Patrick Yeon, and Kyle Colton. Dove High
#    Speed Downlink System. In Small Satellite Conference, 2017.
#and also:
#    Transmitting, Fast and Slow: Scheduling Satellite Traffic through Space and Time
#    Bill Tao, Maleeha Masood, Indranil Gupta, Deepak Vasisht
#    MobiCom 2023
    
#The power numbers are all converted numbers from:
#    Orbital Edge Computing: Nanosatellite Constellations as a New Class of Computing System
#    Bradley Denby and Brandon Lucia
#    ASPLOS 2020

#The radio numbers are all from:
#   Kiruthika Devaraj, Matt Ligon, Eric Blossom, Joseph Breu, Bryan Klofas, 
#   Kyle Colton, and Ryan Kingsbury. Planet High Speed Radio: 
#   Crossing Gbps from a 3U Cubesat. In Small Satellite Conference, 2019.
    

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
                            "min_elevation": 5
                        },
                        {
                            "iname": "ModelImagingRadio",
                            "self_ctrl": true,
                            "radio_physetup":{
                                "_frequency": 8.09e9,
                                "_bandwidth": 96e6,
                                "_tx_power": 8.2,
                                "_tx_antenna_gain": 15,
                                "_tx_line_loss": 2,
                                "_rx_antenna_gain": 49,
                                "_rx_line_loss": 1.8,
                                "_gain_to_temperature": 29,
                                "_symbol_rate": 76.8e6,
                                "_num_channels": 6
                            }
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
                            "min_elevation": 5
                        },
                        {
                            "iname": "ModelImagingRadio",
                            "self_ctrl": false,
                            "radio_physetup":{                                
                                "_frequency": 8.09e9,
                                "_bandwidth": 96e6,
                                "_tx_power": 8.2,
                                "_tx_antenna_gain": 15,
                                "_tx_line_loss": 2,
                                "_rx_antenna_gain": 49,
                                "_rx_line_loss": 1.8,
                                "_gain_to_temperature": 29
                            }
                        }
                    ]
                }""" % (node_id, gs_lat, gs_lon)
    return string


if __name__ == "__main__":
    ##Usage: python3 create_iot_config.py tle_file gs_file start_time end_time delta output_file
    tle_file = sys.argv[1]
    gs_file = sys.argv[2]
    start_time = sys.argv[3]
    end_time = sys.argv[4]
    delta = sys.argv[5]
    
    output_file = open(sys.argv[6], "w+")
    
    base_str = """
{
    "topologies":
    [
        {
            "name": "ImagingSatConstellation",
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
            line = lines[i:i+3]
            node_id += 1
            tle_line_1 = line[1][:-1]
            tle_line_2 = line[2][:-1] #Ignore the newlines
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
            "logfolder": "imagingLogs",
            "logchunksize": 1000000
        }
}
    """ % (start_time, end_time, delta)
    
    output_file.write(end_str)
    output_file.close()