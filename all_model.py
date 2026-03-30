import gurobipy as gp
from Data import *
import copy

class Sub_problem_SP0:
    def __init__(self,duals,modelo=None):
        hub, weight, ready, deadline, x_cood, y_cood, dock, vehicle_type, task_dict = readData()
        hub_no, x_cood_hub, y_cood_hub, dock_hub, hub_dict = readDataHub()
        no, m, Q, c, t_load, t_unload, vehicle = readVehicle()

        #Parameter:
        self.alpha = 0.5 #Discount rate
        self.BigM = 99999999
        self.omega = 20
        
        #Set task
        self.N = task_dict
        self.Np = {}
        self.Nd = {}
        for i in range(len(self.N)):
            if self.N[i]['weight'] != 0:
                if self.N[i]['weight'] > 0:
                    self.Np[i] = self.N[i]
                else:
                    self.Nd[i] = self.N[i]
        
        #Add dummy task
        self.N_dummy = self.N.copy()
        self.Np_dummy = self.Np.copy()
        self.Nd_dummy = self.Nd.copy()
        self.dummy_task_attribute = {"hub": len(self.N)+1, "weight":0}
        self.Np_dummy['dummy_task'] = self.dummy_task_attribute
        self.Nd_dummy['dummy_task'] = self.dummy_task_attribute
        self.N_dummy['dummy_task'] = self.dummy_task_attribute

        #Set arc
        self.A = {(i, j) for i in self.N for j in self.N if i != j}
        self.A_dummy = {(i, j) for i in self.N_dummy for j in self.N_dummy if i != j}
        
        #Set
        self.H = hub
        self.W = weight
        self.E = ready
        self.D = deadline

        #Vehicle attribute
        self.M = vehicle
        self.type_vehicle = {m: self.M[m]['type_vehicle'] for m in self.M}
        self.Q = {m: self.M[m]['capacity'] for m in self.M}
        self.c = {m: self.M[m]['unit_cost'] for m in self.M}
        self.t0 = {m: self.M[m]['load_time'] for m in self.M}
        self.t1 = {m: self.M[m]['unload_time'] for m in self.M}

        #Task attribute
        self.h = {i: int(self.N[i]['hub']) for i in self.N}
        self.w = {i: self.N[i]['weight'] for i in self.N}
        self.e = {i: self.N[i]['ready'] for i in self.N}
        self.l = {i: self.N[i]['deadline'] for i in self.N}
        self.v = {i: self.N[i]['vehicle_type'] for i in self.N}
        
        dummy_task = 'dummy_task'
        self.h[dummy_task] = self.dummy_task_attribute["hub"]
        self.w[dummy_task] = self.dummy_task_attribute["weight"]
        
        "-------------------------------Input distances & time------------------------"
        self.d_hub = haversine_matrix()
        self.distance_matrix = {
            (i,j): (self.d_hub[self.h[i]][self.h[j]] if i != 'dummy_task' and j != 'dummy_task' else 0)
            for (i,j) in self.A_dummy
        }
       
        

        self.t_hub = travelling_time()
        self.time_matrix = {
            (i,j):(self.t_hub[self.h[i]][self.h[j]] if i != 'dummy_task' and j != 'dummy_task' else 0)
            for (i,j) in self.A_dummy
        }
       
        self.d = {}
        self.t = {}
        for (i,j) in self.A_dummy:
            self.d[i,j] = self.distance_matrix[i,j]
            self.t[i,j] = self.time_matrix[i,j]
        "-------------------------Duals-------------------------------------------------"
        self.duals = duals
      


        "-------------------------"
        if modelo == None:
            self.modelo = gp.Model("Sub_Problem_SP0")
        else:
            self.modelo = self.modelo.copy()

    def update_model(self):
        self.u = {}
        for var in self.modelo.getVars():
            ix = var.index
            varName = "done task[{}]".format(ix)
            self.u[ix] = self.modelo.getVarByName(varName)
        self.modelo.update()

    def build_model(self):
        "--------------------Decision variables-------------------"
        self.u = {}
        for i in self.N_dummy:
            self.u[i] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"u_{i}")
        self.x = {}
        for i in self.N_dummy:
            for j in self.N_dummy:
                self.x[i,j] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"x_{i}_{j}")
        self.y = {}
        for m in self.M:
            self.y[m] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"y_{m}")
        self.beta = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"discount") #Applu cost
        "----------------------Continuous variables-----------------"
        self.T_d = {}
        self.T_l = {}
        for i in self.N:
            self.T_d[i] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"T_d_{i}")
            self.T_l[i] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"T_l_{i}")
        self.q_d = {}
        self.q_l = {}
        for i in self.N_dummy:
            self.q_d[i] = self.modelo.addVar(vtype=gp.GRB.CONTINUOUS, name=f"q_d_{i}")
            self.q_l[i] = self.modelo.addVar(vtype=gp.GRB.CONTINUOUS, name=f"q_l_{i}")
        "-----------------------Operational price-------------------"
        self.au_1 = {}
        for m in self.M:
            self.au_1[m] = {}
            for (i,j) in self.A:
                self.au_1[m][i,j] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"au_1_{m}_{i}_{j}")
        
        for m in self.M:
            for (i,j) in self.A:
                self.modelo.addConstr(self.au_1[m][i,j] <= self.y[m], name=f"con1_price_{i}_{j}_{m}")
                self.modelo.addConstr(self.au_1[m][i,j] <= self.x[i,j], name=f"con2_price_{i}_{j}_{m}")
                self.modelo.addConstr(self.au_1[m][i,j] >= self.y[m] + self.x[i,j] - 1, name=f"con3_price_{i}_{j}_{m}")
        
        self.p1 = gp.quicksum(self.c[m] * self.d[i,j] * self.au_1[m][i,j] for m in self.M for (i,j) in self.A)
        self.au_2 = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"au_2")
        self.modelo.addConstr(self.au_2 <= self.BigM * self.beta, name=f"con5_price")
        self.modelo.addConstr(self.au_2 <= self.p1 + self.BigM * (1 - self.beta), name=f"con6_price")
        self.modelo.addConstr(self.au_2 >= self.p1 - self.BigM * (1 - self.beta), name=f"con7_price")
        self.p_r = self.p1 - self.alpha * self.au_2
       

        "---------------------------Routing constraint-------------------------------"
        #Constraint 8:
        self.modelo.addConstr(self.beta <= gp.quicksum(self.u[i] for i in self.Nd), name=f"con8.1")
        self.modelo.addConstr(self.beta <= gp.quicksum(self.u[i] for i in self.Np), name=f"con8.2")

        #Constraint 9:
        for i in self.N:
            self.modelo.addConstr(gp.quicksum(self.x[i,j] for j in self.N) == gp.quicksum(self.x[j,i] for j in self.N), name=f"con9.1_{i}")

        #Constraint 10:
        for j in self.N:
            if j != 0:
                self.modelo.addConstr(gp.quicksum(self.x[i,j] for i in self.N if (i,j) in self.A if j != 0) == self.u[j], name=f"con10.1_{j}")
        
        self.modelo.addConstr(gp.quicksum(self.u[i] for i in self.N) == len(self.N), name=f"con10.2")

        for i in self.N:
            for j in self.N:
                if i != j:
                    self.modelo.addConstr(self.x[i,j] + self.x[j,i] <= 1, name=f"con_10.3_subtour_elimination_{i}_{j}")

        #Constraint 11:
        self.modelo.addConstr(gp.quicksum(self.x[0,i] for i in self.Nd) == 1, name=f"con11.1")
        self.modelo.addConstr(gp.quicksum(self.x[i,0] for i in self.Np) == 1, name=f"con11.2")

        #Constraint 12:
        self.modelo.addConstr(gp.quicksum(self.x['dummy_task', i] for i in self.Nd)==0, name=f"con12.1")
        self.modelo.addConstr(gp.quicksum(self.x[i,'dummy_task'] for i in self.Np)==0, name=f"con12.2")

        #Constraint 13:
        self.modelo.addConstr(gp.quicksum(self.x[i,j] for i in self.Nd for j in self.Np) <=1 , name=f"con13.1")
        self.modelo.addConstr(gp.quicksum(self.x[i,j] for i in self.Np for j in self.Nd) == 0, name=f"con13.2")

        #Constraint 14:
        self.modelo.addConstr(gp.quicksum(self.h[i] * self.x[i,'dummy_task'] for i in self.Nd)
                                - gp.quicksum(self.h[i] * self.x['dummy_task', i] for i in self.Np)
                                <= self.BigM * (self.x[0, 'dummy_task'] + self.x['dummy_task', 0]), name=f"con14")
        
        #Constraint 15:
        self.modelo.addConstr(gp.quicksum(self.h[i] * self.x[i, 'dummy_task'] for i in self.Nd)
                              - gp.quicksum(self.h[i] * self.x['dummy_task', i] for i in self.Np)
                              >= self.BigM *(self.x[0, 'dummy_task'] + self.x['dummy_task', 0]), name=f"con15")
        
        "-----------------------------Loading constraint--------------------------------------------------------------"

        #Constraint 16:
        self.modelo.addConstr(self.q_l['dummy_task'] == 0, name=f"con16.1")
        self.modelo.addConstr(self.q_d['dummy_task'] == 0, name=f"con16.2")

        #Constraint 17:
        self.modelo.addConstr(self.q_d[0] <= (gp.quicksum(self.Q[m] * self.y[m] for m in self.M)), name=f"con17.1")
        self.modelo.addConstr(self.q_l[0] <= (gp.quicksum(self.Q[m] * self.y[m] for m in self.M)), name=f"con17.2")

        #Constraint 18:
        self.modelo.addConstr(self.q_d[0] == (gp.quicksum((abs(self.w[i])) * self.u[i] for i in self.Np)), name=f"con18.1")
        self.modelo.addConstr(self.q_l[0] == gp.quicksum((abs(self.w[i])) * self.u[i] for i in self.Nd), name=f"con18.2")

        #Constraint 19:        
        for (i,j) in self.A:
            if i != 0:
                self.modelo.addConstr(self.q_d[j] >= self.q_d[i] + self.w[i] - self.BigM * (1 - self.x[i,j]), name=f"con19_{i}_{j}")        #Constraint 20:
        for (i,j) in self.A:
            if j != 0:
                self.modelo.addConstr(self.q_l[j] <= self.q_l[i] - self.w[j] + self.BigM * (1 - self.x[i,j]), name=f"con20_{i}_{j}")


        "-------------------------------------------Timing constraint------------------------------"
        #Constraint 21
        for i in self.Nd:
            self.modelo.addConstr(self.T_l[0] >= self.u[i] * self.e[i], name=f"con21.1_{i}")
            self.modelo.addConstr(self.T_d[i] <= self.u[i] * self.l[i] + self.BigM * (1 - self.u[i]), name=f"con21.2_{i}")

        #Constraint 22
        for i in self.Np:
            self.modelo.addConstr(self.T_l[i] >= self.u[i] * self.e[i], name=f"con22.1_{i}")
            self.modelo.addConstr(self.T_d[0] <= self.l[i] + self.BigM * (1 - self.u[i]), name=f"con22.2_{i}")
        
        #Constraint 23
        for i in self.Nd:
            self.modelo.addConstr(self.T_d[i] >= self.T_l[0], name=f"con23_{i}")
       
        #Constraint 24
        for (i,j) in self.A:
            if self.h[i] != self.h[j]:
                self.modelo.addConstr(self.T_l[i] + self.t[i,j] - self.T_d[j] - self.BigM * (1 - self.x[i,j]) <= 0, name=f"con24.1_{i}_{j}")
                self.modelo.addConstr(self.T_l[i] + self.t[i,j] - self.T_d[j] + self.BigM * (1 - self.x[i,j]) >= 0, name=f"con24.2_{i}_{j}")

        #Constraint 25
        for (i,j) in self.A:
            if self.h[i] == self.h[j]:
                self.modelo.addConstr(self.T_d[i] - self.T_d[j] - self.BigM * (1 - self.x[i,j]) <= 0, name=f"con25.1_{i}_{j}")
                self.modelo.addConstr(self.T_d[i] - self.T_d[j] + self.BigM * (1 - self.x[i,j]) >= 0, name=f"con25.2_{i}_{j}")

        #Constraint 26
        for i in self.Nd:
            self.modelo.addConstr(self.T_l[i] >= self.T_d[i] + gp.quicksum(self.y[m] * self.t1[m] for m in self.M), name=f"con26.1_{i}")
            self.modelo.addConstr(self.T_l[i] <= self.T_d[i] + gp.quicksum(self.y[m] * self.t1[m] for m in self.M) + self.omega, name=f"con26.2_{i}")
        for i in self.Np:
            self.modelo.addConstr(self.T_l[i] >= self.T_d[i] + gp.quicksum(self.y[m] * self.t0[m] for m in self.M), name=f"con26.3_{i}")
            self.modelo.addConstr(self.T_l[i] <= self.T_d[i] + gp.quicksum(self.y[m] * self.t0[m] for m in self.M) + self.omega, name=f"con26.4_{i}")

        #Constraint 27
        self.modelo.addConstr(self.T_l[0] >= self.T_d[0] + gp.quicksum(self.y[m] * self.t0[m] for m in self.M)
                                    - self.BigM * (2 - self.u['dummy_task'] - self.beta), name=f"con27.1_{i}")
        self.modelo.addConstr(self.T_l[0] <= self.T_d[0] + gp.quicksum(self.y[m] * self.t0[m] for m in self.M) + self.omega
                                    + self.BigM * (2 - self.u['dummy_task'] - self.beta), name=f"con27.2_{i}")

        "-------------------------------------------Limiting constraint------------------"
        #Constraint 28
        self.modelo.addConstr(gp.quicksum(self.y[m] for m in self.M) == 1, name=f"con28")

        #Constraint 29
        for i in self.N:
            if i != 0:
                self.modelo.addConstr((gp.quicksum(m * self.y[m] for m in self.M))
                            <= self.v[i] * self.u[i] + self.BigM * (1 - self.u[i]), name=f"con29_{i}")
            

            "-----------------------Objective-------------------------------------------------------------"
            self.modelo.setObjective(
                        self.p_r - gp.quicksum(self.duals[i] * self.u[i] for i in self.N), sense=gp.GRB.MINIMIZE,
                    )
            
            self.modelo.update()
            self.modelo.Params.OutputFlag = 0
           

    def optimze(self):
        self.modelo.optimize()
        

    def getSolution(self):
        return self.modelo.getAttr("X")

    def show(self):
            self.segments = []
            for m in self.M:
                if self.y[m].X == 1:
                    for (i,j) in self.A:
                        if i!= 'dummy_task':
                            if j != 'dummy_task':
                                #print(f"from {i} to {j} takes {t[i,j]} minutes")
                                if self.x[i,j].X == 1:
                                    #print(f"The truck type {m+1} does the task {i} to the task {j}")
                                    self.segments.append((i, j))                               
            #print(self.segments)
            return self.segments
    
    def find_all_routes(self):
        self.routes_dict = {} 
        self.tasks_copy = self.segments.copy() 
        route_id = 1  
        self.R_input = {} 
        self.p = {}
        while self.tasks_copy:  
            self.route = [0] 
            self.cost_each_route = 0  

            while self.tasks_copy:
                self.next_segment = next(
                    ((start, end) for start, end in self.tasks_copy if self.route[-1] in (start, end)),
                    None
                )
                if not self.next_segment: 
                    break

                i, j = self.next_segment
                self.segment_cost = ((1 - self.alpha) * gp.quicksum(self.c[m] * self.d[i, j] for m in self.M if self.y[m].X == 1)).getValue()
                self.cost_each_route += self.segment_cost

                self.tasks_copy.remove(self.next_segment)
                self.route.append(j if self.route[-1] == i else i)

                # Dừng lại nếu route quay về depot
                if self.route[-1] == 0:
                    break

            # Lưu route 
            if self.route[-1] == 0:  
                self.routes_dict[route_id] = {
                    "route": self.route,
                    "cost": self.cost_each_route
                }
                self.R_input[route_id] = self.route
                self.p[route_id] = self.cost_each_route
                #print(f"Added Route_{route_id}: {self.route} with cost {cost_each_route}")
                route_id += 1  # Tăng ID cho route tiếp theo

        return self.routes_dict, self.R_input, self.p
    
