import json
import time
import random
import logging
from datetime import datetime
import paho.mqtt.client as mqtt
import threading
from web_service_log import *

class K11BridgeService:
    def __init__(self):
        self.function_name = ""
        self.broker = "localhost"
        self.port = 1883
        self.request_topic = "WBG/CIM/AUTOLINE/MCS"
        # 移除 response_topic，因為不需要監聽回應

        self.client = mqtt.Client()
        self.client.on_connect = self.on_connect
        # 移除 on_message，因為不需要處理回應
    
    def connect(self):
        """連接到 MQTT broker"""
        self.client.connect(self.broker, self.port)
        self.client.loop_start()  # 使用 loop_start 而不是 loop_forever
        time.sleep(0.5)  # 等待連接建立

    def disconnect(self):
        """斷開 MQTT 連接"""
        self.client.loop_stop()
        self.client.disconnect()

    def on_connect(self, client, userdata, flags, rc):
        call_ascbridge_service_logger.info("Connected to MQTT broker with result code {}".format(rc))
        # 移除 subscribe，因為不需要監聽回應

    def call_service(self, request_json_dict):
        try:
            call_ascbridge_service_logger.info("request_json_dict{}".format(request_json_dict))
            request_json_string = json.dumps(request_json_dict)
            result = self.client.publish(self.request_topic, request_json_string)
            
            # 檢查發送狀態
            if result.rc == mqtt.MQTT_ERR_SUCCESS:
                call_ascbridge_service_logger.info("Message published successfully")
                return True
            else:
                call_ascbridge_service_logger.error("Failed to publish message, error code: {}".format(result.rc))
                return False
        
        except Exception as e:
            call_mes_service_logger.error("Exception: {}".format(e))
            return False
        
# Example usage
if __name__ == "__main__":
    k11_service = K11BridgeService()
    
    # 連接到 MQTT broker
    k11_service.connect()
    
    random_number = f"{random.randint(1, 99999):05d}"
    commandid="{}{}".format(datetime.now().strftime("%Y%m%d%H%M%S"),random_number)
    

    message_list=[
        {
            "TRANSID":"{}_{}".format(commandid,1),
            "SOURCEPORT": "CRR_01_016",
            "DESTPORT": "E0167851_I2",
            "CARRIERID": [
                "CARRIER0014"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,1),
            "SOURCEPORT": "CRR_01_015",
            "DESTPORT": "E0167851_O2",
            "CARRIERID": [
                "CARRIER0013"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,1),
            "SOURCEPORT": "CRR_01_014",
            "DESTPORT": "E0167851_I2",
            "CARRIERID": [
                "CARRIER0012"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,1),
            "SOURCEPORT": "CRR_01_013",
            "DESTPORT": "E0167851_O1",
            "CARRIERID": [
                "CARRIER0011"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,1),
            "SOURCEPORT": "CRR_01_001",
            "DESTPORT": "E0167851_I1",
            "CARRIERID": [
                "CARRIER001"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,2),
            "SOURCEPORT": "CRR_01_002",
            "DESTPORT": "E0167736_I2",
            "CARRIERID": [
                "CARRIER002"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,3),
            "SOURCEPORT": "CRR_01_003",
            "DESTPORT": "E0167736_I3",
            "CARRIERID": [
                "CARRIER003"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,4),
            "SOURCEPORT": "CRR_01_004",
            "DESTPORT": "E0167736_I4",
            "CARRIERID": [
                "CARRIER004"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,5),
            "SOURCEPORT": "CRR_01_005",
            "DESTPORT": "E0167736_I5",
            "CARRIERID": [
                "CARRIER005"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,6),
            "SOURCEPORT": "CRR_01_006",
            "DESTPORT": "E0167736_I6",
            "CARRIERID": [
                "CARRIER006"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,7),
            "SOURCEPORT": "CRR_01_007",
            "DESTPORT": "E0167736_O1",
            "CARRIERID": [
                "CARRIER007"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,8),
            "SOURCEPORT": "CRR_01_008",
            "DESTPORT": "E0167736_O2",
            "CARRIERID": [
                "CARRIER008"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,9),
            "SOURCEPORT": "CRR_01_009",
            "DESTPORT": "E0167736_O3",
            "CARRIERID": [
                "CARRIER009"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,10),
            "SOURCEPORT": "CRR_01_010",
            "DESTPORT": "E0167736_O4",
            "CARRIERID": [
                "CARRIER010"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,11),
            "SOURCEPORT": "CRR_01_011",
            "DESTPORT": "E0167736_O5",
            "CARRIERID": [
                "CARRIER011"
                
            ]
        },
        {
            "TRANSID":"{}_{}".format(commandid,12),
            "SOURCEPORT": "CRR_01_012",
            "DESTPORT": "E0167736_O6",
            "CARRIERID": [
                "CARRIER012"
                
            ]
        },
        
            
            
    ]

    # 如果需要隨機排序，取消註解下面這行
    # random.shuffle(message_list)

    print(message_list)

    MCS_require_json_dict={
        "CMD": "ROBOT",
        "CMD_ID": "R007",
        "TID": commandid,
        "ID_DESC":  "ROBOT_SOURCEPORT_TO_DESTPORT",
        "MESSAGE": message_list
    }
    
    # Send the request
    success = k11_service.call_service(MCS_require_json_dict)
    if success:
        print("Request sent successfully")
    else:
        print("Failed to send request")
    
    # 斷開連接
    k11_service.disconnect()
    print("MQTT connection closed") 