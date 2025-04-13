import os
import time
import logging
import logging.handlers as log_handler
import semi.e88_stk_equipment as E88STK
import semi.e88_equipment as E88
import semi.e82_equipment as E82

import traceback

class E88_Host():
    h_list=[]
    host_map_h={}
    client_map_h={}
    default_h=0

    @classmethod
    def getInstance(cls, client='default'):
        f=cls.client_map_h.get(client)
        if client and f:
            return f
        else:
            return cls.default_h
    
    @classmethod
    def mapping(cls, client, host):
        h=cls.host_map_h.get(host)
        if h:
            cls.client_map_h[client]=h

    def __init__(self, address, port, name, mdln, deciveid=0):
        self.address=address
        self.port=port
        self.mdln=mdln
        self.name=name

        log_name="Gyro_Erackc_{}".format(name)
        
        fileHandler=log_handler.TimedRotatingFileHandler(os.path.join("log", "Gyro_Erackc_{}.log".format(name)), when='midnight', interval=1, backupCount=30)
        fileHandler.setFormatter(logging.Formatter("%(asctime)s: %(message)s"))
        fileHandler.setLevel(logging.DEBUG)
        logger=logging.getLogger(log_name)
        logger.setLevel(logging.DEBUG)
        for lh in logger.handlers[:]:
            logger.removeHandler(lh)
            lh.close()
        logger.addHandler(fileHandler)

        print('--------------------------------------------------------------------------------')
        print('Create E88 host:', port, False, deciveid, name, mdln, log_name)
        print('--------------------------------------------------------------------------------')
        h=E88.E88Equipment('', port, False, deciveid, name, mdln=mdln, log_name=log_name)
        h.linktestTimeout=30
        h.rcmd_auto_reply=True
        #h.enable()
        E88_Host.h_list.append(h)
        E88_Host.host_map_h[name]=h #set last h as default
        E88_Host.default_h=h #set last h as default

class E88_STK_Host():
    h_list=[]
    host_map_h={}
    client_map_h={}
    default_h=0

    @classmethod
    def getAllInstance(cls):
        return cls.h_list

    @classmethod
    def getInstance(cls, client='default'):
        f=cls.client_map_h.get(client)
        if client and f:
            return f
        else:
            return cls.default_h
    
    @classmethod
    def mapping(cls, client, host):
        h=cls.host_map_h.get(host)
        if h:
            cls.client_map_h[client]=h

    def __init__(self, address, port, name, mdln):
        self.address=address
        self.port=port
        self.mdln=mdln
        self.name=name

        log_name="Gyro_Stkc_{}".format(name)
        filename=os.path.join("log", "Gyro_Stkc_{}.log".format(name))

        commLogFileHandler=log_handler.TimedRotatingFileHandler(filename, when='midnight', interval=1, backupCount=30)
        commLogFileHandler.setFormatter(logging.Formatter("%(asctime)s: %(message)s"))
        commLogFileHandler.setLevel(logging.DEBUG)
        logger=logging.getLogger(log_name)
        logger.setLevel(logging.DEBUG)
        for lh in logger.handlers[:]:
            logger.removeHandler(lh)
            lh.close()
        logger.addHandler(commLogFileHandler)

        print('--------------------------------------------------------------------------------')
        print('Create E88STK host:', port, False, 0, name, mdln, log_name)
        print('--------------------------------------------------------------------------------')
        h=E88STK.E88Equipment('', port, False, 0, name, mdln=mdln, log_name=log_name)
        h.linktestTimeout=30
        h.rcmd_auto_reply=True
        #h.enable()
        E88_STK_Host.h_list.append(h)
        E88_STK_Host.host_map_h[name]=h #set last h as default
        E88_STK_Host.default_h=h #set last h as default


class E82_Host():
    h_list=[]
    host_map_h={}
    client_map_h={}
    default_h=0

    @classmethod
    def getAllInstance(cls):
        return cls.h_list

    @classmethod
    def getInstance(cls, client='default'):
        f=cls.client_map_h.get(client)
        if client and f:
            return f
        else:
            return cls.default_h

    @classmethod
    def mapping(cls, client, host):
        h=cls.host_map_h.get(host)
        if h:
            cls.client_map_h[client]=h


    def __init__(self, address, port, name, mdln, deciveid=0):
        self.address=address
        self.port=port
        self.mdln=mdln
        self.name=name

        log_name="Gyro_Agvc_{}".format(name)
        filename=os.path.join("log", "Gyro_Agvc_{}.log".format(name))

        commLogFileHandler=log_handler.TimedRotatingFileHandler(filename, when='midnight', interval=1, backupCount=30)
        commLogFileHandler.setFormatter(logging.Formatter("%(asctime)s: %(message)s"))
        commLogFileHandler.setLevel(logging.DEBUG)
        logger=logging.getLogger(log_name)
        logger.setLevel(logging.DEBUG)
        for lh in logger.handlers[:]:
            logger.removeHandler(lh)
            lh.close()
        logger.addHandler(commLogFileHandler)
        print('--------------------------------------------------------------------------------')
        print('Create E82 host:', port, False, deciveid, name, mdln, log_name)
        print('--------------------------------------------------------------------------------')
        h=E82.E82Equipment('', port, False, deciveid, name, mdln=mdln, log_name=log_name)
        h.linktestTimeout=30
        #h.enable()
        E82_Host.h_list.append(h)
        E82_Host.host_map_h[name]=h #host to h
        E82_Host.default_h=h #set last h as default h
        

        