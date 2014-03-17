from unittest import TestCase
from pyemu import emulator, telnet
import telnetlib

class TestEmulator(TestCase):

    def get_emulator(self, f):
        with open(f, 'r') as x:
            return emulator.Emulator(x.read())

    def test_successfull(self):
        e = self.get_emulator('examples/foobar.txt')

        self.assertEqual(e.input(None), "PyEmu v0.1 Session\n\nThis is a test script\n\nEnter 'foo'\n> ")
        self.assertEqual(e.line, 4)
        self.assertEqual(e.input('foo'), "\nEnter 'bar'\n> ")
        self.assertEqual(e.line, 7)
        self.assertEqual(e.input('bar'), "\nBye!\n")
        self.assertEqual(e.line, 10)
        self.assertTrue(e.eof)
        self.assertIsNone(e.input('foo'))

    def test_unexpected_input(self):
        e = self.get_emulator('examples/foobar.txt')
        e.input(None)

        with self.assertRaisesRegexp(emulator.EmulationError, "Expected 'foo', got 'bar' at line 4"):
            e.input('bar')

        # emulation is closed
        self.assertTrue(e.eof)
        self.assertIsNone(e.input('foo'))

        # can restart
        e.start()
        e.input(None)
        self.assertEqual(e.input('foo'), "\nEnter 'bar'\n> ")

class TestTelnetEmulator(TestCase):

    def setUp(self):
        import time
        self.server = telnet.BackgroundEmulationServer(port=9023)
        self.server.start()
        time.sleep(0.01)  # allow servers to start

    def tearDown(self):
        self.assertTrue(self.server.stop())

    def test_background_server(self):
        pass

    def test_emulation(self):
        self.server.load_emulation('examples/foobar.txt')

        c = telnetlib.Telnet('localhost', 9023)
        self.assertEqual(c.read_until('> '), "PyEmu v0.1 Session\r\n\r\nThis is a test script\r\n\r\nEnter 'foo'\r\n> ")

        c.write("foo\r\n")
        self.assertEqual(c.read_until('> '), "\r\nEnter 'bar'\r\n> ")

        c.write("bar\r\n")
        self.assertEqual(c.read_all(), '\r\nBye!\r\n')

    def test_set_data(self):
        self.server.set_emulation('Enter "foo"\n> <%foo%>\nBye!\n')

        c = telnetlib.Telnet('localhost', 9023)
        self.assertEqual(c.read_until('> '), 'PyEmu v0.1 Session\r\n\r\nEnter "foo"\r\n> ')

        c.write("foo\r\n")
        self.assertEqual(c.read_all(), 'Bye!\r\n')
