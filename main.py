import re
from config import login
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib
import ssl
import time
import imaplib
import email
import os
import sys
import datetime
import socket
from requests import get
from getpass import getpass, getuser
from emails import MailBox
import argparse

def wait_for_internet_connection(max_try=5):
	attempt = 0
	while attempt < max_try * 6:
		try:
			get('http://www.google.com')
			print("Connected to internet !")
			print("Current date and time: ", datetime.datetime.now())
			return
		except:
			print("No internet. Attempt: ", attempt, "/", max_try * 6)
			time.sleep(10)
			pass
		attempt += 1
	print("Current date and time: ", datetime.datetime.now())


if __name__ == "__main__":
	parser = argparse.ArgumentParser()
	parser.add_argument(
			"-l",
			"--log",
			help="For Cronjob")
	parser.add_argument(
			"-i",
			"--ip",
			help="IP")
	parser.add_argument(
			"-e",
			"--exec",
			help="Command to exec")
	parser.add_argument(
            "-f",
			"--for",
			help="Ssubject of request")

	args = parser.parse_args()

	if args.log:
		dir_path = os.path.dirname(os.path.realpath(__file__))
		log = open(dir_path + "/cron_log", "a")
		sys.stdout = log
		print("Current date and time: ", datetime.datetime.now())

	port = 465  # For SSL
	# Create a secure SSL context
	wait_for_internet_connection()
	context = ssl.create_default_context()
	with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
		print("SMTP server opened")
		mail_box = MailBox(server, args)
		mail_box.fetch_mail()
		mail_box.do_routine()
		# TODO: Send email here
