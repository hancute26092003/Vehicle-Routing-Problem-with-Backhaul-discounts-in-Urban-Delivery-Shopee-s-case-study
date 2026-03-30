from copy import copy
from all_model import Sub_problem_SP0,Sub_problem_SP1, Sub_problem_SP2, Sub_problem_SP3, Master_Problem
from Data import *
from read_distance_task import distance_matrix_nxn
from Data import readData


def copy_models(coeff, assingments, MP_to_copy):
    MP_1 = Master_Problem(coeff, assingments, MP_to_copy)
    MP_1.update_model()
    MP_2 = Master_Problem(coeff, assingments, MP_to_copy)
    MP_2.update_model()
    return MP_1, MP_2

def copy_model(c, init_assingments, MP_to_copy):
    MP_copy = Master_Problem(c, init_assingments, MP_to_copy)
    MP_copy.update_model()
    return MP_copy

class ImpactHeuristic:
    def __init__(self):
        hub, weight, ready, deadline, x_cood, y_cood, dock, vehicle_type, task_dict = readData()
        self.distance_matrix = haversine_matrix()  # Ma trận khoảng cách
        self.data_task = task_dict  # Thông tin các nhiệm vụ
        self.vehicle_capacity = 1000  # Dung tích xe
        self.routes = []  # Lưu danh sách các tuyến đường
        self.total_cost_per_route = []  # Tổng chi phí từng tuyến
        self.total_cost = 0  # Tổng chi phí toàn bộ các tuyến
        self.total_task = []
    def calculate_route_distance(self, route):
        """Tính tổng khoảng cách của một tuyến đường."""
        self.total_distance = 0
        for i in range(len(route) - 1):
            self.total_distance += self.distance_matrix[route[i], route[i + 1]]
        return self.total_distance
    
    def calculate_route_cost(self, route, route_tasks, distance):
        """Tính chi phí của tuyến đường theo công thức."""
        if route_tasks:  # Đảm bảo tuyến có nhiệm vụ
            # Trọng lượng của task cuối cùng
            last_task = route_tasks[-1]
            last_weight = self.data_task[last_task]['weight']
            beta = 1 if last_weight > 0 else 0  # Kiểm tra beta
            cost = (1 - beta * 0.5) * 8100 * distance
        else:
            beta = 0
            cost = 8100 * distance
        # Tính chi phí theo công thức
        cost = (1 - beta * 0.5) * 8100 * distance
        return cost
    
    def generate_init_solution(self):
        tasks = self.data_task
        remaining_tasks = list(tasks)  # Danh sách các nhiệm vụ chưa xử lý


   # Loại bỏ task 0 khỏi remaining_tasks nếu có
        if 0 in remaining_tasks:
          remaining_tasks.remove(0)
        while remaining_tasks:
            route = [0]  # Bắt đầu tuyến từ depot (hub 0)
            route_tasks = [0]  # Task
            current_capacity = 0  # Dung tích xe hiện tại
            while remaining_tasks:
                best_task = None
                best_task_impact = float('inf')  # Khởi tạo giá trị impact tốt nhất

                for task in remaining_tasks:
                    task_weight = abs(tasks[task]['weight'])  # Trọng lượng của nhiệm vụ
                    task_hub = int(tasks[task]['hub'])  # Hub của nhiệm vụ

                    # Chỉ xét nhiệm vụ nếu đáp ứng điều kiện về trọng lượng
                    if current_capacity + task_weight <= self.vehicle_capacity:
                        last_hub = route[-1]  # Hub hiện tại trong tuyến
                        dist = self.distance_matrix[last_hub, task_hub]

                        # Tính toán impact: kết hợp khoảng cách và trọng lượng
                        impact = dist * (1 + task_weight / self.vehicle_capacity)
                        if impact < best_task_impact:
                            best_task = task
                            best_task_impact = impact
                # Nếu tìm được nhiệm vụ tốt nhất, thêm vào tuyến
                if best_task is not None:
                    task_hub = int(tasks[best_task]['hub'])
                    route.append(task_hub)  # Thêm hub của nhiệm vụ vào tuyến
                    route_tasks.append(best_task)  # Lưu task tương ứng
                    current_capacity += abs(tasks[best_task]['weight'])
                    remaining_tasks.remove(best_task)
                else:
                    break  # Không còn nhiệm vụ nào có thể thêm

            # Kết thúc tuyến đường, quay lại depot nếu cần
            if route[-1] != 0:
                route.append(0)  # Quay lại hub ban đầu
                route_tasks.append(0)  # Quay lại task 0


            # Tính khoảng cách và chi phí của tuyến
            route_distance = self.calculate_route_distance(route)
            route_cost = self.calculate_route_cost(route, route_tasks, route_distance)

            # Lưu thông tin tuyến
            
            self.routes.append((route, route_tasks, route_distance, route_cost))
            self.total_cost_per_route.append(route_cost)  # Lưu tổng chi phí từng route
            self.total_task.append(route_tasks)

        # Tính tổng chi phí toàn bộ
        self.total_cost = sum(self.total_cost_per_route)
        return self.routes, self.total_cost_per_route, self.total_cost, self.total_task

class PriorityQueue(object):
    def __init__(self):
        self.queue = []

    def isEmpty(self):
        return len(self.queue) == 0

    def insert(self, obj, MP):
        self.queue.append([obj,MP])

    def delete(self):
        try:
            min = 0
            for i in range(len(self.queue)):
                if self.queue[i][0] < self.queue[min][0]:
                    min = i
            item = self.queue[min]
            del self.queue[min]
            return item
        except IndexError:
            print()
            exit()


