import git
import sys
import os
from tasks.task import MailTask
import __main__
from config import env_pswd, login

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
		print(sys.argv)
		to_exec = 'python3 main.py'
		print(to_exec)

		body = ""
		body += 'git_dir: ' + git_dir + '\n'
		body += 'to_exec: ' + to_exec + '\n'
		subj = self.task

		g = git.cmd.Git(git_dir)
		res = g.pull()
		print(res)

		# if res != 'Already up to date.':
		if mail != None:
			self.mb.send_mail(body, subject=subj, reply=mail)
		executable = sys.executable
		new_args = []
		new_args.append(executable)
		new_args.append(os.path.realpath(__main__.__file__))
		for av in sys.argv[1:]:
			new_args.append(av)
		new_env = os.environ
		new_env[env_pswd[0]] = self.mb.safebox['password']
		new_env[env_pswd[1]] = self.mb.key
		print(executable, new_args, new_env)
		os.execvpe(executable, new_args, new_env)
		print("QUITING!")
		sys.exit()
		# raise NotImplementedError

	def ask_action(self, dest):
		body = "?"
		self.mb.send_mail(body, subject=self.task, to_addr=dest)
		# raise NotImplementedError
