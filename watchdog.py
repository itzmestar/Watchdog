#!/usr/bin/python3
import logging
from logging.handlers import TimedRotatingFileHandler
import queue
import os

# Version Info #
__version__ = "v0.0.1"


LOG = None


class Logger:
    logger = logging.getLogger(__name__)

    def __init__(self, level='INFO', logfile_backup=5):
        #logger = logging.getLogger(__name__)
        self.listener = None
        self.logfile_backup = logfile_backup
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
            os.path.splitext(os.path.basename(__file__))[0]+'.log'
        )
        Logger.logger.setLevel(self.level)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(log_formatter)
        console_handler.setLevel(self.level)
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


class Watchdog:
    """
    Watchdog class
    """
    pass


def main():
    global LOG
    log = Logger()
    LOG = Logger.get_logger()
    LOG.info(f"Running Version: {__version__}")


    LOG.info(f"Finished Version: {__version__}")
    log.stop()


if __name__ == '__main__':
    main()


