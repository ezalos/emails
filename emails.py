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
import copy
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
		# ------------------
		# INIT SERVER
		# ------------------
		print("Attempting to connect...")
		self.server = server
		self.server.login(login["user"], login["password"])
		print("SMTP connected for sending mails!")
		self.inbox = imaplib.IMAP4_SSL("imap.gmail.com")
		self.inbox.login(login["user"], login["password"])
		print("IMAP connected for receiving mails!")

		# ------------------
		# INIT DATA
		# ------------------
		## BIG DATA STRUCTURES:
		self.mails = {}
		# mails:	{	# Need to be ordered
		#				msg_id : {
		#							msg:		mail
		#							raw_msg:	r_mail # For clean
		#							workers:	{	# NEED strong init gestion
		#											identifiant * n:	None -> ack_id
		#											deleted:			bool
		# 										}
		#							index:	int # just_in_case
		#							?from: 	identifiant
		#							?to: 	identifiant
		#							?subj: 	str/split in dict?
		#							?body: 	str #order
		# 						 }	
		# 			}
		self.workers = {}
		# Workers: {
		# 			identifier * n:	{
		#								last_update: time
		#								init_mail: msg_id
		# 							}
		# 			}

		## SECURITY:
		self.key = get_password(key, 1)['password']
		self.white_list = white_list
		self.safebox = login

		## SELF
		self.identifier = make_email_identifier()
		self.login_adrr = login['user']
		self.mail_addr = make_email_address(login['user'], self.identifier)
		print('Mail: ' + self.mail_addr)
		print('Identifier: ' + self.identifier)

		## LOGISTICS
		self.idle_time = 5
		# self.tasks = {}

		## DO
		self.do_ip = SendIP(self, self.identifier)
		self.do_exec = FalseSSH(
			self, self.mail_addr, self.key)
		self.do_tobe = MailTask(self)
		self.do_update = SelfUpdate(self)

		## TMP
		self.tasks_done = {}

		# ------------------
		# INIT BOX
		# ------------------
		self.mails = self.fetch_mail()
		self.init_box()
		self.do_tobe.ask_action(make_email_address(self.login_adrr, 'all'))

	def fetch_mail(self, folder="inbox", search="ALL"):
		print("~" * 40)
		print(f"{YELLOW}NEW FETCH{RESET} at {GREEN}{datetime.now().strftime(" % H: % M: % S - %d/%m/%Y")}{RESET}")
		print("~" * 40)

		self.inbox.select(folder)
		# TODO: only fetch all 1st time, after do since laste date
		type, data = self.inbox.search(None, search)
		i = 0
		mails = {}
		for mail_obj in data[0].split()[-1::-1]:
			# Access data
			typ, data = self.inbox.fetch(mail_obj, '(RFC822)')
			raw_email = data[0][1]
			raw_email_string = raw_email.decode('utf-8')
			msg = email.message_from_string(raw_email_string)

			# Store data
			mails[msg["Message-ID"]] = {}
			mails[msg["Message-ID"]]['email'] = msg
			mails[msg["Message-ID"]]['raw_email'] = mail_obj
			mails[msg["Message-ID"]]['identifier_to'] = get_email_identifier(msg['To'])
			mails[msg["Message-ID"]]['identifier_from'] = get_email_identifier(msg['From'])
			mails[msg["Message-ID"]]['mail_addr_to'] = get_email(mail['To'])
			mails[msg["Message-ID"]]['mail_addr_from'] = get_email(mail['From'])
			mails[msg["Message-ID"]]['mail_id'] = msg["Message-ID"]
			# Should be done during processing
			# mails[msg["Message-ID"]]['workers'] = copy.deepcopy(self.workers)
			mails[msg["Message-ID"]]['index'] = i

			i += 1
		return mails


	def filter(self, mail):
		# ret_types
		t_delete = 		0b00000001
		t_done = 		0b00000010
		t_error = 		0b00000100
		t_identifier =	0b00001000
		t_ack = 		0b00010000
		t_init = 		0b00100000

		ret = 0

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

	def delete(self, mail):
		self.inbox.store(mail, '+FLAGS', '\\Deleted')

	def process_mail(self, mail, action=True):
		t_delete = 		0b00000001
		t_done = 		0b00000010
		t_error = 		0b00000100
		t_identifier =	0b00001000
		t_ack = 		0b00010000
		t_init = 		0b00100000

		self.print_one_mail(self.mails[id], id=id)

		# Workers: {
		# 			identifier * n:	{
		#								last_update: time
		#								init_mail: msg_id
		# 							}
		# 			}

		attributes = self.filter(mail)
		if attributes ^ t_delete or attributes ^ t_error:
			self.delete(mail)
		if attributes ^ t_init:
			self.workers[] 



		if self.filter(self.mails[id]):
			if "INIT" in self.mails[id]['subject']:
				identifier = self.get_payload(self.mails[id])[0]
				if identifier == self.identifier:
					init_delcaration = self.mails[id]["Message-ID"]

		if self.filter(self.mails[id]):
			self.do_tasks(self.mails[id])
		if origin == self.mails[id]["Message-ID"]:
			break
		elif last_id == self.mails[id]["Message-ID"]:
			break
		print()


	def init_box(self):
		# for mail_to_del in data[0].split():
		# mails:	{	# Need to be ordered
		#				msg_id : {
		#							msg:		mail
		#							raw_msg:	r_mail # For clean
		#							workers:	{	# NEED strong init gestion
		#											identifiant * n:	None -> ack_id
		#											deleted:			bool
		# 										}
		#							index:	int # just_in_case
		#							?from: 	identifiant
		#							?to: 	identifiant
		#							?subj: 	str/split in dict?
		#							?body: 	str #order
		# 						 }
		# 			}

		# Cleaning in 
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
		print(RED + "Workers: " + RESET)
		for w in self.workers.keys():
			if w == 'all':
				print("\t" + BLUE + w + RESET)
			elif w == self.identifier:
				print("\t" + GREEN + w + RESET)
			else:
				print("\t" + YELLOW + w + RESET)
		return init_delcaration


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
			self.server.sendmail(from_addr, to_addr, message.as_string())
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


def delete_mail_from_uid(m, uiid, folder='INBOX'):
	no_of_msgs = int(m.select(folder)[1][0])
	print(f"Nb of msg: {no_of_msgs}")
	typ, data = m.search(None, '(FROM "{0}")'.format(uiid))
	if data != ['']:  # if not empty list means messages exist
		for mail_to_del in data[0].split():
			print(f"Deleting {mail_to_del}")
			m.store(mail_to_del, '+FLAGS', '\\Deleted')
	else:
		print("- Nothing to remove.")


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
