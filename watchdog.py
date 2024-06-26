#!/usr/bin/python3
import glob
import logging
import signal
import sys
from logging.handlers import TimedRotatingFileHandler
import queue
import os
from subprocess import Popen
import argparse
import psutil
import configparser
from time import sleep
from pprint import pformat
import concurrent.futures
# ---------- Version Info ----------#
__version__ = "v1.0.0"

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


def ensure_uniqness(pid_file="./.watchdog.pid"):
    """
    Ensure only 1 instance of script run at a time
    """
    pid = str(os.getpid())
    if os.path.exists(pid_file):
        print("{} already exists, exiting".format(pid_file))
        exit(0)
    with open(pid_file, 'w') as f:
        f.write(pid)


def delete_pidfile(pid_file="./.watchdog.pid"):
    """
    Delete pid file if exists
    :param pid_file: filename with path
    :return:
    """
    if os.path.exists(pid_file):
        os.unlink(pid_file)


def terminate_process(signalNumber, frame):
    LOG.warning('({}) terminating the process'.format(signalNumber))
    delete_pidfile()
    logging.shutdown()
    sys.exit()


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

    def terminate_process(self):
        pass

    def start(self):
        if self.listener:
            self.listener.start()

    def stop(self):
        if self.listener:
            self.listener.stop()
        logging.shutdown(handlerList=Logger.logger.handlers)

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

        file_handler = TimedRotatingFileHandler(logging_file, when='d', interval=1,
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


# LOG = logging.getLogger(__name__)


class Watchdog:
    """
    Watchdog class
    """

    def __init__(self, config_file):
        LOG.info("Initializing Watchdog...")
        self.config_file = config_file
        self.monitored_processes = dict()
        self.monitored_process_cmd = None
        self.started_processes = list()
        self.watchdog_interval = 1
        self.disk_interval = 60
        self.monitored_partitions = list()
        self.usage_threshold = 90
        self.delete_file_paths = list()


    @staticmethod
    def get_process_dict(startswith='python'):
        filtered_processes = {p.pid: p for p in psutil.process_iter(['name', 'username', 'cmdline', 'create_time'])
                              if p.info.get('name').startswith(startswith)}
        return filtered_processes

    def read_watchdog_config(self):
        LOG.info("Reading any watchdog configuration changes...")
        CONFIG.read(self.config_file)
        self.watchdog_interval = CONFIG.getfloat('Watchdog', 'interval', fallback=1)
        self.monitored_process_cmd = [' '.join(x.strip().split()) for x in
                                      CONFIG.get('Watchdog', 'programs', fallback=[]).split(',')]

    def update_process_dict(self):
        LOG.info("Started")
        self.read_watchdog_config()

        current_filtered_processes = self.get_process_dict()
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
        LOG.debug(self.monitored_process_cmd)
        # commands for which no process exists
        for cmdline in self.monitored_process_cmd:
            self.monitored_processes[cmdline] = None
        LOG.debug(pformat(self.monitored_processes))

    def start_process(self, start_cmd):
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
            process = Popen(start_cmd)
            self.started_processes.append(process)
            LOG.debug("Process started successfully, pid: {}".format(process.pid))
        except Exception as e:
            LOG.error("Process failed to start, cmd: {}".format(start_cmd))
            LOG.exception(e)
            return None
        return process.pid

    def watch_process(self):
        LOG.debug("Started")
        self.update_process_dict()
        # LOG.debug(self.monitored_processes)
        while True:
            for process in self.started_processes:
                if process.poll():
                    self.started_processes.remove(process)

            # LOG.debug(self.monitored_processes.values())
            for cmd, process in self.monitored_processes.items():
                # if process exists & running fine -> do nothing
                if process and process.is_running():
                    LOG.info("Process {} is running.".format(cmd))
                    continue
                # else: create a new process
                pid = self.start_process(cmd)

                if pid: pass
            # update process dict
            self.update_process_dict()

            # sleep
            sleep(self.watchdog_interval)

    @staticmethod
    def get_disk_usage(path):
        """
        Get disk used percentage of partition
        :param path: path
        :return: disk usage %
        """
        try:
            u = psutil.disk_usage(path)
            # available_per = Avail*100 / total
            free_percent = (u.free / u.total) * 100.0
            return 100.0 - free_percent
        except Exception as e:
            LOG.exception(e)
            return 0.0

    def get_all_files(self):
        """
        Get the list of all files sorted by modification time
        :param paths: list of path
        :return: list of files
        """
        LOG.debug("Started")

        files = list()
        for path in self.delete_file_paths:
            files += glob.glob(path + '/**/*', recursive=True)

        # filter out directories
        files = [x for x in files if os.path.isfile(x)]

        # sort files based on modify time
        files.sort(key=os.path.getmtime)

        return files

    def free_space(self, partition):
        """
        Delete oldest file in given path to free space
        :param partition:
        :return:
        """
        files = self.get_all_files()
        if len(files) == 0:
            LOG.warning("No files in delete list. Can't delete any file.")
            return
        for file in files:
            try:
                os.unlink(file)
                LOG.info("Deleted file {}".format(file))
            except Exception as e:
                LOG.exception(e)
            usage = self.get_disk_usage(path=partition)
            if usage < self.usage_threshold:
                LOG.info("Disk usage for {} is {} < threshold {}.".format(partition, usage, self.usage_threshold))
                return

    def read_disk_config(self):
        LOG.debug("Reading any disk configuration changes...")
        CONFIG.read(self.config_file)
        self.disk_interval = CONFIG.getfloat('Disk', 'interval', fallback=60)
        self.monitored_partitions = [' '.join(x.strip().split()) for x in
                                     CONFIG.get('Disk', 'partitions', fallback=[]).split(',')]
        self.usage_threshold = CONFIG.getfloat('Disk', 'usage_threshold', fallback=90)
        self.delete_file_paths = [' '.join(x.strip().split()) for x in
                                  CONFIG.get('Disk', 'delete_file_paths', fallback=[]).split(',')]

    def watch_disk_usage(self):
        LOG.debug("Started")
        while True:
            # Read all configurations
            self.read_disk_config()
            # monitor all partitions
            for partition in self.monitored_partitions:
                # get disk usage for partition
                usage = self.get_disk_usage(path=partition)
                if usage < self.usage_threshold:
                    LOG.debug("Disk usage for {} is {} < threshold {}.".format(partition, usage, self.usage_threshold))
                    continue
                LOG.warning("Disk usage for {} is {} >= threshold {}.".format(partition, usage, self.usage_threshold))
                self.free_space(partition)
            sleep(self.disk_interval)

    def workflow(self):
        result_list = list()
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
            result = executor.submit(self.watch_process)
            result_list.append(result)
            result = executor.submit(self.watch_disk_usage)
            result_list.append(result)


def main(args):
    global LOG
    load_config(args.ini)
    log = Logger(level=CONFIG.get('Logging', 'level', fallback='INFO'),
                 console=CONFIG.getboolean('Logging', 'console_log', fallback=False),
                 logfile_backup=CONFIG.getint('Logging', 'backup', fallback=5)
                 )
    LOG = Logger.get_logger()
    LOG.info("============= Running Version {} =============".format(__version__))
    w = Watchdog(args.ini)
    w.workflow()
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
    signal.signal(signal.SIGTERM, terminate_process)
    signal.signal(signal.SIGINT, terminate_process)
    try:
        main(args)
    except Exception as e:
        print(e)
    delete_pidfile()