class ILS:
    def __init__(self):
        # Initialize data
        self.hub, self.weight, self.ready, self.deadline, self.x_cood, self.y_cood, self.dock, self.vehicle_type, self.task_dict = readData()
        self.distance_matrix = distance_matrix_nxn
        
        # Prepare task-related data
        self.N = self.task_dict
        self.Np, self.Nd, self.demands = {}, {}, {}
        for i in range(len(self.N)):
            if self.N[i]['weight'] != 0:
                if self.N[i]['weight'] > 0:
                    self.Np[i] = self.N[i]['weight']  # Pickup task
                    self.demands[i] = self.Np[i]  # Positive demand
                else:
                    self.Nd[i] = self.N[i]['weight']  # Delivery task
                    self.demands[i] = self.Nd[i]  # Negative demand
        
        self.time_windows = {}
        for i in range(len(self.N)):
            if self.N[i]['ready'] != 0 and self.N[i]['deadline'] != 0:
                self.time_windows[i] = {
                    'ready': float(self.N[i]['ready']),
                    'deadline': float(self.N[i]['deadline'])
                }
        
        # Vehicle settings
        self.vehicle_capacity = 1500
        vehicle_data = pd.read_excel('data_vehicle.xlsx', index_col=0, header=0)
        self.vehicle_info = vehicle_data[vehicle_data['vehicle_capacity'] >= self.vehicle_capacity]
        
        if not self.vehicle_info.empty:
            selected_vehicle = self.vehicle_info.iloc[0]
            self.cost_type = selected_vehicle['cost_vehicle_type']
            self.vehicle_type = selected_vehicle['type_vehicle']
        else:
            raise ValueError("No suitable vehicle found.")
        
        # Additional parameters
        self.depot = 0
        self.speed = 60  # km/h
        self.discount_factor = 0.5
        self.is_round_trip = 1

    def nearest_neighbor_with_deadline(self):
        tasks = sorted([i for i in range(1, len(self.N))], key=lambda x: self.time_windows[x]['deadline'])
        visited = set()
        routes = []
        
        while len(visited) < len(tasks):
            current_route = [self.depot]
            current_load = 0
            current_time = 0
            current_location = self.depot
            
            for task in tasks:
                if task in visited:
                    continue
                
                demand = self.demands[task]
                tw_start, tw_end = self.time_windows[task]['ready'], self.time_windows[task]['deadline']
                travel_time = self.distance_matrix[current_location][task] / self.speed
                
                if (current_load + demand <= self.vehicle_capacity and 
                    current_time + travel_time <= tw_end):
                    current_route.append(task)
                    visited.add(task)
                    current_load += demand
                    current_time = max(current_time + travel_time, tw_start)
                    current_location = task
            
            current_route.append(self.depot)
            routes.append(current_route)
        
        return routes

    def calculate_cost(self, routes):
        cost = 0
        for i in range(len(routes) - 1):
            distance = self.distance_matrix[routes[i]][routes[i + 1]]
            cost += (1 - self.discount_factor * self.is_round_trip) * distance * self.cost_type
        return cost

    def local_search_with_swap(self, routes):
        improved = True
        best_route = routes
        best_cost = self.calculate_cost(routes)
        
        
        while improved:
            improved = False
            for i in range(1, len(routes) - 2):
                for j in range(i + 1, len(routes) - 1):
                    new_route = routes[:i] + routes[i:j+1][::-1] + routes[j+1:]
                    new_cost = self.calculate_cost(routes)
                    if new_cost < best_cost:
                        best_route = new_route
                        best_cost = new_cost
                        improved = True
                        
            
            for i in range(1, len(routes) - 1):
                for j in range(i + 1, len(routes) - 1):
                    # Swap two customers in the route
                    new_route = routes[:]
                    new_route[i], new_route[j] = new_route[j], new_route[i]
                    
                    # Calculate the new cost of the route
                    new_cost = self.calculate_cost(new_route)  # Sử dụng self để gọi phương thức
                    
                    # Update the best route and cost if improvement is found
                    if new_cost < best_cost:
                        best_route = new_route
                        best_cost = new_cost
                        improved = True
            route = best_route
        
        return best_route
        

    def perturb_solution(self, routes):
        import random
        if len(routes) > 1:
            i, j = random.sample(range(len(routes)), 2)
            routes[i], routes[j] = routes[j], routes[i]
        return routes
    """
    def perturb_solution(self, routes):
        perturbed_routes = routes.copy()
        return perturbed_routes"""


    def iterated_local_search(self, iterations=10):
        routes = self.nearest_neighbor_with_deadline()
        best_routes = routes
        best_cost = sum(self.calculate_cost(route) for route in best_routes)
        
        for _ in range(iterations):
            perturbed_routes = self.perturb_solution(best_routes)
            improved_routes = [self.local_search_with_swap(route) for route in perturbed_routes]
            improved_cost = sum(self.calculate_cost(route) for route in improved_routes)
            
            if improved_cost < best_cost:
                best_routes = improved_routes
                best_cost = improved_cost
        
        return best_routes, best_cost
    
    
    def calculate_distance(self, route):
        distance = 0
        for i in range(len(route) - 1):
            distance += self.distance_matrix[route[i]][route[i + 1]]
        return distance

    def print_results(self):
        best_routes, best_cost = self.iterated_local_search()
        print(f"\nVehicle Type: {self.vehicle_type}, Cost per vehicle: {self.cost_type}")
        for i, route in enumerate(best_routes):
            route_cost = self.calculate_cost(route)
            distance = sum(self.distance_matrix[route[j]][route[j+1]] for j in range(len(route)-1))
            print(f"Route {i + 1}: {route} | Distance: {distance:.2f} km | Cost: ${route_cost:.2f}")
        print(f"\nTotal cost of all routes: ${best_cost:.2f}")