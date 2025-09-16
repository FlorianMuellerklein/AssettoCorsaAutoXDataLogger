import ac
import acsys
import datetime
import math
import os

# lincoln airpark center lat long 40.84489462794975, -96.76910629089815
lincoln_lat = 40.8448946279497
lincoln_long = -96.76910629089815
lincoln_alt = 355.0


class DataStorage:
    car_id = 0

    def __init__(self):
        self.car_id = ac.getFocusedCar()
        cur_pos = ac.getCarState(self.car_id, acsys.CS.WorldPosition)
        self.prev_x = cur_pos[0]
        self.prev_y = cur_pos[2]

        # data recording
        self.brakes = []
        self.laps = []
        self.lats = []
        self.longs = []
        self.runtimes = []
        self.pos_xs = []
        self.pos_ys = []
        self.speeds = []
        self.steerings = []
        self.throttles = []
        self.total_times = []
        self.heights = []
        self.lateral_gs = []

        # time tracking
        self.update_interval = 0.05
        self.last_update = 0
        self.cur_time = 0.0

        # track whether we found start/finish lines
        self.start_lat_a = 0
        self.start_long_a = 0
        self.start_lat_b = 0
        self.start_long_b = 0
        self.finish_lat_a = 0
        self.finish_long_a = 0
        self.finish_lat_b = 0
        self.finish_long_b = 0
        self.found_start = False
        self.found_finish = False

        # constants for calculations
        self.earth_radius = 6378000.0

        # if we are on a circuit instead of point2point
        self.found_circuit = False

        self.parsed_data = "\n[data]\n"

    def update_data(self, dT):
        self.cur_time += dT

        # record data at 10hz
        if self.cur_time - self.last_update > self.update_interval:
            self.last_update = self.cur_time

            throttle = ac.getCarState(self.car_id, acsys.CS.Gas)
            brake = ac.getCarState(self.car_id, acsys.CS.Brake)
            runtime = ac.getCarState(self.car_id, acsys.CS.LapTime)
            steering = ac.getCarState(self.car_id, acsys.CS.Steer)
            speed = ac.getCarState(self.car_id, acsys.CS.SpeedKMH)
            cur_lap = ac.getCarState(self.car_id, acsys.CS.LapCount)
            cur_g = ac.getCarState(self.car_id, acsys.CS.AccG)

            # convert position to lat long
            cur_pos = ac.getCarState(self.car_id, acsys.CS.WorldPosition)
            pos_x = cur_pos[2]
            pos_z = cur_pos[1] 
            pos_y = cur_pos[0]
            lat, long = self.lat_long_from_meters(pos_x, pos_y, lincoln_lat)
            cur_lat = lincoln_lat + lat
            cur_long = lincoln_long + long

            # ac.log("{},{},{},{},{},{},{},{},{},{}".format(
            #     speed, runtime / 1000, self.cur_time, throttle, brake, steering, pos_x, pos_y, cur_lat, cur_long
            # ))

            # only record data if we are in a valid lap to save memory
            #if runtime > 0:
            self.brakes.append(brake)
            self.laps.append(cur_lap)
            self.lateral_gs.append(cur_g[0])
            self.lats.append(cur_lat)
            self.longs.append(cur_long)
            self.pos_xs.append(pos_x)
            self.pos_ys.append(pos_y)
            self.heights.append(lincoln_alt + pos_z)
            self.runtimes.append(runtime / 1000)
            self.speeds.append(speed)
            self.steerings.append(steering)
            self.total_times.append(self.parse_time())
            self.throttles.append(throttle)

    def parse_data(self):
        ac.log("parsing data ... ")
        for idx, cur_laptime in enumerate(self.runtimes):

            # Only parse data where we are in the course
            if idx > 1:
                # find the direction of travel between the two points
                angle_of_travel = self.find_angle([self.lats[idx-1], self.longs[idx-1]], [self.lats[idx], self.longs[idx]])

                # sats lat long velocity kmh
                self.parsed_data += "{sats:03d} {time} {lat:+012.8f} {long:+012.8f} {speed:07.3f} {height:+09.2f} {heading:05.2f} {steer:05.2f} {brake:.2f} {throttle:.2f} {lat_g:04.2f}\n".format(
                    sats=16,
                    time=self.total_times[idx],
                    lat=self.lats[idx] * 60,
                    long=self.longs[idx] * -60,
                    speed=self.speeds[idx],
                    height=self.heights[idx],
                    heading=(math.degrees(angle_of_travel) + 360) % 360,
                    steer=self.steerings[idx],
                    brake=self.brakes[idx],
                    throttle=self.throttles[idx],
                    lat_g=self.lateral_gs[idx]
                )
                
                # find the starting line
                if idx > 1 and not self.found_start:
                    ac.log("looking for start lat long ... ")

                    self.start_lat_a, self.start_long_a = self.create_start_finish_line(self.lats[idx], self.longs[idx], angle_of_travel + (math.pi / 2), 10)
                    self.start_lat_b, self.start_long_b = self.create_start_finish_line(self.lats[idx], self.longs[idx], angle_of_travel + (3 * math.pi / 2), 10)
                    self.found_start = True
                    ac.log("found start lat long!")

                

            # # if we finish a lap 
            if idx > 1 and self.laps[idx-1] < self.laps[idx] and not self.found_finish:
                ac.log("looking for finish lat long ... ")
                # find the direction of travel between the two points
                angle_of_travel = self.find_angle([self.lats[idx-1], self.longs[idx-1]], [self.lats[idx], self.longs[idx]])

                self.finish_lat_a, self.finish_long_a = self.create_start_finish_line(self.lats[idx], self.longs[idx], angle_of_travel + (math.pi / 2), 10)
                self.finish_lat_b, self.finish_long_b = self.create_start_finish_line(self.lats[idx], self.longs[idx], angle_of_travel + (3 * math.pi / 2), 10)
                self.found_finish = True
                ac.log("found finish lat long!")

            
        # if self.found_start and self.found_finish:
        #     start_finish_distance = self.lat_long_distance(
        #         [(self.start_lat_a + self.start_lat_b) / 2, (self.start_long_a + self.start_long_b) / 2],
        #         [(self.finish_lat_a + self.finish_lat_b) / 2, (self.finish_long_a + self.finish_long_b) / 2]
        #     )
        #     if abs(start_finish_distance) < 30:
        #         ac.log("saving as a circuit")
        #         self.found_circuit = True

        ac.log("{}".format(self.make_header()))
        ac.log(self.parsed_data)

    def parse_time(self):
        now = datetime.datetime.now()
        hours = int(now.hour)
        minutes = int(now.minute)
        seconds = int(now.second)
        millis = int(now.microsecond / 1000)

        return "{:02d}{:02d}{:02d}.{:03d}".format(hours, minutes, seconds, millis)

    def degree_2_radians(self, degrees):
        return degrees * (math.pi / 180)

    def lat_long_from_meters(self, dx, dy, start_lat):
        earth_radius = 6371000.0

        new_lat = (dy / earth_radius) * (180.0 / math.pi)
        new_long = (dx / earth_radius) * (180.0 / math.pi) / math.cos(self.degree_2_radians(start_lat))

        return new_lat, new_long
    
    def lat_long_distance(self, point_a, point_b):
        ac.log("Calculating distance between start and finish lines")
        lat_a = math.radians(point_a[0])
        long_a = math.radians(point_a[1])
        lat_b = math.radians(point_b[0])
        long_b = math.radians(point_b[1])
        ac.log("{} {} {} {}".format(lat_a, long_a, lat_b, long_b))

        lat_delta = lat_b - lat_a
        long_delta = long_b - long_a
        ac.log("{} {}".format(lat_delta, long_delta))

        a = math.sin(lat_delta / 2) * math.sin(lat_delta / 2) + math.cos(lat_a) * math.cos(lat_b) * math.sin(long_delta / 2) * math.sin(long_delta / 2)
        ac.log("{}".format(a))
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        ac.log("{}".format(c))
        ac.log("distance {}".format(self.earth_radius * c))

        return self.earth_radius * c

    def find_angle(self, point_a, point_b):
        # if using meters
        #y_diff = point_b[1] - point_a[1]
        #x_diff = point_b[0] - point_a[0]
        lat_a = math.radians(point_a[0])
        long_a = math.radians(point_a[1])
        lat_b = math.radians(point_b[0])
        long_b = math.radians(point_b[1])
        y_diff = math.cos(lat_b) * math.sin(long_b - long_a)
        x_diff = math.cos(lat_a) * math.sin(lat_b) - math.sin(lat_a) * math.cos(lat_b) * math.cos(long_b - long_a)

        return math.atan2(y_diff, x_diff) # radians

    def create_start_finish_line(self, lat, long, angle, distance):
        dx = distance * math.sin(angle)
        dy = distance * math.cos(angle)

        new_lat = lat + (dy / self.earth_radius) * (180 / math.pi)
        new_long = long + (dx / self.earth_radius) * (180 / math.pi) / math.cos(self.degree_2_radians(lat))

        return new_lat, new_long

    def write_data(self):
        ac.log("writing files ...")
        user_path = "C:/ACAutoXDataLogs"
        if not os.path.exists(user_path):
            os.makedirs(user_path)

        time_now = datetime.datetime.now()
        save_file = "AutoXLog_{year}-{month}-{day}_{hour}-{minute}.vbo".format(
            year=time_now.year,
            month=time_now.month,
            day=time_now.day,
            hour=time_now.hour,
            minute=time_now.minute
        )
        
        with open(os.path.join(user_path, save_file), 'w') as f:
            f.write("{}\n{}".format(self.make_header(), self.parsed_data))
        ac.log("done writing files!")


    def make_header(self):
        ac.log("making header ...")
        header = datetime.datetime.now().strftime("File created on %d/%m/%Y at %I:%M:%S %p")
        header += "\n\n"
        header += "[header]"
        for col_type in ["satellites", "time", "latitude", "longitude", "velocity kmh", "height", "heading", "Steering", "Brake", "Throttle", "Lateral G"]:
            header += "\n{}".format(col_type)

        # header += "\n\n[channel units]\ns\n"
        header += "\n\n[laptiming]\n"

        if not self.found_circuit:
            header += "Start        {:+012.8f} {:+012.8f} {:+012.8f} {:+012.8f} ¬  Start\n".format(
                self.start_long_a * -60, self.start_lat_a * 60, self.start_long_b * -60, self.start_lat_b * 60
            )
            header += "Finish        {:+012.8f} {:+012.8f} {:+012.8f} {:+012.8f} ¬  Finish\n".format(
                self.finish_long_a * -60, self.finish_lat_a * 60, self.finish_long_b * -60, self.finish_lat_b * 60
            )
        else:
            header += "Start        {:+012.8f} {:+012.8f} {:+012.8f} {:+012.8f} ¬  Start / Finish\n".format(
                self.start_long_a * -60, self.start_lat_a * 60, self.start_long_b * -60, self.start_lat_b * 60
            )
        
        header += "\n[session data]\nlaps {}\n".format(self.laps[-1])

        header += "\n[column names]\n"
        header += " ".join(["sats", "time", "lat", "long", "velocity", "height", "heading", "steering", "brake", "throttle", "lateralG"])

        ac.log("done making header!")
        return header
    
