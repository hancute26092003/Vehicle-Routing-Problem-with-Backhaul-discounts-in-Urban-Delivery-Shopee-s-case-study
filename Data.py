import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import math


def readData():
    #Nhập data từ file excel gồm task, địa chỉ hub, thông số loại xe
    data_task = pd.read_excel(r'C:\Users\quynh\OneDrive - VietNam National University - HCM INTERNATIONAL UNIVERSITY\Desktop\Sem 2\Tam ca ba cô gái\Code\data_sample_0.xlsx')
    data_hub = pd.read_excel(r'C:\Users\quynh\OneDrive - VietNam National University - HCM INTERNATIONAL UNIVERSITY\Desktop\Sem 2\Tam ca ba cô gái\Code\data_cood_0.xlsx')
    data_vehicle = pd.read_excel(r'C:\Users\quynh\OneDrive - VietNam National University - HCM INTERNATIONAL UNIVERSITY\Desktop\Sem 2\Tam ca ba cô gái\Code\data_vehicle.xlsx')
    data_task_name = data_task.values.tolist()
    data_hub_name = data_hub.values.tolist()
    data_vehicle_name = data_vehicle.values.tolist()
    

    #Liên kết hub cần thực hiện task và địa chỉ của hub đó
    hub_coordinates = {data_hub_name[i][0]: (data_hub_name[i][1], data_hub_name[i][2], data_hub_name[i][3]) for i in range(len(data_hub_name))}
    #Liên kết loại xe lớn nhất dành cho task và weight của task đó
    biggest_vehicle = {data_vehicle_name[i][0]: (data_vehicle_name[i][1], data_vehicle_name[i][2], data_vehicle_name[i][3], data_vehicle_name[i][4], data_vehicle_name[i][5]) for i in range(len(data_vehicle_name))}
    fields = ["hub", "weight", "ready", "deadline"]
    task_dict = {}
    # attribute_vehicle = ["type_vehicle", "capacity", "unit_cost", "load_time", "unload_time"]
    for i  in range(len(data_task_name)):
        task_dict[i]= dict(zip(fields, data_task_name[i]))
        
        hub_id = task_dict[i]["hub"]
        if hub_id in hub_coordinates:
            task_dict[i]["x_cood"], task_dict[i]["y_cood"], task_dict[i]["dock"] = hub_coordinates[hub_id]
            
        #Dựa vào số lượng dock tại mỗi hub để chọn loại vehicle phù hợp để đảm bảo công suất của hub
        vehicle_id = task_dict[i]["dock"]
        if vehicle_id in biggest_vehicle:
            task_dict[i]["vehicle_type"], task_dict[i]["capacity"], task_dict[i]["unit cost"], task_dict[i]["load time"], task_dict[i]["unload time"] = biggest_vehicle[vehicle_id]  
        #print(task_dict[i]) #Nếu cần kiểm tra thì cho phép lệnh này hoạt động 

        #task_weight = task_dict[i]["weight"]
        # Kiểm tra weight của task với capacity của vehicle
        #for vehicle_info in biggest_vehicle.items():
            #capacity = vehicle_info[1][0]
            #if task_weight <= capacity:
                #task_dict[i]["vehicle type"] = vehicle_info[0]  # Lưu lại loại xe vào task_dict
    

    #List của từng attribute của task
    hub = []; weight = []; ready = []; deadline = []; x_cood=[]; y_cood=[]; dock=[]; vehicle_type = []
    for i in range(len(data_task_name)):
        hub.append(int(task_dict[i]["hub"]))
        weight.append(float(task_dict[i]["weight"])) 
        ready.append(float(task_dict[i]["ready"]))
        deadline.append(float(task_dict[i]["deadline"]))
        x_cood.append(float(task_dict[i]["x_cood"]))
        y_cood.append(float(task_dict[i]["y_cood"]))
        dock.append((int(task_dict[i]["dock"])))
        vehicle_type.append((int(task_dict[i]["vehicle_type"])))
    return hub, weight, ready, deadline, x_cood, y_cood, dock, vehicle_type, task_dict   

#print(readData())

def readDataHub():
    data_hub = pd.read_excel(r'C:\Users\quynh\OneDrive - VietNam National University - HCM INTERNATIONAL UNIVERSITY\Desktop\Sem 2\Tam ca ba cô gái\Code\data_cood_0.xlsx')
    data_hub_name = data_hub.values.tolist()
    #List của từng attribute của hub
    fields_hub = ["hub_no", "x_cood_hub", "y_cood_hub", "dock_hub"]
    hub_dict = {}
    hub_no = []; x_cood_hub = []; y_cood_hub = []; dock_hub = []
    for i in range(len(data_hub_name)):
        hub_dict[i] = dict(zip(fields_hub, data_hub_name[i]))
    for i in range(len(data_hub_name)):
        hub_no.append(int(hub_dict[i]["hub_no"]))
        x_cood_hub.append(float(hub_dict[i]["x_cood_hub"]))
        y_cood_hub.append(float(hub_dict[i]["y_cood_hub"]))
        dock_hub.append(int(hub_dict[i]["dock_hub"]))
    return hub_no, x_cood_hub, y_cood_hub, dock_hub, hub_dict

#print(readDataHub())

def createHubMap():
    position = pd.read_excel(r'data_cood_0.xlsx', index_col=0, header=0, usecols="A:D")
    x_hub = position['x']
    y_hub = position['y']
    
    # Plot the points
    plt.scatter(x_hub, y_hub)

    # Customize the plot (optional)
    plt.xlabel('X-axis')
    plt.ylabel('Y-axis')
    plt.title('Hub Map')

    for i in range(len(x_hub)):
        plt.annotate(f"Hub {i}", (x_hub[i], y_hub[i]), ha='center', va='bottom')
        
    # Display the plot
    plt.show()
#print(createHubMap())

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

def travelling_time():
    time_matrix = pd.read_excel('data_time_0.xlsx', index_col=0, header=0)
    time_matrix_value = time_matrix.values
    n = len(time_matrix_value)
    t = np.zeros((n, n))
    for i in range(n):
        for j in range(i+1, n):
            t[i,j] = time_matrix_value[i,j]
            t[j,i] = time_matrix_value[j,i]
    return t
#print(travelling_time())




def readVehicle():
    #Nhập data từ file excel thông số loại xe
    data_vehicle = pd.read_excel(r'C:\Users\quynh\OneDrive - VietNam National University - HCM INTERNATIONAL UNIVERSITY\Desktop\Sem 2\Tam ca ba cô gái\Code\data_vehicle.xlsx')
    data_vehicle_name = data_vehicle.values.tolist()
    n = len(data_vehicle_name)
    attribute_vehicle = ["no","type_vehicle", "capacity", "unit_cost", "load_time", "unload_time"]
    vehicle = {}
    for i  in range(n):
        vehicle[i]= dict(zip(attribute_vehicle, data_vehicle_name[i]))
    no =[]; m = []; Q = []; c = []; t_load = []; t_unload = []
    for i in range(n):
        no.append(int(vehicle[i]["no"]))
        m.append(int(vehicle[i]["type_vehicle"]))
        Q.append(int(vehicle[i]["capacity"]))
        c.append(int(vehicle[i]["unit_cost"]))
        t_load.append(int(vehicle[i]["load_time"]))
        t_unload.append(int(vehicle[i]["unload_time"]))
    return no,m, Q, c, t_load, t_unload, vehicle
#readVehicle())