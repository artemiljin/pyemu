from pyemu.emulator import Emulator, EmulationError

import asyncore, asynchat, socket
import shlex, threading

import logging
logger = logging.getLogger(__name__)

EOL = '\r\n'

class LineBasedHandler(asynchat.async_chat):
    '''
    Basic line based async handler.
    Subclasses should implement :handle_line()
    '''

    DEBUG = False

    def __init__(self, *args, **kwargs):
        asynchat.async_chat.__init__(self, *args, **kwargs)
        self.buffer = []
        self.set_terminator(EOL)
        logger.debug("Ready")

    def collect_incoming_data(self, data):
        if self.DEBUG: logger.debug("collect_incoming_data")
        self.buffer.append(data)

    def found_terminator(self):
        if self.DEBUG: logger.debug('found_terminator')
        data = ''.join(self.buffer).rstrip()
        self.buffer = []

        self.handle_line(data)

    def handle_line(self):
        raise NotImplementedError()

    def handle_close(self):
        asynchat.async_chat.handle_close(self)
        logger.debug("Connection closed")

class CommandHandler(LineBasedHandler):
    '''
    Command handler for emulation server.
    
    LOAD <file>: Load a simulation into the emulator
    SET <data>:  Sets the emulation data (must be quoted)
    QUIT:        Quit command server
    SHUTDOWN:    Shutdown all servers
    HELP:        This help
    '''
    prompt = EOL + "> "

    def __init__(self, sock, emulation_server, *args, **kwargs):
        LineBasedHandler.__init__(self, sock, *args, **kwargs)
        self.emulation_server = emulation_server
        self.send(self.prompt)

    def handle_line(self, line):
        parts = shlex.split(line)
        cmd = parts[0].upper()

        if cmd == "LOAD":
            try:
                f = parts[1]
                self.send("Loading '{0}'".format(f) + EOL)
                with open(f, 'r') as bob:
                    data = bob.read()
                self.emulation_server.set_emulation(data)
                self.send("Loaded file" + EOL)
            except (IOError, IndexError):
                self.send("Failed to load file" + EOL)
            return self.send(self.prompt)

        if cmd == "SET":
            try:
                self.emulation_server.set_emulation(parts[1])
                self.send("Set emulation data")
            except IndexError:
                self.send("Failed to set data")
            return self.send(self.prompt)

        if cmd == "QUIT":
            self.send("Closing connection..." + EOL)
            self.close()

        if cmd == 'SHUTDOWN':
            self.send("Sending shutdown signal..." + EOL)
            raise asyncore.ExitNow

        if cmd == 'HELP':
            self.send(self.__doc__)
            return self.send(self.prompt)

        self.send("Unknown command: {0}{1}".format(cmd, EOL))
        self.send(self.prompt)

class EmulatorTelnetHandler(LineBasedHandler):
    '''
    Handler for telnet connections using an Emulator instance.
    '''
    def __init__(self, sock, emulator, **kwargs):
        logger.debug("ONE")
        LineBasedHandler.__init__(self, sock, **kwargs)

        self.emulator = emulator
        self.emulator.start()
        self.handle_line(None)

    def handle_line(self, line):
        try:
            result = self.emulator.input(line)
            if not result is None:
                result = result.replace('\n', EOL)
                self.send(result)
                if self.emulator.eof:
                    self.close()
            else:
                self.close()
        except (EmulationError, IOError), e:
            logger.exception("Error while running emulation")
            self.send("Error: {0}\r\n".format(e))
            self.close()

class TCPServer(asyncore.dispatcher):
    '''
    A generic async TCP Server.
    Subclasses should implement the create_handler(sock) method.
    '''

    def __init__(self, host, port, max_connections=5):
        asyncore.dispatcher.__init__(self)

        self.create_socket(socket.AF_INET, socket.SOCK_STREAM)
        self.set_reuse_addr()
        self.bind((host, port))
        self.listen(max_connections)

        logger.info("Listening for connections on port {0}".format(port))

    def handle_accept(self):
        pair = self.accept()

        if pair is not None:
            sock, addr = pair
            logger.info("Accepting connection from {0}".format(addr))
            _handler = self.create_handler(sock)

    def create_handler(self):
        raise NotImplementedError()

    def handle_close(self):
        asyncore.dispatcher.handle_close(self)
        logger.info("Closing server {0}".format(self))

class EmulatorTelnetServer(TCPServer):
    '''
    Async server for spawning emulation handlers.
    '''
    data = None

    def set_emulation(self, data):
        self.data = data

    def create_handler(self, sock):
        if self.data is None:
            raise RuntimeError("Emulation not set")

        emulator = Emulator(self.data)
        return EmulatorTelnetHandler(sock, emulator)

class CommandServer(TCPServer):
    '''
    Async server for spawning control handlers.
    '''
    server = None

    def set_emulation_server(self, server):
        self.server = server

    def create_handler(self, sock):
        return CommandHandler(sock, self.server)

def run_telnet_server(data, port=23, command_port=2323):
    '''
    Create a telnet server and enter the listening loop
    '''
    emulation_server = EmulatorTelnetServer('', port)
    emulation_server.set_emulation(data)

    # create a command server as well
    command_server = CommandServer('', command_port)
    command_server.set_emulation_server(emulation_server)

    try:
        asyncore.loop()
    except (KeyboardInterrupt, asyncore.ExitNow):
        logger.info("Closing servers")
    emulation_server.close()
    command_server.close()

class BackgroundEmulationServer(threading.Thread):

    def __init__(self, port=23, command_port=2323, *args, **kwargs):
        threading.Thread.__init__(self, *args, **kwargs)
        self.port = port
        self.command_port = command_port
        self.daemon = True

    def run(self):
        run_telnet_server(None, self.port, self.command_port)

    def _send_command(self, cmd):
        from telnetlib import Telnet
        c = Telnet('localhost', self.command_port)
        c.read_until('> ')
        c.write(cmd + EOL)
        c.close()

    def stop(self):
        # open a connection and send the .quit command
        self._send_command('SHUTDOWN')
        logger.debug("Waiting for servers to shutdown")
        self.join(10)
        if self.is_alive():
            logger.warning("Failed to shutdown servers cleanly")
        return not self.is_alive()

    def load_emulation(self, f):
        self._send_command('LOAD "{0}"'.format(f))

    def set_emulation(self, s):
        self._send_command('SET "{0}"'.format(s.replace('"', '\\"')))
