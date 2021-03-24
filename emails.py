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
import datetime
import socket
from requests import get
from getpass import getpass, getuser

from exec import FalseSSH
from ip import SendIP
from utils import *
from task import MailTask

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
			self, self.mail_addr, get_password(key, 'MAIL_KEY')['password'])
		self.do_tobe = MailTask(self)


	def send_mail(self, body, subject="", to_addr=None, from_addr=None, reply=None):
		if from_addr == None:
			from_addr = self.mail_addr
		if to_addr == None:
			to_addr = self.mail_addr

		message = MIMEMultipart()

		if reply != None:
			subject = "ACK: " + reply['Subject']

		message["Message-ID"] = email.utils.make_msgid()
		message["Subject"] = subject
		message["From"] = from_addr
		message["To"] = to_addr

		part1 = MIMEText(body, "plain")
		message.attach(part1)
		
		ret = self.server.sendmail(from_addr, to_addr, message.as_string())

		print(YELLOW + "** Sending mail!" + RESET)
		self.print_one_mail(message)

	def fetch_mail(self, folder="inbox", search="ALL"):
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
		pattern = r"([A-Za-z0-9\.]+)(\+[A-Za-z0-9\.]+)?(@[A-Za-z0-9\.]+)"
		a = re.search(pattern, mail['From'])
		if a == None:
			print("\tFILTER: Mail from is not an email")
			return False
		email = a.group(1) + a.group(3)
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

		self.print_one_mail(mail, False)
		if self.do_tobe.is_for_me(mail):
			self.do_tobe.do_action(mail)
		if self.do_ip.is_for_me(mail):
			self.do_ip.do_routine()
		if self.do_exec.is_for_me(mail):
			self.do_exec.do_action(mail)
		self.tasks_done[mail["Message-ID"]] = True


	def init_box(self):
		self.do_tobe.ask_action(make_email_address(self.login_adrr, 'all'))
		self.mails = self.fetch_mail()
		self.do_cleaning()
		init = False
		end_index = 0
		for id in range(0, len(self.mails)):
			if self.filter(self.mails[id]):
				if "INIT" in self.mails[id]['subject']:
					identifier = self.get_payload(self.mails[id])[0]
					if identifier == self.identifier:
						init = True
						end_index = id
					self.workers.append(identifier)
		if not init:
			self.send_mail(self.identifier, "INIT", to_addr=make_email_address(self.login_adrr , "all"))
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
		return end_index + 1

	def do_cleaning(self):
		move_to_trash_before_date(self.inbox, "noreply@google.com")
		move_to_trash_before_date(self.inbox, "no-reply@accounts.google.com")
		move_to_trash_before_date(self.inbox, "gmail-noreply@google.com")

	def do_routine(self):
		last_mail = None
		end = self.init_box()
		last_len = len(self.mails)
		print("Init end: ", end)
		while True:
			print("~" * 40)
			print("NEW CYCLE")
			print("~" * 40)
			if last_len < len(self.mails):
				self.do_cleaning()
			last_len = len(self.mails)
			print("End: ", end)
			for id in range(0, len(self.mails)):
				print(f"{id}: {self.mails[id]['Subject']}")
				# if end == 0:
				# 	break
				if self.filter(self.mails[id]):
					self.do_tasks(self.mails[id])
				last_mail = id + 1
			end = last_mail
			self.mails = self.fetch_mail()

	def get_payload(self, msg):
		if msg.is_multipart():
				pay = [part.get_payload() for part in msg.get_payload()]
		else:
			pay = [msg.get_payload()]
		return pay





	def print_one_mail(self, msg, body=True):
		print("\tto:      " + GREEN + str(msg['to']) + RESET)
		print("\tfrom:    " + str(msg['from']))
		print('\tID:      ' + str(msg["Message-ID"]))
		print("\tSubject: " + BLUE + str(msg['subject']) + RESET)
		if body:
			print("\tBody:    " + GREEN + self.get_payload(msg)[0] + RESET)
		print()

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



def move_to_trash_before_date(m, from_addr, folder='INBOX', days_before=2):
	# required to perform search, m.list() for all lables, '[Gmail]/Sent Mail'
	no_of_msgs = int(m.select(folder)[1][0])
	# print(
	# 	"- Found a total of {1} messages in '{0}'.".format(folder, no_of_msgs))

	before_date = (datetime.date.today() - datetime.timedelta(days_before)
				   ).strftime("%d-%b-%Y")  # date string, 04-Jan-2013
	# search pointer for msgs before before_date
	typ, data = m.search(None, '(BEFORE {0})'.format(before_date))
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
