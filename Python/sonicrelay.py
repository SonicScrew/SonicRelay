#! /usr/bin/env python

import os
import sys
import platform
import glob
import subprocess
import smtplib
import re
import Tkinter

from ConfigParser import SafeConfigParser

from string import printable

class SonicRelayError(Exception):
  pass

class ConfigError(SonicRelayError):
  pass


class FakeSecHead(object):
  """
  Alex Martelli: http://stackoverflow.com/a/2819788
  """
  def __init__(self, fp):
    self.fp = fp
    self.sechead = '[asection]\n'
  def readline(self):
    if self.sechead:
      try: return self.sechead
      finally: self.sechead = None
    else: return self.fp.readline()



def _last_made_helper(dirpath, suffix):
  # get all entries in the directory w/ stats
  entries = [os.path.join(dirpath, fn) for fn in os.listdir(dirpath)]
  entries = [(os.stat(path), path) for path in entries]

  # leave only regular files, insert creation date
  entries = [(stat[ST_CTIME], path)
             for stat, path in entries if S_ISREG(stat[ST_MODE])]

  if suffix is not None:
    if isinstance(suffix, basestring):
      suffix = (suffix,)
    selected = []
    for sfx in suffix:
      es = [e for e in entries if e[1].endswith(sfx)]
      selected.extend(es)
    entries = selected

  entries.sort(reverse=True)

  if entries:
    result = entries[0]
  else:
    result = None

  return result

def last_made(dirpath='.', suffix=None, depth=0):
  """
  Returns the most recently created file in `dirpath`. If provided,
  the newest of the files with the given suffix/suffices is returned.
  This will recurse to `depth`, with `dirpath` being at depth 0 and
  its children directories being at depth 1, etc. Set `depth` to
  any value but 0 or a positive integer if recursion should be exauhstive
  (e.g. ``-1`` or ``None``).

  Returns ``None`` if no files are found that match `suffix`.

  The `suffix` parameter is either a single suffix
  (e.g. ``'.txt'``) or a sequence of suffices
  (e.g. ``['.txt', '.text']``).
  """
  result = None
  i = 0
  for (apath, dirs, files) in os.walk(dirpath):
    newest = _last_made_helper(apath, suffix)
    if ((newest is not None) and
        ((result is None) or (newest[0] > result[0]))):
      result = newest
    if (i == depth):
      break
    else:
       i += 1
  return result[1]



def get_home_dir():
    """
    Returns the home directory of the account under which
    the python program is executed. The home directory
    is represented in a manner that is comprehensible
    by the host operating system (e.g. ``C:\\something\\``
    for Windows, etc.).
    
    Adapted directly from K. S. Sreeram's approach, message
    393819 on c.l.python (7/18/2006). I treat this code
    as public domain.
    """
    def valid(path) :
        if path and os.path.isdir(path) :
            return True
        return False
    def env(name) :
        return os.environ.get( name, '' )
    if sys.platform != 'win32' :
      homeDir = os.path.expanduser( '~' )
      if valid(homeDir):
        return homeDir
    homeDir = env( 'USERPROFILE' )
    if valid(homeDir) :
      return homeDir
    homeDir = env( 'HOME' )
    if valid(homeDir) :
      return homeDir   
    homeDir = '%s%s' % (env('HOMEDRIVE'),env('HOMEPATH'))
    if valid(homeDir) :
      return homeDir
    homeDir = env( 'SYSTEMDRIVE' )
    if homeDir and (not homeDir.endswith('\\')) :
      homeDir += '\\'
      if valid(homeDir) :
        return homeDir
    homeDir = 'C:\\'
    return homeDir


def read_config(config_file):
  """
  Returns the contents of a sectionless `config_file` as a `dict`.
  """
  cp = SafeConfigParser()
  cp.readfp(FakeSecHead(open(config_file)))
  return dict(cp.items('asection'))

def get_profiles(home):
  profiles = None
  if sys.platform == "darwin":
    profiles = os.path.join(home, "Library",
                                  "Thunderbird",
                                  "Profiles") 
  elif sys.platform.startswith("linux"):
    profiles = os.path.join(home, ".thunderbird")
  elif sys.platform == "win32":
    v = int(platform.version().split('.', 1)[0])
    if platform.release in (4, 5):
      profiles = os.path.join(home, "Application Data",
                                    "Thunderbird",
                                    "Profiles")
    elif platform.release >= 6:
      profiles = os.path.join(home, "AppData", "Roaming",
                                               "Thunderbird",
                                               "Profiles")
  return profiles

def main():
  home = get_home_dir()
  config_file = os.path.join(home, ".sonicrelay")
  if os.path.exists(config_file):
    config = read_config(config_file)
  else:
    raise ConfigError("Unable to find '%s' config." % config_file)
  if "sonicrelay" in config:
    sonicrelay = config['.sonicrelay']
  else:
    sonicrelay = os.path.join(home, ".sonicrelay")
  debug = config.get("debug", False)
  if debug:
    tk = Tkinter.Tk()
    tk.title("SonicRelay")
    txt = Tkinter.Text(tk)
    txt.pack(expand=Tkinter.YES, fill=Tkinter.BOTH)
  sonicoind = config['daemon']
  f5 = config.get("f5", "f5.jar")
  text = config.get("text", "text.txt")
  java = config.get("java", "java")
  steg_key = config.get("steg_key", "abcdefg123")
  os.chdir(sonicrelay)
  jpeg = last_made(dirpath='.', suffix='.jpg', depth=0)

  java_cmd = [java, '-jar', f5, 'x', '-p', steg_key,
              '-e', text, jpeg]
  output = subprocess.check_output(java_cmd)
  if debug:
    txt.insert(Tkinter.END, output.strip() + "\n\n")

  msg = open(text).read().strip()

  if debug:
    txt.insert(Tkinter.END, msg + "\n\n")

  command = [soniccoind, "decryptsend", "%s" % (msg,)]
  # print "command is:"
  # print command
  output = subprocess.check_output(command)
  if debug:
    txt.insert(Tkinter.END, "\n\n" + output.strip())
  # output = "test\n"
  sys.stderr.write(output)
  if "confirm_address" in config:
    if output.startswith('<<'):
      message = config.get("fail", "-") + "\n"
    else:
      message = config.get("success", "+") + "\n"
    if "sender" in config:
      sender = config['sender']
    else:
      raise ConfigError("Setting 'email' not in config.")
    if "confirm_address" in config:
      receivers = [config['confirm_address']]
    else:
      raise ConfigError("Setting 'confirm_address' not in config.")
  else:
    message = "<No Message>"
    sender = "<No Sender>"
    receivers = []
  if "confirm_address" in config:
    try:
      server = smtplib.SMTP(config['server'])
      server.starttls()
      server.login(config['username'], config['password'])
      server.sendmail(sender, receivers, message)
      if debug:
        txt.insert(Tkinter.END, "\n\n" + "Email sent successfully.")
      else:
        sys.stderr.write("Email sent successfully.\n")
    except smtplib.SMTPException:
      if debug:
        txt.insert(Tkinter.END, "\n\n" + "Email unsuccessful.")
      else:
        sys.stderr.write("Email unsuccessful.\n")

  os.remove('text.txt')
  os.remove(jpeg)

  if debug:
    tk.mainloop()
    

if __name__ == "__main__":
  main()
