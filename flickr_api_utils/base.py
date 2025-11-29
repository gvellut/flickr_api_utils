import logging
import sys

import click

logger = logging.getLogger(__name__)


class CatchAllExceptionsCommand(click.Command):
    def invoke(self, ctx):
        try:
            return super().invoke(ctx)
        except Exception as ex:
            raise UnrecoverableJNCEPError(str(ex), sys.exc_info()) from ex


class UnrecoverableJNCEPError(click.ClickException):
    def __init__(self, message, exc_info):
        super().__init__(message)
        self.exc_info = exc_info

    def show(self):
        out_log = logger.error
        if logger.isEnabledFor(logging.DEBUG):
            out_log = logger.exception
        logger.error("*** An unrecoverable error occured ***")
        out_log(self.message)
