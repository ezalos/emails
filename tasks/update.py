import git
import sys
import os
from task import MailTask


class SelfUpdate(MailTask):
	'''
		Obj: Task
		Body: *
	'''

	def __init__(self, mail_box):
		self.mb = mail_box
		self.identifier = self.mb.identifier
		self.task = "UPDATE"

	def is_for_me(self, mail):
		if self.task in mail['subject']:
			print("Task for " + self.task)
			return True
		return False

	def do_action(self, mail):
		git_dir = "."
		to_exec = [str(a) + ' ' for a in sys.argv]

		body = ""
		body += 'git_dir: ' + git_dir + '\n'
		body += 'to_exec: ' + to_exec + '\n'
		subj = self.task

		g = git.cmd.Git(git_dir)
		g.pull()

		self.mb.send_mail(body, subject=subj, reply=mail)
		os.execl(to_exec)
		sys.exit()
		# raise NotImplementedError

	def ask_action(self, dest):
		body = "?"
		self.mb.send_mail(body, subject=self.task, to_addr=dest)
		# raise NotImplementedError