class Sub_problem_SP4:
    def __init__(self,duals,modelo=None):
        hub, weight, ready, deadline, x_cood, y_cood, dock, vehicle_type, task_dict = readData()
        hub_no, x_cood_hub, y_cood_hub, dock_hub, hub_dict = readDataHub()
        no, m, Q, c, t_load, t_unload, vehicle = readVehicle()

        #Parameter:
        self.alpha = 0.5 #Discount rate
        self.BigM = 99999999
        self.omega = 0
        
        #Set task
        self.N = task_dict
        self.Np = {}
        self.Nd = {}
        for i in range(len(self.N)):
            if self.N[i]['weight'] != 0:
                if self.N[i]['weight'] > 0:
                    self.Np[i] = self.N[i]
                else:
                    self.Nd[i] = self.N[i]
        
        #Add dummy task
        self.N_dummy = self.N.copy()
        self.Np_dummy = self.Np.copy()
        self.Nd_dummy = self.Nd.copy()
        self.dummy_task_attribute = {"hub": len(self.N)+1, "weight":0}
        self.Np_dummy['dummy_task'] = self.dummy_task_attribute
        self.Nd_dummy['dummy_task'] = self.dummy_task_attribute
        self.N_dummy['dummy_task'] = self.dummy_task_attribute

        #Set arc
        self.A = {(i, j) for i in self.N for j in self.N if i != j}
        self.A_dummy = {(i, j) for i in self.N_dummy for j in self.N_dummy if i != j}
        
        #Set
        self.H = hub
        self.W = weight
        self.E = ready
        self.D = deadline

        #Vehicle attribute
        self.M = vehicle
        self.type_vehicle = {m: self.M[m]['type_vehicle'] for m in self.M}
        self.Q = {m: self.M[m]['capacity'] for m in self.M}
        self.c = {m: self.M[m]['unit_cost'] for m in self.M}
        self.t0 = {m: self.M[m]['load_time'] for m in self.M}
        self.t1 = {m: self.M[m]['unload_time'] for m in self.M}

        #Task attribute
        self.h = {i: int(self.N[i]['hub']) for i in self.N}
        self.w = {i: self.N[i]['weight'] for i in self.N}
        self.e = {i: self.N[i]['ready'] for i in self.N}
        self.l = {i: self.N[i]['deadline'] for i in self.N}
        self.v = {i: self.N[i]['vehicle_type'] for i in self.N}
        
        dummy_task = 'dummy_task'
        self.h[dummy_task] = self.dummy_task_attribute["hub"]
        self.w[dummy_task] = self.dummy_task_attribute["weight"]
        
        "-------------------------------Input distances & time------------------------"
        self.d_hub = haversine_matrix()
        self.distance_matrix = {
            (i,j): (self.d_hub[self.h[i]][self.h[j]] if i != 'dummy_task' and j != 'dummy_task' else 0)
            for (i,j) in self.A_dummy
        }
       
        

        self.t_hub = travelling_time()
        self.time_matrix = {
            (i,j):(self.t_hub[self.h[i]][self.h[j]] if i != 'dummy_task' and j != 'dummy_task' else 0)
            for (i,j) in self.A_dummy
        }
       
        self.d = {}
        self.t = {}
        for (i,j) in self.A_dummy:
            self.d[i,j] = self.distance_matrix[i,j]
            self.t[i,j] = self.time_matrix[i,j]
        "-------------------------Duals-------------------------------------------------"
        self.duals = duals
        


        "-------------------------"
        if modelo == None:
            self.modelo = gp.Model("Sub_Problem_SP0")
        else:
            self.modelo = self.modelo.copy()

    def update_model(self):
        self.u = {}
        for var in self.modelo.getVars():
            ix = var.index
            varName = "done task[{}]".format(ix)
            self.u[ix] = self.modelo.getVarByName(varName)
        self.modelo.update()

    def build_model(self):
        "--------------------Decision variables-------------------"
        self.u = {}
        for i in self.N_dummy:
            self.u[i] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"u_{i}")
        self.x = {}
        for i in self.N_dummy:
            for j in self.N_dummy:
                self.x[i,j] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"x_{i}_{j}")
        self.y = {}
        for m in self.M:
            self.y[m] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"y_{m}")
        self.beta = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"discount") #Applu cost
        "----------------------Continuous variables-----------------"
        self.T_d = {}
        self.T_l = {}
        for i in self.N:
            self.T_d[i] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"T_d_{i}")
            self.T_l[i] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"T_l_{i}")
        self.q_d = {}
        self.q_l = {}
        for i in self.N_dummy:
            self.q_d[i] = self.modelo.addVar(vtype=gp.GRB.CONTINUOUS, name=f"q_d_{i}")
            self.q_l[i] = self.modelo.addVar(vtype=gp.GRB.CONTINUOUS, name=f"q_l_{i}")
        "-----------------------Operational price-------------------"
        self.au_1 = {}
        for m in self.M:
            self.au_1[m] = {}
            for (i,j) in self.A:
                self.au_1[m][i,j] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"au_1_{m}_{i}_{j}")
        
        for m in self.M:
            for (i,j) in self.A:
                self.modelo.addConstr(self.au_1[m][i,j] <= self.y[m], name=f"con1_price_{i}_{j}_{m}")
                self.modelo.addConstr(self.au_1[m][i,j] <= self.x[i,j], name=f"con2_price_{i}_{j}_{m}")
                self.modelo.addConstr(self.au_1[m][i,j] >= self.y[m] + self.x[i,j] - 1, name=f"con3_price_{i}_{j}_{m}")
        
        self.p1 = gp.quicksum(self.c[m] * self.d[i,j] * self.au_1[m][i,j] for m in self.M for (i,j) in self.A)
        
        self.p_r = self.p1 - self.alpha * self.p1
       
        "---------------------------Adjusting constraint-------------------------------"
        self.modelo.addConstr(gp.quicksum(self.x[i,'dummy_task'] for i in self.N) == 0, name=f"con_add_1")
        self.modelo.addConstr(gp.quicksum(self.x[i,j] for i in self.Nd for j in self.Np) == 1, name=f"con_add_2")

        "---------------------------Routing constraint-------------------------------"
        #Constraint 9:
        for i in self.N:
            self.modelo.addConstr(gp.quicksum(self.x[i,j] for j in self.N) == gp.quicksum(self.x[j,i] for j in self.N), name=f"con9.1_{i}")

        #Constraint 10:
        for j in self.N:
            if j != 0:
                self.modelo.addConstr(gp.quicksum(self.x[i,j] for i in self.N if (i,j) in self.A if j != 0) == self.u[j], name=f"con10.1_{j}")
        
        self.modelo.addConstr(gp.quicksum(self.u[i] for i in self.N) == len(self.N), name=f"con10.2")

        for i in self.N:
            for j in self.N:
                if i != j:
                    self.modelo.addConstr(self.x[i,j] + self.x[j,i] <= 1, name=f"con_10.3_subtour_elimination_{i}_{j}")

        #Constraint 11:
        self.modelo.addConstr(gp.quicksum(self.x[0,i] for i in self.Nd) == 1, name=f"con11.1")
        self.modelo.addConstr(gp.quicksum(self.x[i,0] for i in self.Np) == 1, name=f"con11.2")
        

        "-----------------------------Loading constraint--------------------------------------------------------------"

        #Constraint 16:
        self.modelo.addConstr(self.q_l['dummy_task'] == 0, name=f"con16.1")
        self.modelo.addConstr(self.q_d['dummy_task'] == 0, name=f"con16.2")

        #Constraint 17:
        self.modelo.addConstr(self.q_d[0] <= (gp.quicksum(self.Q[m] * self.y[m] for m in self.M)), name=f"con17.1")
        self.modelo.addConstr(self.q_l[0] <= (gp.quicksum(self.Q[m] * self.y[m] for m in self.M)), name=f"con17.2")

        #Constraint 18:
        self.modelo.addConstr(self.q_d[0] == (gp.quicksum((abs(self.w[i])) * self.u[i] for i in self.Np)), name=f"con18.1")
        self.modelo.addConstr(self.q_l[0] == gp.quicksum((abs(self.w[i])) * self.u[i] for i in self.Nd), name=f"con18.2")

        #Constraint 19:        
        for (i,j) in self.A:
            if i != 0:
                self.modelo.addConstr(self.q_d[j] >= self.q_d[i] + self.w[i] - self.BigM * (1 - self.x[i,j]), name=f"con19_{i}_{j}")        #Constraint 20:
        
        #Constraint 20:
        for (i,j) in self.A:
            if j != 0:
                self.modelo.addConstr(self.q_l[j] <= self.q_l[i] - self.w[j] + self.BigM * (1 - self.x[i,j]), name=f"con20_{i}_{j}")


        "-------------------------------------------Timing constraint------------------------------"
        #Constraint 21
        for i in self.Nd:
            self.modelo.addConstr(self.T_l[0] >= self.u[i] * self.e[i], name=f"con21.1_{i}")
            self.modelo.addConstr(self.T_d[i] <= self.u[i] * self.l[i] + self.BigM * (1 - self.u[i]), name=f"con21.2_{i}")

        #Constraint 22
        for i in self.Np:
            self.modelo.addConstr(self.T_l[i] >= self.u[i] * self.e[i], name=f"con22.1_{i}")
            self.modelo.addConstr(self.T_d[0] <= self.l[i] + self.BigM * (1 - self.u[i]), name=f"con22.2_{i}")
        
        #Constraint 23
        for i in self.Nd:
            self.modelo.addConstr(self.T_d[i] >= self.T_l[0], name=f"con23_{i}")
       
        #Constraint 24
        for (i,j) in self.A:
            if self.h[i] != self.h[j]:
                self.modelo.addConstr(self.T_l[i] + self.t[i,j] - self.T_d[j] - self.BigM * (1 - self.x[i,j]) <= 0, name=f"con24.1_{i}_{j}")
                self.modelo.addConstr(self.T_l[i] + self.t[i,j] - self.T_d[j] + self.BigM * (1 - self.x[i,j]) >= 0, name=f"con24.2_{i}_{j}")

        #Constraint 25
        for (i,j) in self.A:
            if self.h[i] == self.h[j]:
                self.modelo.addConstr(self.T_d[i] - self.T_d[j] - self.BigM * (1 - self.x[i,j]) <= 0, name=f"con25.1_{i}_{j}")
                self.modelo.addConstr(self.T_d[i] - self.T_d[j] + self.BigM * (1 - self.x[i,j]) >= 0, name=f"con25.2_{i}_{j}")

        #Constraint 26
        for i in self.Nd:
            self.modelo.addConstr(self.T_l[i] >= self.T_d[i] + gp.quicksum(self.y[m] * self.t1[m] for m in self.M), name=f"con26.1_{i}")
            self.modelo.addConstr(self.T_l[i] <= self.T_d[i] + gp.quicksum(self.y[m] * self.t1[m] for m in self.M) + self.omega, name=f"con26.2_{i}")
        for i in self.Np:
            self.modelo.addConstr(self.T_l[i] >= self.T_d[i] + gp.quicksum(self.y[m] * self.t0[m] for m in self.M), name=f"con26.3_{i}")
            self.modelo.addConstr(self.T_l[i] <= self.T_d[i] + gp.quicksum(self.y[m] * self.t0[m] for m in self.M) + self.omega, name=f"con26.4_{i}")

        

        "-------------------------------------------Limiting constraint------------------"
        #Constraint 28
        self.modelo.addConstr(gp.quicksum(self.y[m] for m in self.M) == 1, name=f"con28")

        #Constraint 29
        for i in self.N:
            if i != 0:
                self.modelo.addConstr((gp.quicksum(m * self.y[m] for m in self.M))
                            <= self.v[i] * self.u[i] + self.BigM * (1 - self.u[i]), name=f"con29_{i}")
            
       
            "-----------------------Objective-------------------------------------------------------------"
            self.modelo.setObjective(
                        self.p_r - gp.quicksum(self.duals[i] * self.u[i] for i in self.N), sense=gp.GRB.MINIMIZE,
                    )
            
            self.modelo.update()
            self.modelo.Params.OutputFlag = 0
           

    def optimze(self):
        self.modelo.optimize()
        

    def getSolution(self):
        return self.modelo.getAttr("X")

    
    def show(self):
        self.segments = []
        for m in self.M:
            if self.y[m].X == 1:
                for (i,j) in self.A:
                    if i!= 'dummy_task':
                        if j != 'dummy_task':
                            #print(f"from {i} to {j} takes {t[i,j]} minutes")
                            if self.x[i,j].X == 1:
                                #print(f"The truck type {m+1} does the task {i} to the task {j}")
                                self.segments.append((i, j))                               
        #print(self.segments)
        return self.segments
    
    
    def find_all_routes(self):
        self.routes_dict = {} 
        self.tasks_copy = self.segments.copy() 
        route_id = 1  
        self.R_input = {}
        self.p = {}
        while self.tasks_copy:  
            self.route = [0] 
            self.cost_each_route = 0  

            while self.tasks_copy:
                self.next_segment = next(
                    ((start, end) for start, end in self.tasks_copy if self.route[-1] in (start, end)),
                    None
                )
                if not self.next_segment: 
                    break

                i, j = self.next_segment
                self.segment_cost = ((1 - self.alpha) * gp.quicksum(self.c[m] * self.d[i, j] for m in self.M if self.y[m].X == 1)).getValue()
                self.cost_each_route += self.segment_cost

                self.tasks_copy.remove(self.next_segment)
                self.route.append(j if self.route[-1] == i else i)

                # Dừng lại nếu route quay về depot
                if self.route[-1] == 0:
                    break

            # Lưu route 
            if self.route[-1] == 0:  
                self.routes_dict[route_id] = {
                    "route": self.route,
                    "cost": self.cost_each_route
                }
                self.R_input[route_id] = self.route
                self.p[route_id] = self.cost_each_route
                #print(f"Added Route_{route_id}: {self.route} with cost {cost_each_route}")
                route_id += 1  # Tăng ID cho route tiếp theo

        return self.routes_dict, self.R_input, self.p
    
