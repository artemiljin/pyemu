from distutils.core import setup

setup(name='PyEmu',
      version='0.1',
      description='Emulator for testing line based protocols (Telnet, FTP, HTTP etc)',
      author='Tris Forster',
      author_email='tris@tfconsulting.com.au',
      packages=['pyemu'],
      scripts=['scripts/pyemu', 'scripts/pyemu-recorder'])