import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from os.path import dirname, join as pjoin
import scipy.io as sio
import scipy.signal as signal
from mat73_reader import load
from pathlib import Path


Sample_Rate = 200

# Load .mat Data
East001_5th = load("Test-001/SUT-001-5th-East.mat")
West001_5th = load("Test-001/SUT-001-5th-West.mat")
East001_Ground = load("Test-001/SUT-001-Ground-East.mat")
West001_Ground = load("Test-001/SUT-001-Ground-West.mat")
print(East001_5th.keys())
def inspect_dict(d, indent=0):
    for key, value in d.items():
        print(" " * indent + str(key), type(value))

        if isinstance(value, dict):
            inspect_dict(value, indent + 2)

inspect_dict(East001_5th)
print("\n")
print("==========================================\n")
inspect_dict(West001_5th)
print("\n")
print("==========================================\n")
inspect_dict(East001_Ground)
print("\n")
print("==========================================\n")
inspect_dict(West001_Ground)
def save_mat_data(data, filename):
    data = data["data"]

    np.savez_compressed(
        filename,
        accX=data["accX"],
        accY=data["accY"],
        accZ=data["accZ"],
        currA=data["currA"],
        currD=data["currD"],
        tempX=data["tempX"],
        tempY=data["tempY"],
        tempZ=data["tempZ"],
        time=data["time"],
        vbatA=data["vbatA"],
        vbatD=data["vbatD"],
    )


save_mat_data(East001_5th, "East001_5th.npz")
save_mat_data(West001_5th, "West001_5th.npz")
save_mat_data(East001_Ground, "East001_Ground.npz")
save_mat_data(West001_Ground, "West001_Ground.npz")
East001_5th_accX = np.load("East001_5th.npz")["accX"]
East001_5th_accY = np.load("East001_5th.npz")["accY"]
East001_5th_accZ = np.load("East001_5th.npz")["accZ"]
East001_5th_time = np.load("East001_5th.npz")["time"]
West001_5th_accX = np.load("West001_5th.npz")["accX"]
West001_5th_accY = np.load("West001_5th.npz")["accY"]
West001_5th_accZ = np.load("West001_5th.npz")["accZ"]
West001_5th_time = np.load("West001_5th.npz")["time"]
East001_Ground_accX = np.load("East001_Ground.npz")["accX"]
East001_Ground_accY = np.load("East001_Ground.npz")["accY"]
East001_Ground_accZ = np.load("East001_Ground.npz")["accZ"]
East001_Ground_time = np.load("East001_Ground.npz")["time"]
West001_Ground_accX = np.load("West001_Ground.npz")["accX"]
West001_Ground_accY = np.load("West001_Ground.npz")["accY"]
West001_Ground_accZ = np.load("West001_Ground.npz")["accZ"]
West001_Ground_time = np.load("West001_Ground.npz")["time"]

plt.subplot(3, 1, 1)
plt.plot(East001_5th_time, East001_5th_accX)
plt.title("Acceleration - X @ East001 , 5th floor")
plt.xlabel("Time (Sec)")
plt.ylabel("ax (mg)")
plt.subplot(3, 1, 2)
plt.plot(East001_5th_time, East001_5th_accY)
plt.title("Acceleration - Y @ East001 , 5th floor")
plt.xlabel("Time (Sec)")
plt.ylabel("ay (mg)")
plt.subplot(3, 1, 3)
plt.plot(East001_5th_time, East001_5th_accZ)
plt.title("Acceleration - Z @ East001 , 5th floor")
plt.xlabel("Time (Sec)")
plt.ylabel("az (mg)")
plt.show()
plt.subplot(3, 1, 1)
plt.plot(West001_5th_time, West001_5th_accX)
plt.title("Acceleration - X @ West001 , 5th floor")
plt.xlabel("Time (Sec)")
plt.ylabel("ax (mg)")
plt.subplot(3, 1, 2)
plt.plot(West001_5th_time, West001_5th_accY)
plt.title("Acceleration - Y @ West001 , 5th floor")
plt.xlabel("Time (Sec)")
plt.ylabel("ay (mg)")
plt.subplot(3, 1, 3)
plt.plot(West001_5th_time, West001_5th_accZ)
plt.title("Acceleration - Z @ West001 , 5th floor")
plt.xlabel("Time (Sec)")
plt.ylabel("az (mg)")
plt.show()
plt.subplot(3, 1, 1)
plt.plot(East001_Ground_time, East001_Ground_accX)
plt.title("Acceleration - X @ East001 , Ground floor")
plt.xlabel("Time (Sec)")
plt.ylabel("ax (mg)")
plt.subplot(3, 1, 2)
plt.plot(East001_Ground_time, East001_Ground_accY)
plt.title("Acceleration - Y @ East001 , Ground floor")
plt.xlabel("Time (Sec)")
plt.ylabel("ay (mg)")
plt.subplot(3, 1, 3)
plt.plot(East001_Ground_time, East001_Ground_accZ)
plt.title("Acceleration - Z @ East001 , Ground floor")
plt.xlabel("Time (Sec)")
plt.ylabel("az (mg)")
plt.show()
plt.subplot(3, 1, 1)
plt.plot(West001_Ground_time, West001_Ground_accX)
plt.title("Acceleration - X @ West001 , Ground floor")
plt.xlabel("Time (Sec)")
plt.ylabel("ax (mg)")
plt.subplot(3, 1, 2)
plt.plot(West001_Ground_time, West001_Ground_accY)
plt.title("Acceleration - Y @ West001 , Ground floor")
plt.xlabel("Time (Sec)")
plt.ylabel("ay (mg)")
plt.subplot(3, 1, 3)
plt.plot(West001_Ground_time, West001_Ground_accZ)
plt.title("Acceleration - Z @ West001 , Ground floor")
plt.xlabel("Time (Sec)")
plt.ylabel("az (mg)")
plt.show()


# Detrend Data
# داده های سنسورها حول صفر نیست بخاطر خطا در  تراز کردن سنسور

# detrend_East001_5th_accY = signal.detrend(East001_5th_accY, type="constant")
detrend_East001_5th_accY = (East001_5th_accY) - np.mean(East001_5th_accY)

plt.plot(East001_5th_time, detrend_East001_5th_accY)
plt.title("Detrend Acceleration - Y @ East001 , 5th floor")
plt.xlabel("Time (Sec)")
plt.ylabel("ay (mg)")
plt.show()

# Trim Data
t_start = 800
t_end = 1000
bounds_index = [t_start - East001_5th_time[0], t_end - East001_5th_time[0]] * Sample_Rate
trimed_East001_5th_accY = East001_5th_accY[bounds_index[0]: bounds_index[-1]]
trimed_East001_5th_time = East001_5th_time[bounds_index[0]: bounds_index[-1]]

plt.plot(trimed_East001_5th_time, trimed_East001_5th_accY)
plt.title("Trimed Acceleration - Y @ East001 , 5th floor")
plt.xlabel("Time (Sec)")
plt.ylabel("ay (mg)")
plt.show()
