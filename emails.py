from config import login
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import smtplib, ssl
import time
import imaplib
import email

import socket
from requests import get

class MailBox():
    
    def __init__(self, server):
        self.server = server
        self.server.login(login["user"], login["password"])

        self.inbox = imaplib.IMAP4_SSL("imap.gmail.com")
        self.inbox.login(login["user"], login["password"])

        self.mails = []

    def send_mail(self, body,
                  subject="", from_addr=login["user"], to_addr=login["user"]):
        
        message = MIMEMultipart()
        subject += " - " if len(subject) else ""
        subject += socket.gethostname()
        message["Subject"] = subject
        message["From"] = from_addr
        message["To"] = to_addr

        part1 = MIMEText(body, "plain")
        message.attach(part1)
        
        self.server.sendmail(login["user"], login["user"], message.as_string())
        print("Mail sent")
        print(message)

    def fetch_mail(self):
        self.inbox.select('inbox')
        type, data = self.inbox.search(None, 'ALL')
        self.mails = []
        for num in data[0].split()[-1::-1]:
            typ, data = self.inbox.fetch(num, '(RFC822)' )
            raw_email = data[0][1]
            raw_email_string = raw_email.decode('utf-8')
            msg = email.message_from_string(raw_email_string)
            self.mails.append(msg)

    def read_mail(self, refetch=False):
        if refetch or not len(self.mails):
            self.fetch_mail()
        for msg in self.mails:
            email_subject = msg['subject']
            email_from = msg['from']
            if msg.is_multipart():
                pay = [part.get_payload() for part in msg.get_payload()]
            else:
                pay = [msg.get_payload()]
            print('From : ', email_from)
            print('Subj : ', email_subject)
            print('Body : ', pay)
            print()

    def send_ip(self):
        ip = get('https://api.ipify.org').text
        subject = "IP_WELC"
        for msg in self.mails:
            if msg['from'] == login['user']:
                if msg['subject'] and msg['subject'][:len(subject)] == subject:
                    if msg.is_multipart():
                        pay = [part.get_payload() for part in msg.get_payload()]
                    else:
                        pay = [msg.get_payload()]
                    for p in pay:
                        if p == ip:
                            return
                    self.send_mail(ip, subject)
                    return
        self.send_mail(ip, subject)
                    

if __name__ == "__main__":
    port = 465  # For SSL
    # Create a secure SSL context
    context = ssl.create_default_context()
    with smtplib.SMTP_SSL("smtp.gmail.com", port, context=context) as server:
        mail_box = MailBox(server)
        mail_box.fetch_mail()
        mail_box.send_ip()
        mail_box.read_mail(True)
        #mail_box.send_mail(message, "Subject_TEST")
        #check_in()
        #print(ret)
        # TODO: Send email here

