PyEmu
=====

Python Emulator for testing line based protocols (telnet, ftp, etc...)

Follows script files.  Input is delimited by <% %> tags and is designed so you can
pretty much cut-and-paste a a session and mark up the input.

**examples/foobar.txt**:

```
	This is a test script

	Enter 'foo'
	> <%foo%>

	Enter 'bar'
	> <%bar%>

	Bye!
```
	
Usage::
```bash
	$ pyemu --help
	$ pyemu examples/foobar.txt --cli
	PyEmu v0.1 Session
	
	This is a test script
	
	Enter 'foo'
	> 
```

Telnet
------
Can run as a telnet server.

	> pyemu examples/foobar.txt -p 9023 &
	
	> telnet localhost 9023
	This is a test script
	
	Enter 'foo'
	> ^C
	
This also runs a control server on port 2323 which can be used to instruct the server to load
emulation files or shutdown.

Unittesting
-----------

Includes :telnet.BackgroundEmulationServer which can be used to unit test your clients.

```python
from unittest import TestCase
from pycart.telnet import BackgroundEmulationServer
import telnetlib

class MyTestCase(TestCase):

	def setUp(self):
		self.emulation = BackgroundEmulationServer(port=9023)
		
	def tearDown(self):
		self.emulation.stop()
		
	def test_emulation_server(self):
		self.server.set_emulation('Enter "foo"\n> <%foo%>\nBye!\n')
		
		c = telnetlib.Telnet('localhost', 9023)
		self.assertEqual(c.read_until('> '), 'PyEmu v0.1 Session\r\n\r\nEnter "foo"\r\n> ')
		
		c.write("foo\r\n")
		self.assertEqual(c.read_all(), 'Bye!\r\n')
```

Recorder
--------
Records telnet sessions for playback

```bash
	> pyemu-recorder myserver -f output/myserver_login.session
	User: bob
	Pass: ******
	> quit
	
	> pyemu output/myserver_login.session
	PyEmu v0.1 Session
	
	User: 
```
		
Docs
----
Minimal at present (this file) but source is easy to understand.
