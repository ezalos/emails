from requests import get
from tasks.task import MailTask
import subprocess
import time

# Exec might be non blocking, but getting output is complex:
# Need to verify  if this solution works : 
# https://stackoverflow.com/questions/3906232/python-get-the-print-output-in-an-exec-statement
def execute_mail(cmd):
	t = time.process_time()
	# print(self.command)
	raw_output = subprocess.run(cmd, stdout=subprocess.PIPE,
								stderr=subprocess.PIPE, shell=True)
	t = time.process_time() - t
	stdout = raw_output.stdout.decode('utf-8')
	stderr = raw_output.stderr.decode('utf-8')

	output = ""
	output += "-" * 33 + "\n"
	output += "cmd: " + str(cmd) + "\n"
	output += "-" * 33 + "\n"
	output += "Time: " + str(t) + "\n"
	output += "-" * 33 + "\n"
	output += "stdout: " + str(stdout) + "\n"
	output += "-" * 33 + "\n"
	output += "stderr: " + str(stderr) + "\n"
	output += "-" * 33 + "\n"

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
		from emails import message_content
		to_exe = self.mb.get_payload(mail)
		to_exe = to_exe[0]
		if to_exe[-2:] == "\r\n":
			to_exe = to_exe[:-2]
		# print("#" * 100)
		# print("New way: ")
		# print(message_content(mail))
		# print("#" * 100)
		# print(to_exe)
		print("EXEC: `" + to_exe + "`")
		body = execute_mail(to_exe)
		dest = None
		if "wassup" in mail['Subject']:
			dest = mail['From']
		self.mb.send_mail(body, subject=self.task, to_addr=dest, reply=mail)

	def ask_action(self, dest, body):
		body = "echo 'Hello World!\\n'"
		self.mb.send_mail(body, subject=self.task, to_addr=dest)