class Sub_problem_SP3:
    def __init__(self,duals,modelo=None):
        hub, weight, ready, deadline, x_cood, y_cood, dock, vehicle_type, task_dict = readData()
        hub_no, x_cood_hub, y_cood_hub, dock_hub, hub_dict = readDataHub()
        no, m, Q, c, t_load, t_unload, vehicle = readVehicle()

        #Parameter:
        self.alpha = 0.5 #Discount rate
        self.BigM = 99999999
        self.omega = 0
        
        #Set task
        self.N = task_dict
        self.Np = {}
        self.Nd = {}
        for i in range(len(self.N)):
            if self.N[i]['weight'] != 0:
                if self.N[i]['weight'] > 0:
                    self.Np[i] = self.N[i]
                else:
                    self.Nd[i] = self.N[i]
        
        #Add dummy task
        self.N_dummy = self.N.copy()
        self.Np_dummy = self.Np.copy()
        self.Nd_dummy = self.Nd.copy()
        self.dummy_task_attribute = {"hub": len(self.N)+1, "weight":0}
        self.Np_dummy['dummy_task'] = self.dummy_task_attribute
        self.Nd_dummy['dummy_task'] = self.dummy_task_attribute
        self.N_dummy['dummy_task'] = self.dummy_task_attribute

        #Set arc
        self.A = {(i, j) for i in self.N for j in self.N if i != j}
        self.A_dummy = {(i, j) for i in self.N_dummy for j in self.N_dummy if i != j}
        
        #Set
        self.H = hub
        self.W = weight
        self.E = ready
        self.D = deadline

        #Vehicle attribute
        self.M = vehicle
        self.type_vehicle = {m: self.M[m]['type_vehicle'] for m in self.M}
        self.Q = {m: self.M[m]['capacity'] for m in self.M}
        self.c = {m: self.M[m]['unit_cost'] for m in self.M}
        self.t0 = {m: self.M[m]['load_time'] for m in self.M}
        self.t1 = {m: self.M[m]['unload_time'] for m in self.M}

        #Task attribute
        self.h = {i: int(self.N[i]['hub']) for i in self.N}
        self.w = {i: self.N[i]['weight'] for i in self.N}
        self.e = {i: self.N[i]['ready'] for i in self.N}
        self.l = {i: self.N[i]['deadline'] for i in self.N}
        self.v = {i: self.N[i]['vehicle_type'] for i in self.N}
        
        dummy_task = 'dummy_task'
        self.h[dummy_task] = self.dummy_task_attribute["hub"]
        self.w[dummy_task] = self.dummy_task_attribute["weight"]
        
        "-------------------------------Input distances & time------------------------"
        self.d_hub = haversine_matrix()
        self.distance_matrix = {
            (i,j): (self.d_hub[self.h[i]][self.h[j]] if i != 'dummy_task' and j != 'dummy_task' else 0)
            for (i,j) in self.A_dummy
        }
       
        

        self.t_hub = travelling_time()
        self.time_matrix = {
            (i,j):(self.t_hub[self.h[i]][self.h[j]] if i != 'dummy_task' and j != 'dummy_task' else 0)
            for (i,j) in self.A_dummy
        }
       
        self.d = {}
        self.t = {}
        for (i,j) in self.A_dummy:
            self.d[i,j] = self.distance_matrix[i,j]
            self.t[i,j] = self.time_matrix[i,j]
        "-------------------------Duals-------------------------------------------------"
        self.duals = duals
  
        "-------------------------"
        if modelo == None:
            self.modelo = gp.Model("Sub_Problem_SP0")
        else:
            self.modelo = self.modelo.copy()

    def update_model(self):
        self.u = {}
        for var in self.modelo.getVars():
            ix = var.index
            varName = "done task[{}]".format(ix)
            self.u[ix] = self.modelo.getVarByName(varName)
        self.modelo.update()

    def build_model(self):
        "--------------------Decision variables-------------------"
        self.u = {}
        for i in self.N_dummy:
            self.u[i] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"u_{i}")
        self.x = {}
        for i in self.N_dummy:
            for j in self.N_dummy:
                self.x[i,j] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"x_{i}_{j}")
        self.y = {}
        for m in self.M:
            self.y[m] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"y_{m}")
        self.beta = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"discount") #Applu cost
        "----------------------Continuous variables-----------------"
        self.T_d = {}
        self.T_l = {}
        for i in self.N:
            self.T_d[i] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"T_d_{i}")
            self.T_l[i] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"T_l_{i}")
        self.q_d = {}
        self.q_l = {}
        for i in self.N_dummy:
            self.q_d[i] = self.modelo.addVar(vtype=gp.GRB.CONTINUOUS, name=f"q_d_{i}")
            self.q_l[i] = self.modelo.addVar(vtype=gp.GRB.CONTINUOUS, name=f"q_l_{i}")
        "-----------------------Operational price-------------------"
        self.au_1 = {}
        for m in self.M:
            self.au_1[m] = {}
            for (i,j) in self.A:
                self.au_1[m][i,j] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"au_1_{m}_{i}_{j}")
        
        for m in self.M:
            for (i,j) in self.A:
                self.modelo.addConstr(self.au_1[m][i,j] <= self.y[m], name=f"con1_price_{i}_{j}_{m}")
                self.modelo.addConstr(self.au_1[m][i,j] <= self.x[i,j], name=f"con2_price_{i}_{j}_{m}")
                self.modelo.addConstr(self.au_1[m][i,j] >= self.y[m] + self.x[i,j] - 1, name=f"con3_price_{i}_{j}_{m}")
        
        self.p1 = gp.quicksum(self.c[m] * self.d[i,j] * self.au_1[m][i,j] for m in self.M for (i,j) in self.A)
        
        self.p_r = self.p1 - self.alpha * self.p1
       
        "---------------------------Adjusting constraint-------------------------------"
        self.modelo.addConstr(gp.quicksum(self.x[i, 'dummy_task'] for i in self.Nd) == 1, name=f"con_add_1")
        self.modelo.addConstr(gp.quicksum(self.x['dummy_task',i] for i in self.Np) == 1, name=f"con_add_2")
        self.modelo.addConstr(gp.quicksum(self.x[i,j] for i in self.Nd for j in self.Np) == 0, name=f"con_add_3")
        #self.modelo.addConstr(self.T_l[0] >= self.T_d[0] + gp.quicksum(self.y[m] * self.t0[m] for m in self.M), name=f"con_add_4")
        #self.modelo.addConstr(self.T_l[0] <= self.T_d[0] + gp.quicksum(self.y[m] * self.t0[m] for m in self.M) + self.omega, name=f"con_add_5")
        "---------------------------Routing constraint-------------------------------"
        #Constraint 9:
        for i in self.N:
            self.modelo.addConstr(gp.quicksum(self.x[i,j] for j in self.N) == gp.quicksum(self.x[j,i] for j in self.N), name=f"con9.1_{i}")

        #Constraint 10:
        for j in self.N:
            if j != 0:
                self.modelo.addConstr(gp.quicksum(self.x[i,j] for i in self.N if (i,j) in self.A if j != 0) == self.u[j], name=f"con10.1_{j}")
        
        self.modelo.addConstr(gp.quicksum(self.u[i] for i in self.N) == len(self.N), name=f"con10.2")

        for i in self.N:
            for j in self.N:
                if i != j:
                    self.modelo.addConstr(self.x[i,j] + self.x[j,i] <= 1, name=f"con_10.3_subtour_elimination_{i}_{j}")

        #Constraint 11:
        self.modelo.addConstr(gp.quicksum(self.x[0,i] for i in self.Nd) == 1, name=f"con11.1")
        self.modelo.addConstr(gp.quicksum(self.x[i,0] for i in self.Np) == 1, name=f"con11.2")
        
        #Constraint 14:
        self.modelo.addConstr(gp.quicksum(self.h[i] * self.x[i,'dummy_task'] for i in self.Nd)
                                - gp.quicksum(self.h[i] * self.x['dummy_task', i] for i in self.Np)
                                <= self.BigM * (self.x[0, 'dummy_task'] + self.x['dummy_task', 0]), name=f"con14")
        
        #Constraint 15:
        self.modelo.addConstr(gp.quicksum(self.h[i] * self.x[i, 'dummy_task'] for i in self.Nd)
                              - gp.quicksum(self.h[i] * self.x['dummy_task', i] for i in self.Np)
                              >= self.BigM *(self.x[0, 'dummy_task'] + self.x['dummy_task', 0]), name=f"con15")

        "-----------------------------Loading constraint--------------------------------------------------------------"

        #Constraint 16:
        self.modelo.addConstr(self.q_l['dummy_task'] == 0, name=f"con16.1")
        self.modelo.addConstr(self.q_d['dummy_task'] == 0, name=f"con16.2")

        #Constraint 17:
        self.modelo.addConstr(self.q_d[0] <= (gp.quicksum(self.Q[m] * self.y[m] for m in self.M)), name=f"con17.1")
        self.modelo.addConstr(self.q_l[0] <= (gp.quicksum(self.Q[m] * self.y[m] for m in self.M)), name=f"con17.2")

        #Constraint 18:
        self.modelo.addConstr(self.q_d[0] == (gp.quicksum((abs(self.w[i])) * self.u[i] for i in self.Np)), name=f"con18.1")
        self.modelo.addConstr(self.q_l[0] == gp.quicksum((abs(self.w[i])) * self.u[i] for i in self.Nd), name=f"con18.2")

        #Constraint 19:        
        for (i,j) in self.A:
            if i != 0:
                self.modelo.addConstr(self.q_d[j] >= self.q_d[i] + self.w[i] - self.BigM * (1 - self.x[i,j]), name=f"con19_{i}_{j}")        #Constraint 20:
        
        #Constraint 20:
        for (i,j) in self.A:
            if j != 0:
                self.modelo.addConstr(self.q_l[j] <= self.q_l[i] - self.w[j] + self.BigM * (1 - self.x[i,j]), name=f"con20_{i}_{j}")


        "-------------------------------------------Timing constraint------------------------------"
        #Constraint 21
        for i in self.Nd:
            self.modelo.addConstr(self.T_l[0] >= self.u[i] * self.e[i], name=f"con21.1_{i}")
            self.modelo.addConstr(self.T_d[i] <= self.u[i] * self.l[i] + self.BigM * (1 - self.u[i]), name=f"con21.2_{i}")

        #Constraint 22
        for i in self.Np:
            self.modelo.addConstr(self.T_l[i] >= self.u[i] * self.e[i], name=f"con22.1_{i}")
            self.modelo.addConstr(self.T_d[0] <= self.l[i] + self.BigM * (1 - self.u[i]), name=f"con22.2_{i}")
        
        #Constraint 23
        for i in self.Nd:
            self.modelo.addConstr(self.T_d[i] >= self.T_l[0], name=f"con23_{i}")
       
        #Constraint 24
        for (i,j) in self.A:
            if self.h[i] != self.h[j]:
                self.modelo.addConstr(self.T_l[i] + self.t[i,j] - self.T_d[j] - self.BigM * (1 - self.x[i,j]) <= 0, name=f"con24.1_{i}_{j}")
                self.modelo.addConstr(self.T_l[i] + self.t[i,j] - self.T_d[j] + self.BigM * (1 - self.x[i,j]) >= 0, name=f"con24.2_{i}_{j}")

        #Constraint 25
        for (i,j) in self.A:
            if self.h[i] == self.h[j]:
                self.modelo.addConstr(self.T_d[i] - self.T_d[j] - self.BigM * (1 - self.x[i,j]) <= 0, name=f"con25.1_{i}_{j}")
                self.modelo.addConstr(self.T_d[i] - self.T_d[j] + self.BigM * (1 - self.x[i,j]) >= 0, name=f"con25.2_{i}_{j}")

        #Constraint 26
        for i in self.Nd:
            self.modelo.addConstr(self.T_l[i] >= self.T_d[i] + gp.quicksum(self.y[m] * self.t1[m] for m in self.M), name=f"con26.1_{i}")
            self.modelo.addConstr(self.T_l[i] <= self.T_d[i] + gp.quicksum(self.y[m] * self.t1[m] for m in self.M) + self.omega, name=f"con26.2_{i}")
        for i in self.Np:
            self.modelo.addConstr(self.T_l[i] >= self.T_d[i] + gp.quicksum(self.y[m] * self.t0[m] for m in self.M), name=f"con26.3_{i}")
            self.modelo.addConstr(self.T_l[i] <= self.T_d[i] + gp.quicksum(self.y[m] * self.t0[m] for m in self.M) + self.omega, name=f"con26.4_{i}")

        

        "-------------------------------------------Limiting constraint------------------"
        #Constraint 28
        self.modelo.addConstr(gp.quicksum(self.y[m] for m in self.M) == 1, name=f"con28")

        #Constraint 29
        for i in self.N:
            if i != 0:
                self.modelo.addConstr((gp.quicksum(m * self.y[m] for m in self.M))
                            <= self.v[i] * self.u[i] + self.BigM * (1 - self.u[i]), name=f"con29_{i}")
            
       
            "-----------------------Objective-------------------------------------------------------------"
            self.modelo.setObjective(
                        self.p_r - gp.quicksum(self.duals[i] * self.u[i] for i in self.N), sense=gp.GRB.MINIMIZE,
                    )
            
            self.modelo.update()
            self.modelo.Params.OutputFlag = 0
           

    def optimze(self):
        self.modelo.optimize()
        

    def getSolution(self):
        return self.modelo.getAttr("X")

    def show(self):
        self.segments = []
        for m in self.M:
            if self.y[m].X == 1:
                for (i,j) in self.A:
                    if i!= 'dummy_task':
                        if j != 'dummy_task':
                            #print(f"from {i} to {j} takes {t[i,j]} minutes")
                            if self.x[i,j].X == 1:
                                #print(f"The truck type {m+1} does the task {i} to the task {j}")
                                self.segments.append((i, j))                               
        #print(self.segments)
        return self.segments
    
    def find_all_routes(self):
        self.routes_dict = {} 
        self.tasks_copy = self.segments.copy() 
        route_id = 1  
        self.R_input = {}
        self.p = {}
        while self.tasks_copy:  
            self.route = [0] 
            self.cost_each_route = 0  

            while self.tasks_copy:
                self.next_segment = next(
                    ((start, end) for start, end in self.tasks_copy if self.route[-1] in (start, end)),
                    None
                )
                if not self.next_segment: 
                    break

                i, j = self.next_segment
                self.segment_cost = ((1 - self.alpha) * gp.quicksum(self.c[m] * self.d[i, j] for m in self.M if self.y[m].X == 1)).getValue()
                self.cost_each_route += self.segment_cost

                self.tasks_copy.remove(self.next_segment)
                self.route.append(j if self.route[-1] == i else i)

                # Dừng lại nếu route quay về depot
                if self.route[-1] == 0:
                    break

            # Lưu route 
            if self.route[-1] == 0:  
                self.routes_dict[route_id] = {
                    "route": self.route,
                    "cost": self.cost_each_route
                }
                self.R_input[route_id] = self.route
                self.p[route_id] = self.cost_each_route
                #print(f"Added Route_{route_id}: {self.route} with cost {cost_each_route}")
                route_id += 1  # Tăng ID cho route tiếp theo

        return self.routes_dict, self.R_input, self.p

