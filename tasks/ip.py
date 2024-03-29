from requests import get
from tasks.task import MailTask


class SendIP(MailTask):
	'''
		Obj: Task
		Body: *
	'''

	def __init__(self, mail_box, login):
		self.mb = mail_box
		self.task = "IPing"

	def is_for_me(self, mail):
		if self.task in mail['subject']:
			print("Task for " + self.task)
			return True
		return False

	def do_action(self, mail):
		ip = get('https://api.ipify.org').text
		dest = None
		self.mb.send_mail(ip, subject=self.task, to_addr=dest, reply=mail)
		if "wassup" in mail['Subject']:
			dest = mail['From']
			self.mb.send_mail(ip, subject=self.task, to_addr=dest, reply=mail)

	def ask_action(self, dest, body):
		body = "echo 'Hello World!\\n'"
		self.mb.send_mail(body, subject=self.task, to_addr=dest)

	def do_routine(self):
		ip = get('https://api.ipify.org').text
		subject = "IPong"
		print("Checking last emails received for current IP: ", ip)
		for msg in self.mb.mails:
			if self.is_for_me(msg):
				pay = self.mb.get_payload(msg)
				for p in pay:
					if p == ip:
						print("Last email already have good IP")
						return
				print("Last email does not have good IP")
				print("Sending good IP...")
				self.mb.send_mail(ip, subject)
				return
		print("No emails with IP detail")
		print("Sending good IP...")
		self.mb.send_mail(ip, subject)
