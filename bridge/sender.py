import logging
import threading
import time
from datetime import datetime

import queue

from global_variables import SocketIO
import global_variables
logger=logging.getLogger('tsc')


"""
Thread-safe lock mechanism with timeout support module.
"""

from threading import ThreadError, current_thread
from queue import Queue, Full, Empty


class TimeoutLock(object):
    """
    Thread-safe lock mechanism with timeout support.
    """

    def __init__(self, mutex=True):
        """
        Constructor.
        Mutex parameter specifies if the lock should behave like a Mutex, and
        thus use the concept of thread ownership.
        """
        self._queue=Queue(maxsize=1)
        self._owner=None
        self._mutex=mutex

    def acquire(self, timeout=0):
        """
        Acquire the lock.
        Returns True if the lock was succesfully acquired, False otherwise.

        Timeout:
        - < 0 : Wait forever.
        -   0 : No wait.
        - > 0 : Wait x seconds.
        """
        th=current_thread()
        try:
            self._queue.put(
                th, block=(timeout != 0),
                timeout=(None if timeout < 0 else timeout)
            )
        except Full:
            return False

        self._owner=th
        return True

    def release(self):
        """
        Release the lock.
        If the lock is configured as a Mutex, only the owner thread can release
        the lock. If another thread attempts to release the lock a
        ThreadException is raised.
        """
        th=current_thread()
        if self._mutex and th != self._owner:
            raise ThreadError('This lock isn\'t owned by this thread.')

        self._owner=None
        try:
            self._queue.get(False)
            return True
        except Empty:
            logger.error('This lock was released already.')


class Singleton(object):
    _obj=None

    def __new__(cls, *args, **kwargs):
        if cls._obj is None:
            cls._obj=super(Singleton, cls).__new__(cls)

        return cls._obj


class SkipExecution(Exception):
    pass


class LimitRunInterval(object):

    def __init__(self, interval=1.0, step_interval=0.01):
        self.wait_interval=interval
        self.step_interval=step_interval
        self.run_time=0

    def __enter__(self):
        now=time.time()

        # force wait
        if now - self.run_time > self.wait_interval:
            self.run_time=now
            return True

        return False

    def __exit__(self, exc_type, exc_val, exc_tb):
        time.sleep(self.step_interval)

    def update_interval(self, interval):
        self.wait_interval=interval


class MessageHandler(Singleton):

    def __init__(self):
        self.seq_count=0
        self.seq_count_lock=threading.Lock()

    def get_seq_count(self, now_stamp):
        with self.seq_count_lock:
            self.seq_count=(self.seq_count + 1) % 10000
            now=datetime.fromtimestamp(now_stamp)
            seq=now.strftime('%Y%m%d%H%M%S') + '{:04d}'.format(self.seq_count)

        return seq

    def __call__(self, event, obj, sync=False):
        now_timestamp=time.time()
        obj['timestamp']=now_timestamp
        obj['seq']=self.get_seq_count(now_timestamp)
        obj['ControllerID']=global_variables.controller_id
        return event, obj, sync


class Sender(object):

    def connected(self):
        raise NotImplementedError

    def send(self, *args, **kwargs):
        raise NotImplementedError


