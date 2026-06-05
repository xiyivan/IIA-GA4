#!/usr/local/apps/anaconda3-5.3.1/bin/python
# Python to read in data
import matplotlib.pyplot as plt
tim = []   # Initiate lists for time and inlet water temperature
T1w = []

file_name = input("Enter data file name: ") # Prompt for file name and open file
data_file = open(file_name,"r")
title = data_file.readline() # Read first header line
props = data_file.readline() # Read second header line

# Now read in data line by line
for line in data_file:
    vals = line.split() # Split each line into "words"
    tim.append(eval(vals[0])) # Convert words (strings) to floating point
    T1w.append(eval(vals[1])) # and append to arrays tim[] and T1w

plt.plot(tim,T1w) # Plot a graph
plt.show()





