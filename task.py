from utils import get_email_identifier

class MailTask():
	'''
		Obj: Task
		Body: *
	'''
	def __init__(self, mail_box):
		self.mb = mail_box
		self.identifier = self.mb.identifier
		self.task = "2B||!2B"

	def is_for_me(self, mail):
		if self.task in mail['subject']:
			print("Task for " + self.task)
			return True
		return False

	def do_action(self, mail):
		body = mail["Message-ID"]
		self.mb.send_mail(body, subject=self.task, reply=mail)
		# raise NotImplementedError

	def ask_action(self, dest):
		body = "?"
		self.mb.send_mail(body, subject=self.task, to_addr=dest)
		# raise NotImplementedError
