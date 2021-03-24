from requests import get
from task import MailTask

class FalseSSH(MailTask):
	'''
		Obj: Task - Key
		Body: Command
	'''
	def __init__(self, mail_box, login, key):
		self.mb = mail_box
		self.task = "EXEC"
		self.key = key

	def is_for_me(self, mail):
		if self.task in mail['subject']:
			if self.key in mail['subject']:
				print("Task for " + self.task)
				return True
		return False

	def do_action(self, mail):
		to_exe = self.mb.get_payload(mail)
		print("EXEC: `" + to_exe[0] + "`")
		body = ""
		self.mb.send_mail(body, subject=self.task, reply=mail)

	def ask_action(self, dest, body):
		body = "echo 'Hello World!\\n'"
		self.mb.send_mail(body, subject=self.task, to_addr=dest)
