from requests import get
from task import MailTask
import subprocess
import time

def execute_mail(cmd):
	# t = time.process_time()
	# print(self.command)
	raw_output = subprocess.run(cmd, stdout=subprocess.PIPE,
								stderr=subprocess.PIPE, shell=True)
	# time = time.process_time() - t
	stdout = raw_output.stdout.decode('utf-8')
	stderr = raw_output.stderr.decode('utf-8')

	output = "cmd: " + str(cmd) + "\n"
	output += "-" * 33 + "\n"
	# output += "Time: " + str(time) + "\n"
	# output += "-" * 33 + "\n"
	output += "stdout: " + str(stdout) + "\n"
	output += "-" * 33 + "\n"
	output += "stderr: " + str(stderr) + "\n"

	return output

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
		print(to_exe)
		print("EXEC: `" + to_exe[0] + "`")
		body = execute_mail(to_exe)
		dest = None
		if "wassup" in mail['Subject']:
			dest = mail['From']
		self.mb.send_mail(body, subject=self.task, to_addr=dest, reply=mail)

	def ask_action(self, dest, body):
		body = "echo 'Hello World!\\n'"
		self.mb.send_mail(body, subject=self.task, to_addr=dest)