class Sub_problem_SP2:
    def __init__(self,duals,modelo=None):
        hub, weight, ready, deadline, x_cood, y_cood, dock, vehicle_type, task_dict = readData()
        hub_no, x_cood_hub, y_cood_hub, dock_hub, hub_dict = readDataHub()
        no, m, Q, c, t_load, t_unload, vehicle = readVehicle()

        #Parameter:
        self.alpha = 0.5 #Discount rate
        self.BigM = 99999999
        self.omega = 0
        
        #Set task
        self.N = task_dict
        self.Np = {}
        self.Nd = {}
        for i in range(len(self.N)):
            if self.N[i]['weight'] != 0:
                if self.N[i]['weight'] > 0:
                    self.Np[i] = self.N[i]
                else:
                    self.Nd[i] = self.N[i]
        
        
        self.N_new = {}
        for i in range(len(self.N)):
            if self.N[i]['weight'] == 0:
                self.N_new[i] = self.N[i]
            else:
                if self.N[i]['weight'] < 0:
                    self.N_new[i] = self.N[i]
        
        #Add dummy task
        self.N_new_dummy = self.N_new.copy()
        self.Nd_dummy = self.Nd.copy()
        self.dummy_task_attribute = {"hub": len(self.N)+1, "weight":0}
        self.Nd_dummy['dummy_task'] = self.dummy_task_attribute
        self.N_new_dummy['dummy_task'] = self.dummy_task_attribute
     

        #Set arc
        self.A = {(i, j) for i in self.N_new for j in self.N_new if i != j}
        self.A_dummy = {(i, j) for i in self.N_new_dummy for j in self.N_new_dummy if i != j}
        
        #Set
        self.H = hub
        self.W = weight
        self.E = ready
        self.D = deadline

        #Vehicle attribute
        self.M = vehicle
        self.type_vehicle = {m: self.M[m]['type_vehicle'] for m in self.M}
        self.Q = {m: self.M[m]['capacity'] for m in self.M}
        self.c = {m: self.M[m]['unit_cost'] for m in self.M}
        self.t0 = {m: self.M[m]['load_time'] for m in self.M}
        self.t1 = {m: self.M[m]['unload_time'] for m in self.M}

        #Task attribute
        self.h = {i: int(self.N[i]['hub']) for i in self.N_new}
        self.w = {i: self.N[i]['weight'] for i in self.N_new}
        self.e = {i: self.N[i]['ready'] for i in self.N_new}
        self.l = {i: self.N[i]['deadline'] for i in self.N_new}
        self.v = {i: self.N[i]['vehicle_type'] for i in self.N_new}
        
        dummy_task = 'dummy_task'
        self.h[dummy_task] = self.dummy_task_attribute["hub"]
        self.w[dummy_task] = self.dummy_task_attribute["weight"]
        
        "-------------------------------Input distances & time------------------------"
        self.d_hub = haversine_matrix()
        self.distance_matrix = {
            (i,j): (self.d_hub[self.h[i]][self.h[j]] if i != 'dummy_task' and j != 'dummy_task' else 0)
            for (i,j) in self.A_dummy
        }
       
        

        self.t_hub = travelling_time()
        self.time_matrix = {
            (i,j):(self.t_hub[self.h[i]][self.h[j]] if i != 'dummy_task' and j != 'dummy_task' else 0)
            for (i,j) in self.A_dummy
        }
       
        self.d = {}
        self.t = {}
        for (i,j) in self.A_dummy:
            self.d[i,j] = self.distance_matrix[i,j]
            self.t[i,j] = self.time_matrix[i,j]
        "-------------------------Duals-------------------------------------------------"
        self.duals = duals

        "-------------------------"
        if modelo == None:
            self.modelo = gp.Model("Sub_Problem_SP0")
        else:
            self.modelo = self.modelo.copy()

    def update_model(self):
        self.u = {}
        for var in self.modelo.getVars():
            ix = var.index
            varName = "done task[{}]".format(ix)
            self.u[ix] = self.modelo.getVarByName(varName)
        self.modelo.update()

    def build_model(self):
        "--------------------Decision variables-------------------"
        self.u = {}
        for i in self.N_new_dummy:
            self.u[i] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"u_{i}")
        self.x = {}
        for i in self.N_new_dummy:
            for j in self.N_new_dummy:
                self.x[i,j] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"x_{i}_{j}")
        self.y = {}
        for m in self.M:
            self.y[m] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"y_{m}")
        self.beta = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"discount") #Applu cost
        "----------------------Continuous variables-----------------"
        self.T_d = {}
        self.T_l = {}
        for i in self.N_new:
            self.T_d[i] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"T_d_{i}")
            self.T_l[i] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"T_l_{i}")
        self.q_d = {}
        self.q_l = {}
        for i in self.N_new_dummy:
            self.q_d[i] = self.modelo.addVar(vtype=gp.GRB.CONTINUOUS, name=f"q_d_{i}")
            self.q_l[i] = self.modelo.addVar(vtype=gp.GRB.CONTINUOUS, name=f"q_l_{i}")
        "-----------------------Operational price-------------------"
        self.au_1 = {}
        for m in self.M:
            self.au_1[m] = {}
            for (i,j) in self.A:
                self.au_1[m][i,j] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"au_1_{m}_{i}_{j}")
        
        for m in self.M:
            for (i,j) in self.A:
                self.modelo.addConstr(self.au_1[m][i,j] <= self.y[m], name=f"con1_price_{i}_{j}_{m}")
                self.modelo.addConstr(self.au_1[m][i,j] <= self.x[i,j], name=f"con2_price_{i}_{j}_{m}")
                self.modelo.addConstr(self.au_1[m][i,j] >= self.y[m] + self.x[i,j] - 1, name=f"con3_price_{i}_{j}_{m}")
        
        self.p1 = gp.quicksum(self.c[m] * self.d[i,j] * self.au_1[m][i,j] for m in self.M for (i,j) in self.A)
        
        self.p_r = self.p1 
       
        "---------------------------Adjusting constraint-------------------------------"
        self.modelo.addConstr(self.x['dummy_task',0] == 1, name=f"con_add_1")
        self.modelo.addConstr(gp.quicksum(self.x[0,i] for i in self.Nd) == 1, name=f"con_add_2")

        "---------------------------Routing constraint-------------------------------"
       
        #Constraint 9:
        for i in self.N_new:
            self.modelo.addConstr(gp.quicksum(self.x[i,j] for j in self.N_new) == gp.quicksum(self.x[j,i] for j in self.N_new), name=f"con9.1_{i}")

        #Constraint 10:
        for j in self.N_new:
            if j != 0:
                self.modelo.addConstr(gp.quicksum(self.x[i,j] for i in self.N_new if (i,j) in self.A if j != 0) == self.u[j], name=f"con10.1_{j}")
        
        self.modelo.addConstr(gp.quicksum(self.u[i] for i in self.N_new) == len(self.N_new), name=f"con10.2")

        for i in self.N_new:
            for j in self.N_new:
                if i != j:
                    self.modelo.addConstr(self.x[i,j] + self.x[j,i] <= 1, name=f"con_10.3_subtour_elimination_{i}_{j}")

       
        
        "-----------------------------Loading constraint--------------------------------------------------------------"

        #Constraint 17:
        self.modelo.addConstr(self.q_d[0] <= (gp.quicksum(self.Q[m] * self.y[m] for m in self.M)), name=f"con17.1")
        self.modelo.addConstr(self.q_l[0] <= (gp.quicksum(self.Q[m] * self.y[m] for m in self.M)), name=f"con17.2")

        #Constraint 18:
        #self.modelo.addConstr(self.q_d[0] == (gp.quicksum((abs(self.w[i])) * self.u[i] for i in self.Np)), name=f"con18.1")
        self.modelo.addConstr(self.q_l[0] == gp.quicksum((abs(self.w[i])) * self.u[i] for i in self.Nd), name=f"con18.2")

        
        
        #Constraint 20:
        for (i,j) in self.A:
            if j != 0:
                self.modelo.addConstr(self.q_l[j] <= self.q_l[i] - self.w[j] + self.BigM * (1 - self.x[i,j]), name=f"con20_{i}_{j}")


        "-------------------------------------------Timing constraint------------------------------"
        #Constraint 21
        for i in self.Nd:
            self.modelo.addConstr(self.T_l[0] >= self.u[i] * self.e[i], name=f"con21.1_{i}")
            self.modelo.addConstr(self.T_d[i] <= self.u[i] * self.l[i] + self.BigM * (1 - self.u[i]), name=f"con21.2_{i}")

        
        #Constraint 23
        for i in self.Nd:
            self.modelo.addConstr(self.T_d[i] >= self.T_l[0], name=f"con23_{i}")
       
       

        "-------------------------------------------Limiting constraint------------------"
        #Constraint 28
        self.modelo.addConstr(gp.quicksum(self.y[m] for m in self.M) == 1, name=f"con28")

        #Constraint 29
        for i in self.N_new:
            if i != 0:
                self.modelo.addConstr((gp.quicksum(m * self.y[m] for m in self.M))
                            <= self.v[i] * self.u[i] + self.BigM * (1 - self.u[i]), name=f"con29_{i}")
            

            "-----------------------Objective-------------------------------------------------------------"
            self.modelo.setObjective(
                        self.p_r - gp.quicksum(self.duals[i] * self.u[i] for i in self.N_new), sense=gp.GRB.MINIMIZE,
                    )
            
            self.modelo.update()
            self.modelo.Params.OutputFlag = 0
           
    def optimze(self):
        self.modelo.optimize()
        
    def getSolution(self):
        return self.modelo.getAttr("X")

    def show(self):
        self.segments = []
        for m in self.M:
            if self.y[m].X == 1:
                for (i,j) in self.A:
                    if i!= 'dummy_task':
                        if j != 'dummy_task':
                            #print(f"from {i} to {j} takes {t[i,j]} minutes")
                            if self.x[i,j].X == 1:
                                #print(f"The truck type {m+1} does the task {i} to the task {j}")
                                self.segments.append((i, j))                               
        #print(self.segments)
        return self.segments
    
    
    def find_all_routes(self):
        self.routes_dict = {} 
        self.tasks_copy = self.segments.copy() 
        route_id = 1  
        self.R_input = {}
        self.p = {}
        while self.tasks_copy:  
            self.route = [0] 
            self.cost_each_route = 0  

            while self.tasks_copy:
                self.next_segment = next(
                    ((start, end) for start, end in self.tasks_copy if self.route[-1] in (start, end)),
                    None
                )
                if not self.next_segment: 
                    break

                i, j = self.next_segment
                self.segment_cost = (gp.quicksum(self.c[m] * self.d[i, j] for m in self.M if self.y[m].X == 1)).getValue()
                self.cost_each_route += self.segment_cost

                self.tasks_copy.remove(self.next_segment)
                self.route.append(j if self.route[-1] == i else i)

                # Dừng lại nếu route quay về depot
                if self.route[-1] == 0:
                    break

            # Lưu route 
            if self.route[-1] == 0:  
                self.routes_dict[route_id] = {
                    "route": self.route,
                    "cost": self.cost_each_route
                }
                self.R_input[route_id] = self.route
                self.p[route_id] = self.cost_each_route
                #print(f"Added Route_{route_id}: {self.route} with cost {cost_each_route}")
                route_id += 1  # Tăng ID cho route tiếp theo

        return self.routes_dict, self.R_input, self.p

