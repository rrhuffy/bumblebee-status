# pylint: disable=C0111,R0903,W1401

r""" Execute command in shell and print result

Few command examples:
    'ping -c 1 1.1.1.1 | grep -Po '(?<=time=)\d+(\.\d+)? ms''
    'echo 'BTC=$(curl -s rate.sx/1BTC | grep -Po \'^\d+\')USD''
    'curl -s https://wttr.in/London?format=%l+%t+%h+%w'
    'pip3 freeze | wc -l'
    'any_custom_script.sh | grep arguments'

Parameters:
    * shell.command:  Command to execute
      Use single parentheses if evaluating anything inside (sh-style)
      For example shell.command='echo $(date +'%H:%M:%S')'
      But NOT shell.command='echo $(date +'%H:%M:%S')'
      Second one will be evaluated only once at startup
    * shell.interval: Update interval in seconds
      (defaults to 1s == every bumblebee-status update)
    * shell.async:    Run update in async mode. Won't run next thread if
      previous one didn't finished yet. Useful for long
      running scripts to avoid bumblebee-status freezes
      (defaults to False)

contributed by `rrhuffy <https://github.com/rrhuffy>`_ - many thanks!
"""

import os
import subprocess
import threading

import core.module
import core.widget
import core.input
import util.format
import util.cli


class Module(core.module.Module):
    def __init__(self, config, theme):
        super().__init__(config, theme, core.widget.Widget(self.get_output))

        self.__command = self.parameter("command", 'echo "no command configured"')
        self.__async = util.format.asbool(self.parameter("async"))
        self.__status = 0

        if self.__async:
            self.__output = "please wait..."
            self.__current_thread = threading.Thread()

        if self.parameter("scrolling.makewide") is None:
            self.set("scrolling.makewide", False)

    def set_output(self, value):
        self.__output = value

    @core.decorators.scrollable
    def get_output(self, _):
        if self.__status == 0:
            return self.__output.replace('\033[0;33m', '').replace('\033[0;31m', '')
        else:
            return str(self.__status)

    def update(self):
        # if requested then run not async version and just execute command in this thread
        if not self.__async:
            self.__status, self.__output = util.cli.execute(self.__command, shell=True, ignore_errors=True,
                                                            return_exitcode=True)
            self.__output = self.__output.strip()
            return

        # if previous thread didn't end yet then don't do anything
        if self.__current_thread.is_alive():
            return

        # spawn new thread to execute command and pass callback method to get output from it
        def thread_command(thread_self):
            thread_self.__status, thread_self.__output = util.cli.execute(thread_self.__command, shell=True,
                                                                          ignore_errors=True,
                                                                          return_exitcode=True)
            thread_self.__output = thread_self.__output.strip()

        self.__current_thread = threading.Thread(
            target=thread_command, args=(self,),
        )
        self.__current_thread.start()

    def state(self, _):
        if self.__output == "no command configured":
            return "warning"
        if self.__output.startswith("\033[0;33m"):
            return "warning"  # for yellow
        if self.__output.startswith("\033[0;31m"):
            return 'critical'  # for red
        if self.__status > 0:
            return "critical"
        return ""

# vim: tabstop=4 expandtab shiftwidth=4 softtabstop=4
