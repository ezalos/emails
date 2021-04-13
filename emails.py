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

# Signal ALARM: https://stackoverflow.com/questions/492519/timeout-on-a-function-call
import signal

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
		self.workers = {}
		self.tasks_done = {}
		self.key = get_password(key, 1)['password']
		self.white_list = white_list
		self.identifier = make_email_identifier()
		self.login_adrr = login['user']
		self.safebox = login
		self.mail_addr = make_email_address(login['user'], self.identifier)
		self.idle_time = 5
		# self.tasks = {}
		print('Identifier: ' + self.identifier)
		print('Mail: ' + self.mail_addr)
		self.do_ip = SendIP(self, self.identifier)
		self.do_exec = FalseSSH(
			self, self.mail_addr, self.key)
		self.do_tobe = MailTask(self)
		self.do_update = SelfUpdate(self)

		# Register an handler for the timeout
		def handler(signum, frame):
			print("Forever is over!")
			raise Exception("end of time")
		# Register the signal function handler
		signal.signal(signal.SIGALRM, handler)

	def reconnect(self):
		# ret = self.server.quit()
		# print(f"server.quit(): {ret}")
		port = 465  # For SSL
		context = ssl.create_default_context()
		print(f"ssl.create_default_context(): {context}")

		with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
			print(f"smtplib.SMTP_SSL: {server}")
			print("Attempting to connect...")
			self.server = server
			ret = self.server.login(login["user"], login["password"])
			print(f"server.login(): {ret}")

			print("SMTP connected for sending mails!")
			self.inbox = imaplib.IMAP4_SSL("imap.gmail.com")
			print(f"imaplib.IMAP4_SSL(): {self.inbox}")
			ret = self.inbox.login(login["user"], login["password"])
			print("IMAP connected for receiving mails!")
			print(f"inbox.login(): {ret}")
			# raise SMTPServerDisconnected('please run connect() first')
			# smtplib.SMTPServerDisconnected: please run connect() first


	def send_mail(self, body, subject="", to_addr=None, from_addr=None, reply=None):
		if from_addr == None:
			from_addr = self.mail_addr
		if to_addr == None:
			to_addr = self.mail_addr

		message = MIMEMultipart()

		if reply != None:
			now = datetime.now()
			current_time = now.strftime("%H:%M:%S - %d/%m/%Y")
			subject = "ACK: " + reply['Subject'] + " - " + \
				current_time + " -> " + "{[(" + reply["Message-ID"] + ")]}"

		message["Message-ID"] = email.utils.make_msgid()
		message["Subject"] = subject 

		message["From"] = from_addr
		message["To"] = to_addr

		part1 = MIMEText(body, "plain")
		message.attach(part1)
		
		print(YELLOW + "** Sending mail!" + RESET)
		print(YELLOW + "**" * 20 + RESET)
		self.print_one_mail(message, verbose=1)
		print(YELLOW + "**" * 20 + RESET)

		# https://stackoverflow.com/questions/49203706/is-there-a-way-to-prevent-smtp-connection-timeout-smtplib-python
		# raise SMTPSenderRefused(code, resp, from_addr)
		# smtplib.SMTPSenderRefused: (451, b'4.4.2 Timeout - closing connection. n9sm6613295wrx.46 - gsmtp', 'ezalos.dev+ezalos.TM1704.ezalos@gmail.com')

		try:
			restart = True
			signal.alarm(60 * 15)
			self.server.sendmail(from_addr, to_addr, message.as_string())
			signal.alarm(0)
			restart = False
		except Exception as e:
			print("Error: ", e, "\tRECONNECTING...")
			self.reconnect()
			self.server.sendmail(from_addr, to_addr, message.as_string())
			restart = False
		finally:
			if restart:
				self.do_update.do_action(None)

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
		for num in data[0].split()[::-1]:
			try:
				restart = True
				signal.alarm(60 * 15)
				typ, data = self.inbox.fetch(num, '(RFC822)' )
				signal.alarm(0)
				restart = False
			except Exception as e:
				print("Error: ", e, "\tRECONNECTING...")
			finally:
				if restart:
					self.do_update.do_action(None)
			raw_email = data[0][1]
			raw_email_string = raw_email.decode('utf-8')
			msg = email.message_from_string(raw_email_string)
			mails.append(msg)
		return mails

	def keep_track(self, mail):
		identifier = get_email_identifier(mail['To'])
		if 'INIT' in mail['subject']:
			if identifier not in self.workers.keys():
				self.workers[identifier] = True
		if "ACK: " in mail['subject']:
			if identifier != 'all' and identifier in self.workers.keys():
				msg_time = get_subj_time(mail)
				if msg_time != None:
					msg_time = datetime.strptime(msg_time, "%H:%M:%S - %d/%m/%Y")
					if 'last_update' not in self.workers[identifier]:
						self.workers[identifier]['last_update'] = msg_time
					else:
						if msg_time > self.workers[identifier]['last_update']:
							self.workers[identifier]['last_update'] = msg_time
							print(f"Last activity from {identifier} is at {msg_time}")
				# msg_id = get_subj_msg_id(mail)
				
	def update_tasks_done(self, mail):
		# Dic of mails
		# If task:
		# 	if not exist :
		# 		dic of all workers (now) at false
		#	dic[id][w] = id
		#   if deleted not in dic[id]:
		#		del_mails -> ACKs + Task
		#		dic[id]['deleted'] = True
		pass
		# self.tasks_done[msg_id] = True

	def filter(self, mail):
		email = get_email(mail['From'])
		if email not in self.white_list:
			print("\tFILTER: Mail from is not in white_list")
			return False
		msg = mail
		if mail["Message-ID"] in self.tasks_done.keys():
			print("\tFILTER: Task already done")
			return False
		if not mail['subject']:
			print("\tFILTER: No subject")
			return False
		self.keep_track(mail)
		identifier = get_email_identifier(msg['To'])
		if not self.identifier == identifier and not identifier == "all":
			print("\tFILTER: Not for worker")
			return False
		if "ACK: " in mail['subject']:
			print("\tFILTER: ACK")
			msg_id = get_subj_msg_id(mail)
			if msg_id != None:
				self.tasks_done[msg_id] = True
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
					# self.workers.append(identifier)
					self.workers[identifier] = {}
		if not init_delcaration:
			init_delcaration = self.send_mail(
				self.identifier, "INIT", to_addr=make_email_address(self.login_adrr, "all"))
			self.workers[self.identifier] = {}
			# self.workers.append(self.identifier)
			self.mails = self.fetch_mail()
		self.workers['all'] = {}
		# self.workers.append('all')
		print(RED + "Workers: "+ RESET)
		for w in self.workers.keys():
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
		# TODO: when not init do all the tasks -> BAD
		origin = self.init_box()
		last_len = -1
		last_id = origin
		ite = 0
		while True:
			if last_len < len(self.mails) or ite % 5 == 0:
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
				ite += 1
			else:
				import time
				ite += 1
				time.sleep(60 * 1)
				if ite % self.idle_time == 0:
					self.do_tobe.ask_action(make_email_address(self.login_adrr, 'all'))
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