class Sub_problem_SP1:
    def __init__(self,duals,modelo=None):
        hub, weight, ready, deadline, x_cood, y_cood, dock, vehicle_type, task_dict = readData()
        hub_no, x_cood_hub, y_cood_hub, dock_hub, hub_dict = readDataHub()
        no, m, Q, c, t_load, t_unload, vehicle = readVehicle()

        #Parameter:
        self.alpha = 0.5 #Discount rate
        self.BigM = 99999999
        self.omega = 0
        
        #Set task
        self.N = task_dict
        self.Np = {}
        self.Nd = {}
        for i in range(len(self.N)):
            if self.N[i]['weight'] != 0:
                if self.N[i]['weight'] > 0:
                    self.Np[i] = self.N[i]
                else:
                    self.Nd[i] = self.N[i]
        
        self.N_new = {}
        for i in range(len(self.N)):
            if self.N[i]['weight'] == 0:
                self.N_new[i] = self.N[i]
            else:
                if self.N[i]['weight'] > 0:
                    self.N_new[i] = self.N[i]

        #Add dummy task
        self.N_new_dummy = self.N_new.copy()
        self.Np_dummy = self.Np.copy()
        self.dummy_task_attribute = {"hub": len(self.N)+1, "weight":0}
        self.Np_dummy['dummy_task'] = self.dummy_task_attribute
        self.N_new_dummy['dummy_task'] = self.dummy_task_attribute

        #Set arc
        self.A = {(i, j) for i in self.N_new for j in self.N_new if i != j}
        self.A_dummy = {(i, j) for i in self.N_new_dummy for j in self.N_new_dummy if i != j}
        
        #Set
        self.H = hub
        self.W = weight
        self.E = ready
        self.D = deadline

        #Vehicle attribute
        self.M = vehicle
        self.type_vehicle = {m: self.M[m]['type_vehicle'] for m in self.M}
        self.Q = {m: self.M[m]['capacity'] for m in self.M}
        self.c = {m: self.M[m]['unit_cost'] for m in self.M}
        self.t0 = {m: self.M[m]['load_time'] for m in self.M}
        self.t1 = {m: self.M[m]['unload_time'] for m in self.M}

        #Task attribute
        self.h = {i: int(self.N_new[i]['hub']) for i in self.N_new}
        self.w = {i: self.N_new[i]['weight'] for i in self.N_new}
        self.e = {i: self.N_new[i]['ready'] for i in self.N_new}
        self.l = {i: self.N_new[i]['deadline'] for i in self.N_new}
        self.v = {i: self.N_new[i]['vehicle_type'] for i in self.N_new}
        
        dummy_task = 'dummy_task'
        self.h[dummy_task] = self.dummy_task_attribute["hub"]
        self.w[dummy_task] = self.dummy_task_attribute["weight"]
        
        "-------------------------------Input distances & time------------------------"
        self.d_hub = haversine_matrix()
        self.distance_matrix = {
            (i,j): (self.d_hub[self.h[i]][self.h[j]] if i != 'dummy_task' and j != 'dummy_task' else 0)
            for (i,j) in self.A_dummy
        }
       
        

        self.t_hub = travelling_time()
        self.time_matrix = {
            (i,j):(self.t_hub[self.h[i]][self.h[j]] if i != 'dummy_task' and j != 'dummy_task' else 0)
            for (i,j) in self.A_dummy
        }
       
        self.d = {}
        self.t = {}
        for (i,j) in self.A_dummy:
            self.d[i,j] = self.distance_matrix[i,j]
            self.t[i,j] = self.time_matrix[i,j]
        "-------------------------Duals-------------------------------------------------"
        self.duals = duals

        "-------------------------"
        if modelo == None:
            self.modelo = gp.Model("Sub_Problem_SP0")
        else:
            self.modelo = self.modelo.copy()

    def update_model(self):
        self.u = {}
        for var in self.modelo.getVars():
            ix = var.index
            varName = "done task[{}]".format(ix)
            self.u[ix] = self.modelo.getVarByName(varName)
        self.modelo.update()

    def build_model(self):
        "--------------------Decision variables-------------------"
        self.u = {}
        for i in self.N_new_dummy:
            self.u[i] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"u_{i}")
        self.x = {}
        for i in self.N_new_dummy:
            for j in self.N_new_dummy:
                self.x[i,j] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"x_{i}_{j}")
        self.y = {}
        for m in self.M:
            self.y[m] = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"y_{m}")
        self.beta = self.modelo.addVar(vtype=gp.GRB.BINARY, name=f"discount") #Applu cost
        "----------------------Continuous variables-----------------"
        self.T_d = {}
        self.T_l = {}
        for i in self.N_new:
            self.T_d[i] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"T_d_{i}")
            self.T_l[i] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"T_l_{i}")
        self.q_d = {}
        self.q_l = {}
        for i in self.N_new_dummy:
            self.q_d[i] = self.modelo.addVar(vtype=gp.GRB.CONTINUOUS, name=f"q_d_{i}")
            self.q_l[i] = self.modelo.addVar(vtype=gp.GRB.CONTINUOUS, name=f"q_l_{i}")
        "-----------------------Operational price-------------------"
        self.au_1 = {}
        for m in self.M:
            self.au_1[m] = {}
            for (i,j) in self.A:
                self.au_1[m][i,j] = self.modelo.addVar(lb=0, vtype=gp.GRB.CONTINUOUS, name=f"au_1_{m}_{i}_{j}")
        
        for m in self.M:
            for (i,j) in self.A:
                self.modelo.addConstr(self.au_1[m][i,j] <= self.y[m], name=f"con1_price_{i}_{j}_{m}")
                self.modelo.addConstr(self.au_1[m][i,j] <= self.x[i,j], name=f"con2_price_{i}_{j}_{m}")
                self.modelo.addConstr(self.au_1[m][i,j] >= self.y[m] + self.x[i,j] - 1, name=f"con3_price_{i}_{j}_{m}")
        
        self.p1 = gp.quicksum(self.c[m] * self.d[i,j] * self.au_1[m][i,j] for m in self.M for (i,j) in self.A)
        
        self.p_r = self.p1 
       

        "---------------------------Routing constraint-------------------------------"
        
        #Constraint 9:
        for i in self.N_new:
            self.modelo.addConstr(gp.quicksum(self.x[i,j] for j in self.N_new) == gp.quicksum(self.x[j,i] for j in self.N_new), name=f"con9.1_{i}")

        #Constraint 10:
        for j in self.N_new:
            if j != 0:
                self.modelo.addConstr(gp.quicksum(self.x[i,j] for i in self.N_new if (i,j) in self.A if j != 0) == self.u[j], name=f"con10.1_{j}")
        
        self.modelo.addConstr(gp.quicksum(self.u[i] for i in self.N_new) == len(self.N_new), name=f"con10.2")

        for i in self.N_new:
            for j in self.N_new:
                if i != j:
                    self.modelo.addConstr(self.x[i,j] + self.x[j,i] <= 1, name=f"con_10.3_subtour_elimination_{i}_{j}")

        
        "-----------------------------Loading constraint--------------------------------------------------------------"

        #Constraint 17:
        self.modelo.addConstr(self.q_d[0] <= (gp.quicksum(self.Q[m] * self.y[m] for m in self.M)), name=f"con17.1")
        self.modelo.addConstr(self.q_l[0] <= (gp.quicksum(self.Q[m] * self.y[m] for m in self.M)), name=f"con17.2")

        #Constraint 18:
        self.modelo.addConstr(self.q_d[0] == (gp.quicksum((abs(self.w[i])) * self.u[i] for i in self.Np)), name=f"con18.1")
        #self.modelo.addConstr(self.q_l[0] == gp.quicksum((abs(self.w[i])) * self.u[i] for i in self.Nd), name=f"con18.2")

        #Constraint 19:        
        for (i,j) in self.A:
            if i != 0:
                self.modelo.addConstr(self.q_d[j] >= self.q_d[i] + self.w[i] - self.BigM * (1 - self.x[i,j]), name=f"con19_{i}_{j}")        #Constraint 20:
        
        "-------------------------------------------Timing constraint------------------------------"
        
        #Constraint 22
        for i in self.Np:
            self.modelo.addConstr(self.T_l[i] >= self.u[i] * self.e[i], name=f"con22.1_{i}")
            self.modelo.addConstr(self.T_d[0] <= self.l[i] + self.BigM * (1 - self.u[i]), name=f"con22.2_{i}")
               
        #Constraint 24
        for (i,j) in self.A:
            if self.h[i] != self.h[j]:
                self.modelo.addConstr(self.T_l[i] + self.t[i,j] - self.T_d[j] - self.BigM * (1 - self.x[i,j]) <= 0, name=f"con24.1_{i}_{j}")
                self.modelo.addConstr(self.T_l[i] + self.t[i,j] - self.T_d[j] + self.BigM * (1 - self.x[i,j]) >= 0, name=f"con24.2_{i}_{j}")


        "-------------------------------------------Limiting constraint------------------"
        #Constraint 28
        self.modelo.addConstr(gp.quicksum(self.y[m] for m in self.M) == 1, name=f"con28")

        #Constraint 29
        for i in self.N_new:
            if i != 0:
                self.modelo.addConstr((gp.quicksum(m * self.y[m] for m in self.M))
                            <= self.v[i] * self.u[i] + self.BigM * (1 - self.u[i]), name=f"con29_{i}")
            

            "-----------------------Objective-------------------------------------------------------------"
            self.modelo.setObjective(
                        self.p_r - gp.quicksum(self.duals[i] * self.u[i] for i in self.N_new), sense=gp.GRB.MINIMIZE,
                    )
            
            self.modelo.update()
            self.modelo.Params.OutputFlag = 0
           

    def optimze(self):
        self.modelo.optimize()
        

    def getSolution(self):
        return self.modelo.getAttr("X")

    def show(self):
        self.segments = []
        for m in self.M:
            if self.y[m].X == 1:
                for (i,j) in self.A:
                    if i!= 'dummy_task':
                        if j != 'dummy_task':
                            #print(f"from {i} to {j} takes {t[i,j]} minutes")
                            if self.x[i,j].X == 1:
                                #print(f"The truck type {m+1} does the task {i} to the task {j}")
                                self.segments.append((i, j))                               
        #print(self.segments)
        return self.segments
    
    
    def find_all_routes(self):
        self.routes_dict = {} 
        self.tasks_copy = self.segments.copy() 
        route_id = 1  
        self.R_input = {}
        self.p = {}
        while self.tasks_copy:  
            self.route = [0] 
            self.cost_each_route = 0  

            while self.tasks_copy:
                self.next_segment = next(
                    ((start, end) for start, end in self.tasks_copy if self.route[-1] in (start, end)),
                    None
                )
                if not self.next_segment: 
                    break

                i, j = self.next_segment
                self.segment_cost = (gp.quicksum(self.c[m] * self.d[i, j] for m in self.M if self.y[m].X == 1)).getValue()
                self.cost_each_route += self.segment_cost

                self.tasks_copy.remove(self.next_segment)
                self.route.append(j if self.route[-1] == i else i)

                # Dừng lại nếu route quay về depot
                if self.route[-1] == 0:
                    break

            # Lưu route 
            if self.route[-1] == 0:  
                self.routes_dict[route_id] = {
                    "route": self.route,
                    "cost": self.cost_each_route
                }
                self.R_input[route_id] = self.route
                self.p[route_id] = self.cost_each_route
                #print(f"Added Route_{route_id}: {self.route} with cost {cost_each_route}")
                route_id += 1  # Tăng ID cho route tiếp theo

        return self.routes_dict, self.R_input, self.p

