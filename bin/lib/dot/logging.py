from __future__ import absolute_import

import logging
from termcolor import colored


# DEBUG = 10
VERBOSE = logging.DEBUG+1
# INFO = 20
LINK = logging.INFO + 1
MKDIR = logging.INFO + 2
RM = logging.INFO + 3


class Formatter(logging.Formatter):
    def format(self, record, *args, **kwargs):
        s = super(Formatter, self).format(record, *args, **kwargs)
        if getattr(record, 'color', None):
            level, message = s.split('\t', 1)
            s = '\t'.join((colored(level, record.color), message))
        return s


def init_logging(verbose=False):
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level)
    
    logger = logging.getLogger(None)
    logger.handlers[0].formatter = Formatter('%(levelname)s\t%(message)s')

    logging.addLevelName(VERBOSE, 'INFO')
    logging.addLevelName(LINK, 'LINK')
    logging.addLevelName(MKDIR, 'MKDIR')
    logging.addLevelName(RM, 'RM')


def _create_logger(level, color):
    def inner(message):
        logging.log(level, message, extra=dict(color=color))
    return inner


# Additional output, like if the link is already exists and no action was made
log_verbose = _create_logger(VERBOSE, 'green')

# All destructive operations are in magenta
log_link = _create_logger(LINK, 'magenta')
log_mkdir = _create_logger(MKDIR, 'magenta')
log_rm = _create_logger(RM, 'magenta')

# errors are red
log_error = _create_logger(logging.ERROR, 'red')
