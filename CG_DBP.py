import gurobipy as gp
import sys
import copy
from gurobipy import GRB
from all_model import Sub_problem_SP0,Sub_problem_SP1, Sub_problem_SP2, Sub_problem_SP3, Sub_problem_SP4, Master_Problem
from itertools import combinations
from utils import copy_model, copy_models, PriorityQueue
from Data import *


def column_generation(duals):
    #sys.stdout = open('results_column_generation.txt', 'w')
    hub, weight, ready, deadline, x_cood, y_cood, dock, vehicle_type, task_dict = readData()
    record_newAssing = []  # Lưu trữ new column
    col_max = 10 
    new_MP = None  
    subproblems = [Sub_problem_SP4, Sub_problem_SP3, Sub_problem_SP2, Sub_problem_SP1]
    route_selected = []
    
    initial_duals = duals.copy()

    for SP_class in subproblems:
        while len(duals) < len(task_dict):
            duals.append(0.0)  # Đảm bảo duals đủ dài cho tất cả các task

        # Tạo subproblem với duals ban đầu
        SP_branch = SP_class(duals)
        print(f"1.------------------------------------------------------------------------Duals applying would be{duals}")
        SP_branch.build_model()
        SP_branch.optimze()
        SP_branch.show()
        SP_branch.find_all_routes()

        # New column
        newAssing = [SP_branch.u[i].X for i in SP_branch.u if i != 'dummy_task' and i != 0]

        # Nhập số cho Master
        R_input = list(SP_branch.R_input.values())
        p = list(SP_branch.p.values())
        MP_branch = Master_Problem(p, R_input)

        print(f"2.------------------------------------------------------------------------Add route from {SP_class}: {R_input}, cost {p}")
        reduced_cost = SP_branch.modelo.ObjVal
        
        if newAssing is not None:  # Nếu số lượng cột không vượt quá col_max
            record_newAssing.append(newAssing)
            if len(record_newAssing) <= col_max:
                print(f"3.------------------------------------------------------------------------Objective value from Sub_problem:{SP_branch}", reduced_cost)
                if reduced_cost < 0.0:  # Kiểm tra reduced cost = obj của subproblem
                    MP_branch.build_model()
                    constraints = MP_branch.getConstraints()
                    while len(newAssing) < len(constraints):
                        newAssing.append(0.0)
                    
                    newColumn = gp.Column(newAssing, constraints)
                    #print(f"4.Add column{newAssing} with {constraints}")
                    MP_branch.modelo.addVar(vtype=GRB.BINARY, column=newColumn)
                    #MP_branch.modelo.update()
                    MP_branch.RelaxOptimize()

                    # Lấy duals từ MP_branch sau khi tối ưu hóa
                    duals = MP_branch.getDuals()
                    print(f"4.------------------------------------------------------------------------Duals for {SP_class} is {duals}")
                    
                    # In kết quả từ RMP
                    best_cost = MP_branch.getCosts()
                    route_selected.append(R_input)
                    print(f"5.------------------------------------------------------------------------  Best cost from Master problem:", best_cost)
                    print(f"6.------------------------------------------------------------------------  Routes from Master problem:", route_selected)

                    #new_MP = copy_models(best_cost, route_selected, MP_branch)
                else:
                    print(f"7.------------------------------------------------------------------------The column of {SP_branch} has the reduced cost {reduced_cost} > 0.0, which is non - negative")
            else:
                print(f"No valid assignment generated from {SP_branch}")

        # Kiểm tra kết quả cuối cùng
        if len(record_newAssing) > col_max:
            print(f"5.   Number of columns exceeded col_max.")
        else:
            print(f"8.------------------------------------------------------------------------   Final columns added: {len(record_newAssing)}")

    return new_MP
