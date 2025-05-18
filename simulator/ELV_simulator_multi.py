import socket
import threading
import time
import re

import argparse

class ElevatorPLCSimulator(threading.Thread):
    def __init__(self, ip, port):
        super().__init__()
        self.ip = ip
        self.port = port
        self.client_socket = None
        self.connected = False
        self.status = {
            "PM": "Out_Service",
            "OP": "Auto",
            "CMD": "Door_Close",
            # "Status": "Stopped_DownStair",  # Initial status
            "Status": "Stopped_1F",
            "Location": "1F"
        }
        self.daemon = True
        self.start()

    # def run(self):
    #     self.connect()
    #     while self.connected:
    #         time.sleep(0.5)  # Simulate cyclic refresh
    #         self.send_status_update()
    #         # Listening for commands is done in the same thread for simplicity
    #         self.listen_for_commands()

    def run(self):
        while True:
            if not self.connected:
                self.connect()
            time.sleep(1)  # Simulate cyclic refresh
            if self.connected:
                self.send_status_update()
                self.listen_for_commands()


    def connect(self):
        try:
            self.client_socket = socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.ip, self.port))
            self.connected = True
            print("Connected to server at {}:{}".format(self.ip, self.port))
        except Exception as e:
            print("Failed to connect to server: {}".format(e))
            self.connected = False
            time.sleep(5)  # Wait before trying to reconnect

    def send_status_update(self):
        if self.connected:
            # message = f"[PM_Mode:{self.status['PM']}][Operation_Mode:{self.status['OP']}]" \
            #           f"[Status:{self.status['Status']}][Command:{self.status['CMD']}]" \
            #             f"[Location:{self.status['Location']}]"
            message = ("[PM_Mode:{PM}][Operation_Mode:{OP}]"
                   "[Status:{Status}][Command:{CMD}]"
                   "[Location:{Location}]").format(**self.status)
            try:
                self.client_socket.send(message.encode('utf-8'))
                print("Sent: {}".format(message))
            except Exception as e:
                print("Failed to send message: {}".format(e))
                self.connected = False
                self.client_socket.close()

    def listen_for_commands(self):
        try:
            data = self.client_socket.recv(1024).decode('utf-8')
            if data:
                print("Received: {}".format(data))
                self.handle_command(data)
        except Exception as e:
            print("Error receiving data: {}".format(e))
            self.connected = False
            self.client_socket.close()


    def handle_command(self, command):
        # Extract the command and status from the message using regex
        command_match  = re.search(r'\[Command:(.+?)\]', command)
        status_match = re.search(r'\[Status:(.+?)\]', command)
        pm_match = re.search(r'\[PM_Mode:(.+?)\]', command)
        if pm_match:
            pm_mode = pm_match.group(1)
            if pm_mode == "In_Service":
                self.status['PM'] = "In_Service"
                self.status['Status'] = "Stopped_1F"
        if command_match  and status_match:
            command = command_match .group(1)
            status = status_match.group(1)
            if status == 'Waiting':
                m = re.match(r'Call_Lifter_(\d+)F', command)
                if m:
                    target_floor = int(m.group(1))
                    current_floor = int(self.status['Location'].replace("F", ""))
                    if current_floor != target_floor:
                        self.status['Status'] = f"Moving_{target_floor}F"
                        self.send_status_update()
                        print("Simulating elevator moving from {} to {}F...".format(self.status['Location'], target_floor))
                    time.sleep(3)  # 模擬移動延遲
                    self.status['Status'] = f"Stopped_{target_floor}F"
                    self.status['Location'] = f"{target_floor}F"
                    self.status['CMD'] = "Move_In"
                    self.send_status_update()
                    return
                # open door
                elif command == "Door_Open":
                    # self.status['Status'] = "Door_Opening"
                    # self.send_status_update()
                    # time.sleep(3)
                    self.status['Status'] = "Door_Opened"
                    self.status['CMD'] = "Move_In" # open door completed

                elif command == "Door_Close":
                    # self.status['Status'] = "Door_Closing"
                    # self.send_status_update()
                    # time.sleep(3)
                    self.status['Status'] = "Door_Closed"

            elif status == "Moving_In":
                if command == "Door_Open":
                    self.status['Status'] = "Door_Opened"
                    self.status['CMD'] = "Move_In"

            elif status == "MoveIn_Complete":
                # MoveIn completed, waiting for door close
                if command == "Door_Open":
                    self.status['Status'] = "Door_Opening"
                    self.send_status_update()
                    time.sleep(3)
                    self.status['Status'] = "Door_Opened"
                    self.status['CMD'] = "Move_In"
                elif command == "Door_Close":
                    self.status['Status'] = "Door_Closing"
                    self.send_status_update()
                    time.sleep(3)
                    self.status['Status'] = "Door_Closed" # close door completed
                    self.status['CMD'] = "Move_In"
                # elif command == "Move_Up": # go floor 2
                #     self.status['Status'] = "Moving_Up"
                #     self.status['CMD'] = "Move_In"
                #     time.sleep(3)
                #     self.status['Status'] = "Stopped_UpStair"
                #     self.status['Location'] = "2F"
                #     self.status['CMD'] = "Move_In" # go floor 2 completed
                # elif command == "Move_Down": # go floor 1
                #     self.status['Status'] = "Moving_Down"
                #     self.status['CMD'] = "Move_In"
                #     time.sleep(3)
                #     self.status['Status'] = "Stopped_DownStair"
                #     self.status['Location'] = "1F"
                #     self.status['CMD'] = "Move_In" # go floor 1 completed
                else:
                    # 處理移動命令，動態解析如 "Move_3F"
                    m = re.match(r'Move_(\d+)F', command)
                    if m:
                        target_floor = int(m.group(1))
                        current_floor = int(self.status['Location'].replace("F", ""))
                        if current_floor != target_floor:
                            self.status['Status'] = f"Moving_{target_floor}F"
                            self.status['CMD'] = "Move_In"
                            print("Simulating elevator moving from {} to {}F...".format(self.status['Location'], target_floor))
                            self.send_status_update()
                        # self.status['Status'] = f"Moving_{target_floor}F"

                        time.sleep(3)  # 模擬移動延遲
                        self.status['Status'] = f"Stopped_{target_floor}F"
                        self.status['Location'] = f"{target_floor}F"
                        self.status['CMD'] = "Move_In"

            elif status == "Moving_Out":
                if command == "Door_Open":
                    self.status['Status'] = "Door_Opened"
                    self.status['CMD'] = "Immediate_Stop"
                elif command == "Door_Close":
                    self.status['Status'] = "Door_Closed"
                    self.status['CMD'] = "Move_In"

            elif status == "MoveOut_Complete":
                if command == "Door_Open":
                    self.status['Status'] = "Door_Opened"
                    self.status['CMD'] = "Door_Open"
                elif command == "Door_Close":
                    self.status['Status'] = "Door_Closing"
                    self.status['CMD'] = "Door_Close"
                    time.sleep(3)
                    self.status['Status'] = "Door_Closed"
                    self.status['CMD'] = "Door_Close"



            # ... add additional command handlers as necessary
            # After handling command, send the updated status
        self.send_status_update()

    def stop(self):
        self.connected = False
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception as e:
                print("Error closing socket: {}".format(e))
        print("Client stopped.")


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="Elevator PLC Simulator")
    parser.add_argument('-i', '--ip',
                        help='Server IP address',
                        default='127.0.0.1')
    parser.add_argument('-p', '--port',
                        help='Server port number',
                        type=int,
                        default=4096)
    args = parser.parse_args()

    ip = args.ip
    port = args.port
    # ip = '127.0.0.1'  # Server IP address
    # port = 4096  # Server port number
    elevator_plc = ElevatorPLCSimulator(ip, port)
    try:
        while True:
            time.sleep(1)
            # The loop can be used to simulate different behaviors or wait for user input to simulate commands
    except KeyboardInterrupt:
        print("Simulation interrupted.")
    finally:
        elevator_plc.stop()
