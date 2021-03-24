from requests import get

class SendIP():
	'''
		Obj: Command - Device
		IP_WELC - ezalos-XXXX
	'''
	def __init__(self, mail_box, login):
		self.mb = mail_box
		self.subject = "IP_WELC"
		self.login = login

	def is_for_me(self, mail):
		msg = mail
		if msg['from'] == self.login:
			if msg['subject'] and msg['subject'][:len(self.subject)] == self.subject:
				return True
		return False

	def do_routine(self):
		ip = get('https://api.ipify.org').text
		subject = "IP_WELC"
		print("Checking last emails received for current IP: ", ip)
		for msg in self.mb.mails:
			if self.is_for_me(msg):
				pay = self.mb.get_payload(msg)
				for p in pay:
					if p == ip:
						print("Last email already have good IP")
						self.mb.print_one_mail(msg)
						return
				print("Last email does not have good IP")
				self.mb.print_one_mail(msg)
				print("Sending good IP...")
				self.mb.send_mail(ip, subject)
				return
		print("No emails with IP detail")
		print("Sending good IP...")
		self.mb.send_mail(ip, subject)
