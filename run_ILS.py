import numpy as np
from all_model import Master_Problem
from utils import ILS, ImpactHeuristic
import time
from Data import readData, haversine_matrix, travelling_time, readVehicle
from CG_DBP import column_generation
#from CG_NBP import column_generation
hub, weight, ready, deadline, x_cood, y_cood, dock, vehicle_type, task_dict= readData()
no, m, Q, c, t_load, t_unload, vehicle= readVehicle()

def main():
    start_time = time.time()
    
# ------------ Find initial feasible routes ------------#
    ils = ILS()
    best_routes, best_cost = ils.iterated_local_search(iterations=10)
    print(f"=== The result fromm ILS ===")
    print(f"Total cost of all routes: ${best_cost:.2f}")
    print(f"All routes: {best_routes}")
    
   
    
    
# ----------- Get total distance of initial routes -----#
    for i, route in enumerate(best_routes):
        distance = ils.calculate_distance(route)
        cost = ils.calculate_cost(route)
        print(f"\nRoute {i + 1}: {route}")
        print(f"  - Distance: {distance:.2f} km")
        print(f"  - Cost: ${cost:.2f}")

    # Tính cost cho các route để truyền vào Master_Problem
    c = [ils.calculate_cost(route) for route in best_routes]
    print(f"\nCost: {c}")

# ----------- Create initial Master Problem -------
    
    MP = Master_Problem(c, best_routes, modelo=None)
    MP.build_model()
    print(f"=== MASTER PROBLEM IS SUCCESSFUL ===")
    MP.RelaxOptimize()
    duals = MP.getDuals()
    
    print(f"\nThe duals are: {duals}")
    


# ------------- Run Branch and Pric ----------#
    
    MP_sol = column_generation(duals)
    end_time = time.time()
    print("RUN TIME:{} seg.".format(end_time - start_time))
    #MP_sol.RelaxOptimize()
    #print(MP_sol.relax_modelo.getAttr("X"))
    #print(MP_sol.relax_modelo.ObjVal)
   
if __name__ == "__main__":
    main()

