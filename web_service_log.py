import logging
import logging.handlers as log_handler
import os
from colorlog import ColoredFormatter as cl 
format_str="%(asctime)s-[%(funcName)s]-[line:%(lineno)d]-[%(levelname)s]-[%(threadName)s]:%(message)s"
date_format='%Y-%m-%d %H:%M:%S'
cformat='%(log_color)s' + format_str
colors={'DEBUG': 'green',
          'INFO': 'cyan',
          'INFO2':'yellow',
          'WARNING': 'bold_yellow',
          'ERROR': 'bold_red',
          'CRITICAL': 'bg_purple'}
formatter=cl(cformat, date_format, log_colors=colors)
def addLoggingLevel(levelName, levelNum, methodName=None):
    if not methodName:
        methodName=levelName.lower()
    if hasattr(logging, levelName):
        raise AttributeError('{} already defined in logging module'.format(levelName))
    if hasattr(logging, methodName):
        raise AttributeError('{} already defined in logging module'.format(methodName))
    if hasattr(logging.getLoggerClass(), methodName):
        raise AttributeError('{} already defined in logger class'.format(methodName))
    def logForLevel(self, message, *args, **kwargs):
        if self.isEnabledFor(levelNum):
            self._log(levelNum, message, args, **kwargs)
    def logToRoot(message, *args, **kwargs):
        logging.log(levelNum, message, *args, **kwargs)
    logging.addLevelName(levelNum, levelName)
    setattr(logging, levelName, levelNum)
    setattr(logging.getLoggerClass(), methodName, logForLevel)
    setattr(logging, methodName, logToRoot)
if not os.path.isdir("./log"):
    print("no file log")
    os.mkdir("./log")
#####################################################################################################################################
action_logger=logging.getLogger("action_logger")
action_logger.setLevel(logging.DEBUG)
streamLogHandler=logging.StreamHandler()
streamLogHandler.setLevel(logging.DEBUG)
streamLogHandler.setFormatter(formatter)
action_logger.addHandler(streamLogHandler)
filename=os.path.join("log", "action_logger.log")
LogFileHandler=log_handler.TimedRotatingFileHandler(filename, when='midnight', interval=1, backupCount=30, encoding="utf-8")
LogFileHandler.setLevel(logging.DEBUG)
LogFileHandler.setFormatter(logging.Formatter("%(asctime)s-[%(filename)s]-[%(funcName)s]-[line:%(lineno)d]-[%(levelname)s]-[%(threadName)s]: %(message)s"))
action_logger.addHandler(LogFileHandler)

#####################################################################################################################################
path_logger=logging.getLogger("path_logger")
path_logger.setLevel(logging.DEBUG)
streamLogHandler=logging.StreamHandler()
streamLogHandler.setLevel(logging.DEBUG)
streamLogHandler.setFormatter(formatter)
path_logger.addHandler(streamLogHandler)
filename=os.path.join("log", "path_logger.log")
LogFileHandler=log_handler.TimedRotatingFileHandler(filename, when='midnight', interval=1, backupCount=30, encoding="utf-8")
LogFileHandler.setLevel(logging.DEBUG)
LogFileHandler.setFormatter(logging.Formatter("%(asctime)s-[%(filename)s]-[%(funcName)s]-[line:%(lineno)d]-[%(levelname)s]-[%(threadName)s]: %(message)s"))
path_logger.addHandler(LogFileHandler)

#####################################################################################################################################
node_logger=logging.getLogger("node_logger")
node_logger.setLevel(logging.DEBUG)
streamLogHandler=logging.StreamHandler()
streamLogHandler.setLevel(logging.DEBUG)
streamLogHandler.setFormatter(formatter)
node_logger.addHandler(streamLogHandler)
filename=os.path.join("log", "node_logger.log")
LogFileHandler=log_handler.TimedRotatingFileHandler(filename, when='midnight', interval=1, backupCount=30, encoding="utf-8")
LogFileHandler.setLevel(logging.DEBUG)
LogFileHandler.setFormatter(logging.Formatter("%(asctime)s-[%(filename)s]-[%(funcName)s]-[line:%(lineno)d]-[%(levelname)s]-[%(threadName)s]: %(message)s"))
node_logger.addHandler(LogFileHandler)


#####################################################################################################################################
tool_logger=logging.getLogger("tool_logger")
tool_logger.setLevel(logging.DEBUG)
streamLogHandler=logging.StreamHandler()
streamLogHandler.setLevel(logging.DEBUG)
streamLogHandler.setFormatter(formatter)
tool_logger.addHandler(streamLogHandler)
filename=os.path.join("log", "tool_logger.log")
LogFileHandler=log_handler.TimedRotatingFileHandler(filename, when='midnight', interval=1, backupCount=30, encoding="utf-8")
LogFileHandler.setLevel(logging.DEBUG)
LogFileHandler.setFormatter(logging.Formatter("%(asctime)s-[%(filename)s]-[%(funcName)s]-[line:%(lineno)d]-[%(levelname)s]-[%(threadName)s]: %(message)s"))
tool_logger.addHandler(LogFileHandler)

#####################################################################################################################################
tr_wq_lib_logger=logging.getLogger("tr_wq_lib_logger")
tr_wq_lib_logger.setLevel(logging.DEBUG)
streamLogHandler=logging.StreamHandler()
streamLogHandler.setLevel(logging.DEBUG)
streamLogHandler.setFormatter(formatter)
tr_wq_lib_logger.addHandler(streamLogHandler)
filename=os.path.join("log", "tr_wq_lib_logger.log")
LogFileHandler=log_handler.TimedRotatingFileHandler(filename, when='midnight', interval=1, backupCount=30, encoding="utf-8")
LogFileHandler.setLevel(logging.DEBUG)
LogFileHandler.setFormatter(logging.Formatter("%(asctime)s-[%(filename)s]-[%(funcName)s]-[line:%(lineno)d]-[%(levelname)s]-[%(threadName)s]: %(message)s"))
tr_wq_lib_logger.addHandler(LogFileHandler)

#####################################################################################################################################
tsc_logger=logging.getLogger("tsc_logger")
tsc_logger.setLevel(logging.DEBUG)
streamLogHandler=logging.StreamHandler()
streamLogHandler.setLevel(logging.DEBUG)
streamLogHandler.setFormatter(formatter)
tsc_logger.addHandler(streamLogHandler)
filename=os.path.join("log", "tsc_logger.log")
LogFileHandler=log_handler.TimedRotatingFileHandler(filename, when='midnight', interval=1, backupCount=30, encoding="utf-8")
LogFileHandler.setLevel(logging.DEBUG)
LogFileHandler.setFormatter(logging.Formatter("%(asctime)s-[%(filename)s]-[%(funcName)s]-[line:%(lineno)d]-[%(levelname)s]-[%(threadName)s]: %(message)s"))
tsc_logger.addHandler(LogFileHandler)