class SocketioSender(Sender):

    def __init__(self):
        self.sync_lock=threading.Lock()
        self.emit_lock=TimeoutLock()

        # sync message seq pool
        self.sync_pool=list()

        # default wait time 0.05s
        self.message_wait_time=0.01

        # section, calculate message length, rate
        self.section, self.cml, self.rate=10, 50, 0.1
        self.msg_times, self.msg_back_time=list(), dict()
    @property
    def sender_kwargs(self):
        return {
            'namespace': '/{}'.format(global_variables.controller_id),
        }

    def connected(self):
        return SocketIO.connected

    def send(self, event, obj, sync):
        func=getattr(self, "%s_send" % ('sync' if sync else 'async'))

        # if not sync:
        #     threading.Thread(target=func, args=(event, obj)).start()
        # else:
        func(event, obj)

        #logger.info('wait_time %s' % self.message_wait_time)
        time.sleep(self.message_wait_time)

    def _ack(self, *args):
        if not args or len(args) < 2:
            return

        try:
            seq=args[1]
        except:
            return
        
        if seq in self.msg_back_time:
            self.msg_times.append(time.time() - self.msg_back_time[seq])
            del self.msg_back_time[seq]

        if len(self.msg_times) > self.cml:
            self.message_wait_time=round(min(sum(self.msg_times[-self.cml:]) / self.cml * self.rate, 0.1), 2)
            self.msg_times=self.msg_times[self.section:]

        # When msg_back_time is too large, delete messages that have already exceeded 5 seconds.
        if len(self.msg_back_time) > 1000:
            now=time.time()
            del_keys=[k for k, v in self.msg_back_time.items() if (now - v) > 5]
            for k in del_keys:
                del self.msg_back_time[k]

    def sync_send(self, event, obj):

        self.sync_pool.append(obj['seq'])

        def _callback(_, seq, *args):
            try:
                if seq in self.sync_pool:
                    self.sync_pool.remove(seq)
            except Exception as e:
                logger.error('args %s , %s' % (args, str(e)))

        sync_limit=LimitRunInterval(interval=5.0)

        # Message Send already in same threading, don't need lock to sync
        # with self.sync_lock:
        retry=0

        while obj['seq'] in self.sync_pool:
            with sync_limit as go:
                if not go:
                    continue

                if not retry:
                    #logger.info('socketIO seq:{} sync STARTED. {}'.format(obj['seq'], event))
                    pass

                if not self.connected():
                    retry += 1
                    logger.error('socketIO seq:{} DISCONNECT. {}, retry:{}'.format(obj['seq'], event, retry))

                    time.sleep(2)
                    continue

                self._emit(event, obj, callback=_callback, **self.sender_kwargs)
                #logger.info('socketIO seq:{} sync SUCCESS. {}'.format(obj['seq'], self.sender_kwargs))

                retry += 1
                continue
        # else:
        #     logger.debug('socketIO seq:{} sync COMPLETED. {}'.format(obj['seq'], event))

    def async_send(self, event, obj):
        self.msg_back_time[obj['seq']]=time.time()

        self._emit(event, obj, callback=self._ack, **self.sender_kwargs)
        # logger.info('socketIO seq:{} async COMPLETED. {}'.format(obj['seq'], self.sender_kwargs))

    def _emit(self, event, obj, **kwargs):
        # ac=self.emit_lock.acquire(timeout=2)
        try:
            SocketIO.h.emit(event, obj, **kwargs)
        except Exception as e:
            logger.error(
                'socketIO seq:%s ERROR. Exception in sync_output thread %s' % (obj['seq'], e),
                exc_info=True
            )
        # finally:
        #     if ac:
        #         self.emit_lock.release()


class ZmqSender(Sender):
    def connected(self):
        return global_variables.zmq_h

    def send(self, *args, **kwargs):
        
        event=args[0]
        obj=args[1]
        sync=kwargs.get('sync', False)  
        
        global_variables.zmq_h.send_json((event, obj, obj['seq']))


class MessageController(threading.Thread):
    __instance=None
    senders=list()

    message_handler=MessageHandler()
    output_lock=threading.Lock()

    api_queue=queue.Queue(maxsize=10 ** 6)

    @classmethod
    def get_instance(cls):
        if cls.__instance is None:
            cls()

        return cls.__instance

    @classmethod
    def getInstance(cls):
        return cls.get_instance()

    @classmethod
    def register_sender(cls, sender):
        if not isinstance(sender, Sender):
            return

        cls.senders.append(sender)

    def __init__(self):
        self.__instance=self
        threading.Thread.__init__(self)
        self.setDaemon(True)
        self.start()

    @classmethod
    def output(cls, event, obj, sync=False):
        event, obj, sync=cls.message_handler(event, obj, sync)
        with cls.output_lock:
            if cls.api_queue.full():
                left_event, left_obj, left_sync=cls.api_queue.get()
                logger.warning('message seq: {} DROP. api_queue full {} {}. Current queue size: {}'.format(
                    left_obj["seq"], left_event, left_sync, cls.api_queue.qsize()
                ))

            try:
                cls.api_queue.put_nowait((event, obj, sync))
            except Exception as e:
                logger.error(
                    'message seq: {} Put Error. {} {} {}.'.format(obj["seq"], str(e), event, sync),
                    exc_info=True
                )

    def run(self):
        while True:
            time.sleep(0.01)

            if not self.senders[0].connected():
                continue

            event, obj, sync=self.api_queue.get()
            #logger.debug('message seq: {} {} {} {}'.format(obj["seq"], obj, event, sync))
            for sender in self.senders:
                if sender.connected():
                    try:
                        sender.send(event, obj, sync)
                    except Exception as e:
                        logger.error('{} seq:{} Send Error. {} {} {}.'.format(
                            sender.__class__.__name__, obj["seq"], str(e), event, sync),
                            exc_info=True
                        )


MessageController.register_sender(SocketioSender())
MessageController.register_sender(ZmqSender())
