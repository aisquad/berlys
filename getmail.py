import email
import imaplib
import os
import re

from datetime import datetime, timedelta
from locale import setlocale as set_local_env, LC_TIME as time_cat

from config import Config
from core import DateHandler
from filename_handler import FilenameHandler


class Mail:
    def __init__(self, email_body):
        self.config = Config().get_config()
        self.email_body = email_body.decode()
        self.part = None
        self.params = {}
        self.content = b''
        self.filename = ''
        self.file_type = ''
        self.file_path = ''
        self.delivery_date: DateHandler = None

    def discard_parts(self):
        if self.part.is_multipart():
            return True
        elif not self.part.get_content_disposition():
            return True
        return False

    def optimize_size(self):
        if self.params.get('size'):
            self.params['size'] = int(self.params['size'])

    def optimize_date(self, head):
        dt = datetime.strptime(self.params[f'{head}-date'], "%a, %d %b %Y %H:%M:%S %Z")
        self.params[f'{head}-date'] = int(datetime.timestamp(dt))

    def optimize_dates(self):
        if self.params.get('creation-date'):
            self.optimize_date('creation')
        if self.params.get('modification-date'):
            self.optimize_date('modification')

    def parse_params(self):
        content_disp = self.part.get("Content-Disposition")
        # TODO: this next line might disappear?
        content_disp = content_disp.replace("\r\n\t", "").replace('"', '').replace("; ", ";")
        # TODO: more ugly code!
        content_disp = content_disp.replace("=?iso-8859-1?Q?", "").replace("?=", "").replace("=E7", "ç")
        self.params = dict(
            [(item, True) if item.count("=") == 0 else tuple(item.split("=")) for item in content_disp.split(";")]
        )
        self.optimize_size()
        self.optimize_dates()

    def set_file_properties(self):
        if self.params['filename'].startswith("Volumen"):
            cdate = datetime.fromtimestamp(self.params['creation-date'])
            next_day = cdate + timedelta(days=1)
            _, ext = os.path.splitext(self.params['filename'])
            new_filename = f"{next_day.strftime('%Y-%m-%d')}{ext}"
            file_type = "data"
        else:
            new_filename = self.params['filename'].replace("ç", "").replace("_", " ")
            file_type = "sheet"
        self.filename = new_filename
        self.file_type = file_type

    def set_delivery_date(self):
        if self.file_type == 'data':
            match = re.search(r'(?P<date>\d{2}(\.)\d{2}\2\d{4})', self.content.decode())
            self.delivery_date = DateHandler(match.group('date'))
        else:
            self.delivery_date = DateHandler(self.params['creation-date'])

    def dispatch(self):
        mail = email.message_from_string(self.email_body)
        for part in mail.walk():
            self.part = part
            if self.discard_parts():
                continue
            if self.part.get_filename() in (self.config["default_filename"], self.config['xlsxfile']):
                self.parse_params()
                self.set_file_properties()
                self.content = self.part.get_payload(decode=True)
                self.set_delivery_date()


class GetMail:
    def __init__(self):
        set_local_env(time_cat, "en_US.UTF8")
        self.config = None
        self.session = None
        self.days_ago = 3
        self.sheet_is_saved = False
        self.last_data = ''
        self.last_filename = ''

    def set_config(self):
        c = Config()
        self.config = c.get_config()

    def set_session(self):
        self.session = imaplib.IMAP4_SSL(self.config['imap'])

    def login(self):
        self.set_config()
        self.set_session()
        email_address = f"{self.config['usr_email']}@{self.config['srv_email']}"
        type_, account_details = self.session.login(email_address, self.config['password'])
        if type_ != 'OK':
            raise Exception('Not able to sign in!')

    def save_file(self, mail: Mail):
        try:
            with open(mail.file_path, 'wb') as fp:
                print(f"saving {mail.file_path} (~ {len(mail.content)} b)")
                fp.write(mail.content)
        except OSError as e:
            print("Rejecting", e, mail.filename)

    def download_file(self, mail: Mail):
        fh = FilenameHandler()

        if mail.file_type == 'data':
            file_path = fh.to_data_dir(mail.delivery_date)
            if self.last_data == '':
                self.last_data = mail.content.decode()
                self.last_filename = file_path
            if not os.path.exists(file_path):
                mail.file_path = file_path
                self.save_file(mail)

        elif mail.file_type == 'sheet' and not self.sheet_is_saved:
            self.sheet_is_saved = True
            mail.file_path = fh.to_attachments_dir(mail.filename)
            self.save_file(mail)

    def iterate(self, msg_ids):
        # Iterating over all selected emails.
        for msg_id in msg_ids:
            type_, message_parts = self.session.fetch(msg_id, '(RFC822)')

            if type_ != 'OK':
                print('Error fetching mail.')
                break

            mail = Mail(message_parts[0][1])
            mail.dispatch()
            self.download_file(mail)

    def dispatch(self):
        self.session.select(self.config['label'])
        if self.session.state != "SELECTED":
            raise ValueError(f"No such label named '{self.config['label']}'")
        since_date = datetime.today() - timedelta(days=self.days_ago)
        since_date = since_date.strftime("%d-%b-%Y")
        type_, msg_ids = self.session.search(
            None,
            "ALL",  # f'(SUBJECT "{self.config["subject"]}")',
            f'SENTSINCE {since_date} FROM {self.config["sender"]}'
        )
        if type_ != 'OK':
            print('Error searching Inbox.')
            return

        msg_ids = msg_ids[0].split()
        msg_ids.sort()
        msg_ids.reverse()
        self.iterate(msg_ids)

    def close(self):
        self.session.close()
        self.session.logout()
