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
   
    impact = ImpactHeuristic()
    routes, cost_per_route, total_cost, total_task = impact.generate_init_solution()
    print(f"=== The result fromm IMPACT ===")
    print(f"Total cost of each route: ${cost_per_route}")
    print(f"All routes: {total_task}")
    best_routes = total_task
    c = cost_per_route
    
    

    

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

