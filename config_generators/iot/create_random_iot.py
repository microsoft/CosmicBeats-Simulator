'''
// Copyright (c) Microsoft Corporation.
// Licensed under the MIT license.
'''
#Usage: python create_random_iot.py numIot output_file
import random
import csv
import sys
def generate_random_lat_lon(num_points):
    lat_lon_values = []
    for _ in range(num_points):
        # Generate random latitude between -90 and 90 degrees
        latitude = random.uniform(-90, 90)
        
        # Generate random longitude between -180 and 180 degrees
        longitude = random.uniform(-180, 180)
        
        # Add the value 10220 to each pair
        lat_lon_values.append((latitude, longitude, 10, 220))
    return lat_lon_values
# Number of random lat-long values to generate
num_points = int(sys.argv[1])

generated_values = generate_random_lat_lon(num_points)

f = open(sys.argv[2], 'w')
with f:
    writer = csv.writer(f)
    for row in generated_values:
        writer.writerow(row)