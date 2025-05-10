import socket
import threading
import time
import re

import argparse

class ElevatorPLCSimulator(threading.Thread):
    def __init__(self, ip, port):
        super().__init__()
        self.ip=ip
        self.port=port
        self.client_socket=None
        self.connected=False
        self.status={
            "PM": "In_Service",
            "OP": "Auto",
            "CMD": "Door_Close",
            "Status": "Stopped_DownStair",  # Initial status
            # "Status": "Stopped_1F",
            "Location": "1F"
        }
        self.daemon=True
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
            self.client_socket=socket.socket(
                socket.AF_INET, socket.SOCK_STREAM)
            self.client_socket.connect((self.ip, self.port))
            self.connected=True
            print(f"Connected to server at {self.ip}:{self.port}")
        except Exception as e:
            print(f"Failed to connect to server: {e}")
            self.connected=False
            time.sleep(5)  # Wait before trying to reconnect

    def send_status_update(self):
        if self.connected:
            message=f"[PM_Mode:{self.status['PM']}][Operation_Mode:{self.status['OP']}]" \
                      f"[Status:{self.status['Status']}][Command:{self.status['CMD']}]" \
                        f"[Location:{self.status['Location']}]"
            try:
                self.client_socket.send(message.encode('utf-8'))
                print(f"Sent: {message}")
            except Exception as e:
                print(f"Failed to send message: {e}")
                self.connected=False
                self.client_socket.close()

    def listen_for_commands(self):
        try:
            data=self.client_socket.recv(1024).decode('utf-8')
            if data:
                print(f"Received: {data}")
                self.handle_command(data)
        except Exception as e:
            print(f"Error receiving data: {e}")
            self.connected=False
            self.client_socket.close()


    def handle_command(self, command):
        # Extract the command and status from the message using regex
        command_match =re.search(r'\[Command:(.+?)\]', command)
        status_match=re.search(r'\[Status:(.+?)\]', command)
        if command_match  and status_match:
            command=command_match .group(1)
            status=status_match.group(1)
            if status == 'Waiting':
                if command == "Call_Lifter_Up":
                    if self.status['Status'] == "Stopped_DownStair":
                        self.status['Status']="Moving_Up"
                        self.status['Location']="2F"
                    else:
                        self.status['Status']="Stopped_UpStair"
                        self.status['CMD']="Move_In"
                        self.status['Location']="2F"

                elif command == "Call_Lifter_Down":
                    if self.status['Status'] == "Stopped_UpStair":
                        self.status['Status'] == "Moving_Down"
                        self.status['Location']="2F"
                        time.sleep(3)
                        self.status['Status'] == "Stopped_DownStair"
                        self.status['Location']="1F"
                        self.status['CMD']="Move_In"

                    else:
                        self.status['Status']="Stopped_DownStair"
                        self.status['CMD']="Move_In"
                        self.status['Location']="1F"
                # open door
                elif command == "Door_Open":
                    self.status['Status']="Door_Opened"
                    self.status['CMD']="Move_In" # open door completed

                elif command == "Door_Close":
                    self.status['Status']="Door_Closed"

            elif status == "Moving_In":
                if command == "Door_Open":
                    self.status['Status']="Door_Opened"
                    self.status['CMD']="Move_In"

            elif status == "MoveIn_Complete":
                # MoveIn completed, waiting for door close
                if command == "Door_Open":
                    self.status['Status']="Door_Opened"
                    self.status['CMD']="Move_In"
                elif command == "Door_Close":
                    self.status['Status']="Door_Closed" # close door completed
                    self.status['CMD']="Move_In"
                elif command == "Move_Up": # go floor 2
                    self.status['Status']="Moving_Up"
                    self.status['CMD']="Move_In"
                    time.sleep(3)
                    self.status['Status']="Stopped_UpStair"
                    self.status['Location']="2F"
                    self.status['CMD']="Move_In" # go floor 2 completed
                elif command == "Move_Down": # go floor 1
                    self.status['Status']="Moving_Down"
                    self.status['CMD']="Move_In"
                    time.sleep(3)
                    self.status['Status']="Stopped_DownStair"
                    self.status['Location']="1F"
                    self.status['CMD']="Move_In" # go floor 1 completed

            elif status == "Moving_Out":
                if command == "Door_Open":
                    self.status['Status'] = "Door_Opened"
                    self.status['CMD'] = "Move_Out"
                # elif command == "Door_Close":
                #     self.status['Status'] = "Door_Closed"
                #     self.status['CMD'] = "Move_In"

            elif status == "MoveOut_Complete":
                if command == "Door_Open":
                    self.status['Status']="Door_Opened"
                    self.status['CMD']="Door_Open"
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
        self.connected=False
        if self.client_socket:
            try:
                self.client_socket.close()
            except Exception as e:
                print(f"Error closing socket: {e}")
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
