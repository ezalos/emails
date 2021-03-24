import socket
from getpass import getpass, getuser
import re


def make_email_identifier():
	identifier = socket.gethostname() + "." + getuser()
	identifier = re.sub(r"[^A-Za-z0-9\.]", ".", identifier)
	if identifier[-1] == ".":
		identifier = identifier + 'x'
	return identifier

def get_email_identifier(address):
	if address and '@' in address:
		pattern = r"([A-Za-z0-9\.]+)(\+([A-Za-z0-9\.]+))?(@[A-Za-z0-9\.]+)"
		a = re.search(pattern, address)
		if a == None:
			return False
		return a.group(3)
	else:
		print("ERROR: No @ in adress ", address)
		return None

def make_email_address(login, identifier=None):
	my_addr = login
	if identifier == None:
		identifier = make_email_identifier()
	tab = my_addr.split('@')
	my_addr = tab[0] + "+" + identifier + '@' + tab[1]
	print("MY ADDRESS: " + my_addr)
	return my_addr
