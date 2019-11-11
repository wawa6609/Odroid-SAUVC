import threading

from .connectionOdroid import *
from .PID import *
IP_ADDRESS_1 = '10.42.0.158'  # address jetson
IP_ADDRESS_2 = '192.168.137.208'  # address odroid
PORT = 8181


lock = threading.Lock()

class Autonomy:  # to @Adam & Ernest : ej chłopaki, to narazie sama koncepcja klasy, tu będzie nasze sterowanie
    """Class that implements all autonomy -> methods that will controll AUV depending on
    what cameras see, what they saw and when and also decides in what order perform realising tasks,
    when there are many possibilities.
    Will be run in thread or maybe will inherit from Thread class"""
    def __init__(self, imu, pid_thread, conn_thread):
        self.imu = imu
        self.pid_thread = pid_thread
        self.pid_follow_obj = PID()
        # dodałem tutah obiekt connection z Jetsonem, ale raczej to zmienię i dodam jako paramert konstruktora
        #self.conn = Connection(IP_ADDRESS_2, PORT)
        self.conn = conn_thread
        self.conn.start()

        self.raw_data_frame = []
        self.objects_frame_cam1 = []
        self.objects_frame_cam2 = []
        self.objects_number_cam1 = 0
        self.objects_number_cam2 = 0
        self.objects_centras_cam1 = []
        self.objects_centras_cam2 = []
        self.objects_distances_cam1 = []
        self.objects_distances_cam2 = []




    def catch_detections(self):
        # łapanie ramek danych i wpisywanie ich w pola, których bedziemy uzywać do sterowania
        while True:
            with lock:
                self.raw_data_frame = self.conn.getDataFrame()
                # przypisanie wartosci z ramek do tablic w klasie
                self.objects_frame_cam1 = self.raw_data_frame[0]
                self.objects_number_cam1 = len(self.objects_frame_cam1)
                self.objects_frame_cam2 = self.raw_data_frame[1]
                self.objects_number_cam2 = len(self.objects_frame_cam2)

                for object_frame in self.objects_frame_cam1:
                    self.objects_distances_cam1.append(object_frame[0])
                    self.objects_centras_cam1.append([object_frame[1], object_frame[2]])
                for object_frame in self.objects_frame_cam2:
                    self.objects_distances_cam2.append(object_frame[0])
                    self.objects_centras_cam2.append([object_frame[1], object_frame[2]])

    def look_for_detections(self):
        #self.prev_pid_values = self.pid_thread.center_x_PID.getPIDCoefficients()
        # wyłącz yaw_pid, aby móc się rozejrzeć
        #self.pid_thread.center_x_PID
        self.stop()
        self.pid_thread.yaw_PID.setSetPoint(0.)
        time.sleep(1)
        while self.objects_number_cam1 <1:
            yaw = self.imu.getSample('yaw')
            # max angle w stopniach -> zakres 'rozglądania się' łodzi
            search_max_angle_abs = 120.
            if (yaw > - search_max_angle_abs and yaw < 0) or (yaw > search_max_angle_abs):
                self.turning_left(1.)  # 1 deg/sec
                time.sleep(0.5)
            elif (yaw > 0 and yaw < search_max_angle_abs) or (yaw < - search_max_angle_abs):
                self.turning_right(1.)  # 1 deg/sec
                time.sleep(0.5)

        # tutaj jakas decyzja ktory obiekt sledzić?
        # no i wywołanie śledzenia


    def turning_left(self, vel):
        self.pid_thread.yaw_PID.setSetPoint(self.pid_thread.yaw_PID.getSetPoint - vel)

    def turning_right(self, vel):
        self.pid_thread.yaw_PID.setSetPoint(self.pid_thread.yaw_PID.getSetPoint + vel)

    def follow_object(self, center_offset, pid_values, velocity):
        # for now just X pos, Y pos should be set by getting depth info
        # Nic pewnego czy zadziała narazie

        self.prev_yaw_pid_values = self.pid_thread.yaw_PID.getPIDCoefficients()
        # turn off yaw_PID, żeby mozna bylo sterowac tylko za pomocą offsetu z kamery
        self.pid_thread.yaw_PID.setPIDCoefficients(0., 0., 0.)
        while self.objects_number_cam1 > 1:
            self.pid_thread.center_x_PID.setPIDCoefficients(pid_values[0], pid_values[1], pid_values[2])
            self.pid_thread.center_x_PID.center_x_diff = self.pid_thread.center_x_PID.update(center_offset[0])  # x
            self.forward(velocity)

        # jeśli nie widzi obiektów to znowu wywołuje 'rozglądanie się'
        # ora przywroć poprzednie nastawy PID
        self.pid_thread.yaw_PID.setPIDCoefficients(self.prev_yaw_pid_values[0], self.prev_yaw_pid_values[1],
                                                   self.prev_yaw_pid_values[2])
        self.look_for_detections()

    def forward(self, velocity):
        self.pid_thread.pid_motors_speeds_update[0] = velocity
        self.pid_thread.pid_motors_speeds_update[1] = velocity

    def backward(self, velocity):
        self.pid_thread.pid_motors_speeds_update[0] = -velocity
        self.pid_thread.pid_motors_speeds_update[1] = -velocity

    def stop(self):
        self.pid_thread.pid_motors_speeds_update[0] = 0
        self.pid_thread.pid_motors_speeds_update[1] = 0

    def barrel_roll(self):
        pass

    def hit_object(self):
        pass

