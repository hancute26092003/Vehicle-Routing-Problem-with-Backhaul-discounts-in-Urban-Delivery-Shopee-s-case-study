
import pandas as pd
import numpy as np
import math

def haversine_matrix():
    position = pd.read_excel('data_cood_0.xlsx', index_col=0, header=0)
    longitudes = position['y'].values
    latitudes = position['x'].values
    n = len(longitudes)


    # Transform degree to radian
    lat_rad = np.radians(latitudes)
    long_rad = np.radians(longitudes)


    # Create empty nxn matrix
    d = np.zeros((n, n))


    for i in range(n):
        for j in range(i + 1, n):              
            dLat = lat_rad[j] - lat_rad[i]
            dLong = long_rad[j] - long_rad[i]


            # Apply Haversine formula
            a = (math.sin(dLat / 2) ** 2 +
                 math.cos(lat_rad[i]) * math.cos(lat_rad[j]) * math.sin(dLong / 2) ** 2)
            c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
            R = 6371  
            distances = R * c


            # Save into the matrix
            d[i, j] = distances
            d[j, i] = distances  


    return d

print(haversine_matrix())
print()


from Data import readData
hub, weight, ready, deadline, x_cood, y_cood, dock, vehicle_type, task_dict= readData()

N = task_dict

#Set task with dummy task
N_dummy = N.copy()

h = {i: int(N[i]['hub']) for i in N}

A = {(i, j) for i in N for j in N if i != j}
A_dummy = {(i, j) for i in N_dummy for j in N_dummy if i != j}

d_hub = haversine_matrix()
distance_matrix = {
    (i, j): (d_hub[h[i]][h[j]] if i != "dummy_task" and j != "dummy_task" else 0)
    for i, j in A
}
#print(f"distance {distance_matrix}")

n = len(N)
print(n)
distance_matrix_nxn = np.zeros((n, n))
task_index = {task: idx for idx, task in enumerate(N)}
for (i, j), dist in distance_matrix.items():
    distance_matrix_nxn[task_index[i]][task_index[j]] = dist

print(distance_matrix_nxn)