class Master_Problem:
    def __init__(self,p,R_input, modelo=None):
        hub, weight, ready, deadline, x_cood, y_cood, dock, vehicle_type, task_dict = readData()
        hub_no, x_cood_hub, y_cood_hub, dock_hub, hub_dict = readDataHub()
     
        # Attribute
        self.hub, self.weight, self.ready, self.deadline, self.task_dict = hub, weight, ready, deadline, task_dict
        self.x_cood, self.y_cood, self.dock, self.vehicle_type = x_cood, y_cood, dock, vehicle_type
        self.hub_no, self.x_cood_hub, self.y_cood_hub = hub_no, x_cood_hub, y_cood_hub
        self.dock_hub, self.hub_dict = dock_hub, hub_dict
       
        self.N = task_dict
        # Đặt index cho từng route
        self.R_input = R_input
        self.R_list = list(self.R_input)
        self.R_index = {idx: r for idx, r in enumerate(self.R_list, start=0)}
        self.R_arc = {(r1, r2) for r1 in range(len(self.R_index)) for r2 in range(len(self.R_index)) if r1 != r2}

        # Lấy hub cho từng route
        self.H_hub = {}
        for r in self.R_index:
            self.hubs_for_route = []
            for i in self.R_index[r]:
                if i in self.N:
                    h = int(self.N[i]["hub"])
                    self.hubs_for_route.append(h)
            self.H_hub[r] = self.hubs_for_route
      
        self.theta = {h: int(self.hub_dict[h]["dock_hub"]) for h in self.hub_dict}

        # Binary indicator 'a'
        self.a = {}
        for r in self.R_index:
            self.a[r] = {}
            for i in self.N:
                if i in self.R_index[r]:
                    self.a[r][i] = 1  
                else:
                    self.a[r][i] = 0
        
        # Arc indicator 'b'
        self.b = {}
        for h in self.hub_no:
            self.b[h] = {}
            for (r1, r2) in self.R_arc:
                if h in self.H_hub[r1]:
                    if h in self.H_hub[r2]:
                        self.b[h][r1, r2] = 1
                    else:
                        self.b[h][r1,r2] = 0
                else:
                    self.b[h][r1,r2] = 0
        
        #Pricing - sẽ được lấy từ subproblem
        
        self.p = p

        if modelo is None:
            self.modelo = gp.Model("Master_Problem")
        else:
            self.modelo = self.modelo.copy()
   
    def update_model(self):
        self.z = {}
        for var in self.modelo.getVars():
            r = var.index
            varName = var.VarName
            self.z[r] = self.modelo.getVarByName(varName)
        self.modelo.update()
   
    def build_model(self):
        self.z = self.modelo.addVars(self.R_index, vtype=gp.GRB.BINARY, name=f"z")
        #Objective:
        self.modelo.setObjective(
            gp.quicksum(self.p[r] * self.z[r] for r in self.R_index),sense=gp.GRB.MINIMIZE,
        )
        #Constraint 1:
        for i in self.N:
            if i != 0:
                self.modelo.addConstr(gp.quicksum((self.a[r][i]) * self.z[r] for r in self.R_index) >= 1, name=f"produce_dual")
       
        #Constraint 2:
        self.m3 = {}
        for h in self.hub_no:
            self.m3[h] = int(self.theta[h] * (self.theta[h] - 1)/2)
    

        self.m1 = {}
        for (r1,r2) in self.R_arc:
            if r1 != r2:
                self.m1[r1,r2] = self.modelo.addVar(vtype=gp.GRB.BINARY,name=f"m1_{r1}_{r2}")
        
        for h in self.hub_no:
            for (r1,r2) in self.R_arc:
                if r1 != r2:
                    self.modelo.addConstr(self.m1[r1,r2] <= self.z[r1])
                    self.modelo.addConstr(self.m1[r1,r2] <=  self.z[r2])
                    self.modelo.addConstr(self.m1[r1,r2] <= self.z[r1] + self.z[r2] - 1)
                self.modelo.addConstr(
                    gp.quicksum(self.m1[r1,r2] * self.b[h][r1,r2] for (r1,r2) in self.R_arc if r1 < r2) <= self.m3[h]
                )
       
        self.modelo.write("master_problem.lp")

    def getConstraints(self):
        self.constraints=[]
        for constr in self.modelo.getConstrs():
           if ("produce_dual" in constr.ConstrName):
               self.constraints.append(constr)
        return self.constraints
    
    def RelaxOptimize(self):
        self.relax_modelo = self.modelo.relax()
        self.relax_modelo.optimize()
   
    def getDuals(self):
        self.pi = []
        for constr in self.relax_modelo.getConstrs():
           if ("produce_dual" in constr.ConstrName):
                self.pi.append(constr.Pi)
        return self.pi
   
    def getSolution(self):
        return self.relax_modelo.getAttr("X")
   
    def getCosts(self):
        return self.relax_modelo.ObjVal
   
