'''
A script driven CLI emulator for testing clients.

Allows you to test your client interactions either over command line
or telnet-type interface.  Sends the contents of the script file until
it encounters an input tag like <%configure%>, at which point it waits
for the client to enter 'configure\n' before continuing.

You can pretty much copy and paste console output from a live session
and then mark your input with <% %> tags.

Usage::

    python emulator.py <script>

Example script::

    (FSM7328S)
    User:<%admin%>
    Password:<%secret%>
    (FSM7328S) ><%show hardware%>
    
    Switch: 1
    
    System Description............................. FSM7328S 24+4 L3 Stackable
                                                    Switch
    Machine Model.................................. FSM7328S
    Serial Number.................................. 1234567890
    Burned In MAC Address.......................... XX:XX:XX:XX:XX:XX
    Software Version............................... 7.3.1.7
    Bootcode Version............................... 1.5
    Current Time................................... Jan  3 06:43:29 2000 UTC
    Current SNTP Sync Status....................... Request Timed Out
    
    (FSM7328S) ><%logout%>

'''
import sys, re, logging

logger = logging.getLogger(__name__)

GREETING = 'PyEmu v0.1 Session\n\n'
INPUT_TAG = '<%(.*?)?%>\n'

class Emulator(object):
    '''
    Encapsulates the script and keeps track of where the emulation is up to.
    '''
    def __init__(self, data, options={}):

        self.greeting = options.get('greeting', GREETING)
        self.data = self.greeting + data
        self.tag = re.compile(options.get('input_tag', INPUT_TAG))
        self.start()

    def start(self):
        '''
        Resets the emulation to the start.
        '''
        self.offset = 0
        self.line = -self.greeting.count('\n')
        self.expected = None
        self.running = True

    def input(self, cmd):
        '''
        Run the command and return everything up to the next input tag.
        Throws an exception if the command is not what was expected.
        '''
        if not self.running:
            return None

        # check they entered what we expected
        if self.expected is not None and cmd != self.expected:
            # try a regexp
            match = re.match(self.expected, cmd)
            if match is None:
                self.running = False
                raise EmulationError("Expected {0}, got {1} at line {2}".format(repr(self.expected), repr(cmd), self.line))

        # find the next data tag
        match = self.tag.search(self.data, self.offset)
        if match:
            self.expected = match.group(1)
            return self._chunk(match.start(0), match.end(0))
            # result = self.data[self.offset:match.start(1) - 2]
            # self.offset = match.end(1) + 3
            # self.line += result.count('\n') + 1
            # return result
        else:
            logger.debug("At end of script")
            self.running = False
            return self._chunk(None, None)
            # return self.data[self.offset:]

    def _chunk(self, tag_start, tag_end):
        result = self.data[self.offset:tag_start]
        self.offset = tag_end
        self.line += result.count('\n') + 1
        return result

    @property
    def eof(self):
        return not self.running

class EmulationError(Exception):
    pass

def run_command_line(data):
    '''
    Run the emulation using stdin/stdout instead of a telnet session.
    Will exit 
    '''
    e = Emulator(data)

    e.start()
    sys.stdout.write(e.input(None))
    while True:
        cmd = sys.stdin.readline().rstrip()

        data = e.input(cmd)
        if data is None: break

        sys.stdout.write(data)
        if e.eof: break
