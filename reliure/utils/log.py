#-*- coding:utf-8 -*-
""" :mod:`reliure.utils.log`
=========================

Helper function to setup a basic logger for a reliure app
"""

import logging
from time import time
from reliure.pipeline import Composable

# NullHandler is not defined in python < 2.6
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

def get_basic_logger(level=logging.WARN, scope='reliure'):
    """ return a basic logger that print on stdout msg from reliure lib
    """
    logger = logging.getLogger(scope)
    logger.setLevel(level)
    # create console handler with a higher log level
    ch = logging.StreamHandler()
    ch.setLevel(level)
    # create formatter and add it to the handlers
    formatter = ColorFormatter('%(asctime)s:%(levelname)s:%(name)s:%(message)s')
    ch.setFormatter(formatter)
    # add the handlers to the logger
    logger.addHandler(ch)   
    return logger


class ColorFormatter(logging.Formatter):
    BLACK, RED, GREEN, YELLOW, BLUE, MAGENTA, CYAN, WHITE = range(8)
    COLORS = {
        'WARNING'  : YELLOW,
        'INFO'     : WHITE,
        'DEBUG'    : BLUE,
        'CRITICAL' : YELLOW,
        'ERROR'    : RED,
        
        'RED'      : RED,
        'GREEN'    : GREEN,
        'YELLOW'   : YELLOW,
        'BLUE'     : BLUE,
        'MAGENTA'  : MAGENTA,
        'CYAN'     : CYAN,
        'WHITE'    : WHITE,
    }
    RESET_SEQ = "\033[0m"
    COLOR_SEQ = "\033[1;%dm"
    BOLD_SEQ  = "\033[1m"
    # Add a color formater for logging messagess

    def __init__(self, *args, **kwargs):
        # can't do super(...) here because Formatter is an old school class
        logging.Formatter.__init__(self, *args, **kwargs)

    def format(self, record):
        levelname = record.levelname
        color     = ColorFormatter.COLOR_SEQ % (30 + ColorFormatter.COLORS[levelname])
        message   = logging.Formatter.format(self, record)
        message   = message.replace("$RESET", ColorFormatter.RESET_SEQ)\
                           .replace("$BOLD",  ColorFormatter.BOLD_SEQ)\
                           .replace("$COLOR", color)
        for k,v in ColorFormatter.COLORS.items():
            message = message.replace("$" + k,    ColorFormatter.COLOR_SEQ % (v+30))\
                             .replace("$BG" + k,  ColorFormatter.COLOR_SEQ % (v+40))\
                             .replace("$BG-" + k, ColorFormatter.COLOR_SEQ % (v+40))
        return message + ColorFormatter.RESET_SEQ


def get_app_logger_color(appname, app_log_level=logging.INFO, log_level=logging.WARN, logfile=None):
    """ Configure the logging for an app using reliure (it log's both the app and reliure lib)

    :param appname: the name of the application to log
    :parap app_log_level: log level for the app
    :param log_level: log level for the reliure
    :param logfile: file that store the log, time rotating file (by day), no if None
    """
    # create lib handler
    stderr_handler = logging.StreamHandler()
    stderr_handler.setLevel(log_level)
    # create formatter and add it to the handlers
    name = "reliure"
    name += "_"*(max(0, len(appname)-len(name)))
    formatter = ColorFormatter('$BG-BLUE$WHITE%s$RESET:%%(asctime)s:$COLOR%%(levelname)s$RESET:$BOLD%%(name)s$RESET: %%(message)s' % name)
    stderr_handler.setFormatter(formatter)
    # get the logers it self
    logger = logging.getLogger("reliure")
    logger.setLevel(logging.DEBUG)
    # add the handlers to the loggers
    logger.addHandler(stderr_handler)
    
    # create app handler
    app_stderr_handler = logging.StreamHandler()
    app_stderr_handler.setLevel(app_log_level)
    # create formatter and add it to the handlers
    app_formatter = ColorFormatter("$BG-CYAN$WHITE%s$RESET:%%(asctime)s:$COLOR%%(levelname)s$RESET:$BOLD%%(name)s$RESET: %%(message)s" % appname.upper())
    app_stderr_handler.setFormatter(app_formatter)
    # get the logers it self
    app_logger = logging.getLogger(appname)
    app_logger.setLevel(logging.DEBUG)
    # add the handlers to the loggers
    app_logger.addHandler(app_stderr_handler)

    if logfile is not None:
        file_format = '%(asctime)s:%(levelname)s:%(name)s: %(message)s'
        from logging.handlers import TimedRotatingFileHandler
        file_handler = TimedRotatingFileHandler(logfile, when="D", interval=1, backupCount=7)
        file_handler.setFormatter(logging.Formatter(file_format))
        # add the handlers to the loggers
        logger.addHandler(file_handler)
        # add the handlers to the loggers
        app_logger.addHandler(file_handler)
    return app_logger


class SpeedLogger(Composable):
    """ Pipeline element that do *nothing* but log the procesing speed every K
    element and at the end.
    
    if you have a processing pipe, for example:
    
    >>> from reliure.pipeline import Composable
    >>> pipeline = Composable(lambda data: (x**3 for x in data))
    
    you can add a :class:`SpeedLogger` in it:
    
    >>> pipeline |= SpeedLogger(each=30000, elements="numbers")
    
    And then when you run your pipeline:
    
    >>> import logging
    >>> from reliure.utils.log import get_basic_logger
    >>> logger = get_basic_logger(logging.INFO)
    >>> from reliure.offline import run
    >>> results = run(pipeline, range(100000))
    
    You will get a logging like that::

        2014-09-26 15:19:56,139:INFO:reliure.SpeedLogger:Process 30000 numbers in 0.010 sec (2894886.12 numbers/sec)
        2014-09-26 15:19:56,148:INFO:reliure.SpeedLogger:Process 30000 numbers in 0.008 sec (3579572.14 numbers/sec)
        2014-09-26 15:19:56,156:INFO:reliure.SpeedLogger:Process 30000 numbers in 0.008 sec (3719343.80 numbers/sec)
        2014-09-26 15:19:56,159:INFO:reliure.SpeedLogger:Process 9997 numbers in 0.003 sec (3367096.85 numbers/sec)
        2014-09-26 15:19:56,159:INFO:reliure.SpeedLogger:In total: 100000 numbers proceded in 0.030 sec (3307106.53 numbers/sec)

    
    """
    def __init__(self, each=1000, elements="documents"):
        """ 
        :param each: log the speed every *each* element
        :param elements: name of the elements in the produced log lines
        """
        super(SpeedLogger, self).__init__()
        self.each = each
        self.elements = elements

    def __call__(self, inputs):
        count = 0
        ltop = time()
        tzero = ltop
        tcount = 0
        each = self.each
        info = "Process %d %s in %%1.3f sec (%%1.2f %s/sec)" % (each, self.elements, self.elements)
        logger = self._logger
        for element in inputs:
            count += 1
            yield element
            if count > each:
                dtime = time() - ltop
                speed = each / dtime
                logger.info(info % (dtime, speed))
                tcount += count
                count = 0
                ltop = time()
        dtime = time() - ltop
        speed = count / dtime
        tcount += count
        logger.info("Process %d %s in %1.3f sec (%1.2f %s/sec)" % (count, self.elements, dtime, speed, self.elements))
        if tcount > count:
            dtime_tot = time() - tzero
            speed_tot = tcount / dtime_tot
            logger.info("In total: %d %s proceded in %1.3f sec (%1.2f %s/sec)" % (tcount, self.elements, dtime_tot, speed_tot, self.elements))
