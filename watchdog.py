#!/usr/bin/python3
import glob
import logging
from logging.handlers import TimedRotatingFileHandler
import queue
import os
from subprocess import Popen
import argparse
import psutil
import configparser
from time import sleep
from pprint import pformat
# ---------- Version Info ----------#
__version__ = "v0.0.2"

LOG = None
CONFIG = None


def check_file(file, on_exit=False):
    """
    Check if a file exists or not.
    :param file: file with path
    :param on_exit: if True and file doesn't exist then exit the program. Else just warn.
    """
    if not os.path.isfile(file):
        if on_exit:
            LOG.error("{} isn't a file. Exiting.".format(file))
            delete_pidfile()
            exit(1)
        LOG.warning("{} isn't a file.".format(file))
        return False
    return True


def load_config(config_file):
    global CONFIG
    CONFIG = configparser.RawConfigParser()

    # check config file
    check_file(config_file, on_exit=True)

    CONFIG.optionxform = lambda option: option
    CONFIG.read(config_file)


def ensure_uniqness(pid_file=".watchdog.pid"):
    """
    Ensure only 1 instance of script run at a time
    """
    pid = str(os.getpid())
    if os.path.exists(pid_file):
        print("{} already exists, exiting".format(pid_file))
        exit(0)
    with open(pid_file, 'w') as f:
        f.write(pid)


def delete_pidfile(pid_file=".watchdog.pid"):
    """
    Delete pid file if exists
    :param pid_file: filename with path
    :return:
    """
    if os.path.exists(pid_file):
        os.unlink(pid_file)


class Logger:
    logger = logging.getLogger(__name__)

    def __init__(self, level='INFO', console=True, logfile_backup=5):
        self.listener = None
        self.logfile_backup = logfile_backup
        self.console_logging = console
        if level == 'DEBUG':
            self.level = logging.DEBUG
        elif level == 'WARN':
            self.level = logging.WARNING
        elif level == 'ERROR':
            self.level = logging.ERROR
        elif level == 'CRITICAL':
            self.level = logging.CRITICAL
        else:
            self.level = logging.INFO

        self.configuration()
        self.start()

    def start(self):
        if self.listener:
            self.listener.start()

    def stop(self):
        for h in Logger.logger.handlers:
            h.flush()
        if self.listener:
            self.listener.stop()
        logging.shutdown()

    def configuration(self):
        log_formatter = logging.Formatter('%(asctime)s : %(levelname)s : %(funcName)s : %(message)s')
        logging_file = os.path.join(
            os.getcwd(),
            os.path.splitext(os.path.basename(__file__))[0] + '.log'
        )
        Logger.logger.setLevel(self.level)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        console_handler.setLevel(self.level)
        if self.console_logging:
            Logger.logger.addHandler(console_handler)

        file_handler = TimedRotatingFileHandler(logging_file, when='h', interval=1,
                                                backupCount=self.logfile_backup)
        file_handler.setFormatter(log_formatter)
        file_handler.setLevel(self.level)

        que = queue.Queue(-1)  # no limit on size
        queue_handler = logging.handlers.QueueHandler(que)
        self.listener = logging.handlers.QueueListener(que, file_handler)
        Logger.logger.addHandler(queue_handler)

    @staticmethod
    def get_logger():
        return Logger.logger


LOG = logging.getLogger(__name__)


class Watchdog:
    """
    Watchdog class
    """

    def __init__(self):
        LOG.info("Initializing Watchdog...")
        self.monitored_processes = dict()
        self.monitored_process_cmd = ['python /home/ubuntu/Watchdog/test/while.py',
                                      'python /home/ubuntu/Watchdog/test/img_compare.py']  # <- fetch from config file
        self.update_process_dict()

    @staticmethod
    def get_process_list(startswith='python'):
        # {p.pid: p.info for p in psutil.process_iter(['name', 'username'])}
        '''
        for process in psutil.process_iter(['pid', 'name', 'username', 'cmdline']):
            if process.info.get('name').startswith('python'):
                print(process.info)
        '''
        filtered_processes = {p.pid: p for p in psutil.process_iter(['name', 'username', 'cmdline', 'create_time'])
                              if p.info.get('name').startswith(startswith)}
        return filtered_processes

    def update_process_dict(self):
        LOG.info("Started")
        # load_config()
        current_filtered_processes = self.get_process_list()
        LOG.debug(pformat(current_filtered_processes))
        self.monitored_processes = dict()
        for process in current_filtered_processes.values():
            cmdline = ' '.join(process.info.get('cmdline'))
            LOG.debug(cmdline)
            if cmdline in self.monitored_process_cmd:
                self.monitored_processes[cmdline] = process
                self.monitored_process_cmd.remove(cmdline)

            if len(self.monitored_process_cmd) == 0:
                return
        # commands for which no process exists
        for cmdline in self.monitored_process_cmd:
            self.monitored_processes[cmdline] = None

    @staticmethod
    def start_process(start_cmd):
        """
        Starts a process
        :param start_cmd: string or list
        :return: pid or None
        """
        LOG.info("Started for {}".format(start_cmd))
        if isinstance(start_cmd, str):
            start_cmd = start_cmd.strip().split()
        elif isinstance(start_cmd, list):
            return None
        try:
            # pid = Popen(["python", "/home/ubuntu/Watchdog/test/while.py"]).pid
            pid = Popen(start_cmd).pid
            LOG.debug("Process started successfully, pid: {}".format(pid))
        except Exception as e:
            LOG.exception(e)
            return None
        return pid

    def get_disk_usage(self, path):
        """
        Get disk used percentage of partition
        :param path: path
        :return: disk usage %
        """
        try:
            u = psutil.disk_usage(path)
            # available_per = Avail*100 / total
            free_percent = (u.free * 100) / u.free
            return 100 - free_percent
        except Exception as e:
            LOG.exception(e)
            return 0.0

    def free_space(self, path):
        """
        Delete oldest file in given path to free space
        :param path: path
        :return:
        """
        glob.glob('D:\\py_game\\upwork\\Watchdog\\' + '**\\', recursive=True)

    def watch_process(self, interval=1):
        LOG.info("Started")
        while True:
            for cmd, process in self.monitored_processes.values():
                # if process exists & running fine -> do nothing
                if process and process.is_running():
                    LOG.debug("Process {} is running.".format(cmd))
                    continue
                # else: create a new process
                pid = self.start_process(cmd)

                if pid:
                    # update process dict
                    self.update_process_dict()

            # sleep
            sleep(interval)


def main(args):
    global LOG
    load_config(args.ini)
    log = Logger(level=CONFIG)
    LOG = Logger.get_logger()
    LOG.info("============= Running Version {} =============".format(__version__))
    w = Watchdog()
    w.watch_process()
    LOG.info("============= Finished Version {} =============".format(__version__))
    log.stop()


if __name__ == '__main__':
    """
        Execution starts here.
    """

    parser = argparse.ArgumentParser(description='Watchdog Script')
    parser.add_argument('-i', '--ini', help='config filename', type=str, required=False, default='watchdog.ini')
    args = parser.parse_args()
    ensure_uniqness()
    try:
        main(args)
    except Exception as e:
        print(e)
    delete_pidfile()
