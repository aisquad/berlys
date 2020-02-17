import email
import imaplib
import os

from datetime import datetime, timedelta
from locale import setlocale as set_local_env, LC_TIME as time_cat


class GetMail:
    def __init__(self):
        set_local_env(time_cat, "en_US.UTF8")
        self.detach_dir = "."
        self.config = None
        self.session = None
        self._files = 0
        self.retrieved_file = ""
        self.data_path = os.path.join('..', '..', 'data', 'berlys')
        self.attachments_path = os.path.join(self.data_path, 'attachments')

    def set_config(self):
        import Berlys.berlys as berlys
        c = berlys.Config()
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

    def discard_parts(self, part):
        if part.is_multipart():
            # print ("#1 SKIPPING multipart")
            return True
        elif not part.get_content_disposition():
            # print ("#2 SKIPPING no content disposition")
            return True
        return False

    def wanted(self, filename_ext):
        if filename_ext.startswith(self.config["subject"]):
            return True
        elif filename_ext == self.config['xlsxfile']:
            return True
        else:
            print(filename_ext, "rejected")
        return False

    def optimize_size(self, params):
        if params.get('size'):
            params['size'] = int(params['size'])

    def optimize_date(self, params, key_header):
        dt = datetime.strptime(params[f'{key_header}-date'], "%a, %d %b %Y %H:%M:%S %Z")
        params[f'{key_header}-date'] = int(datetime.timestamp(dt))

    def optimize_dates(self, params):
        if params.get('creation-date'):
            self.optimize_date(params, 'creation')
        if params.get('modification-date'):
            self.optimize_date(params, 'modification')

    def parse_params(self, string):
        # TODO: this next line might disappear?
        string = string.replace("\r\n\t", "").replace("\"", "").replace("; ", ";")
        # TODO: more ugly code!
        string = string.replace("=?iso-8859-1?Q?", "").replace("?=", "").replace("=E7", "ç")
        params = dict([(item, True) if item.count("=") == 0 else tuple(item.split("=")) for item in string.split(";")])
        self.optimize_size(params)
        self.optimize_dates(params)
        return params

    def file_properties(self, params):
        write_over = False
        if params['filename'].startswith("Volumen"):
            cdate = datetime.fromtimestamp(params['creation-date'])
            next_day = cdate + timedelta(days=1)
            filename, ext = os.path.splitext(params['filename'])
            new_filename = f"{filename} {next_day.strftime('%Y-%m-%d')}{ext}"
        else:
            new_filename = params['filename'].replace("ç", "").replace("_", " ")
            write_over = self._files == 0
            self._files += 1
        return {"filename": new_filename, "write_over": write_over}

    def write_file(self, action, fname, file_path, part):
        try:
            with open(file_path, 'wb') as fp:
                print(f"{action} '{fname}'.")
                fp.write(part.get_payload(decode=True))
                if not self.retrieved_file and action == "creating":
                    self.retrieved_file = file_path
        except OSError as e:
            print("Rejecting", e, part.get_filename())

    def download_file(self, part):
        params = self.parse_params(part.get("Content-Disposition"))
        file_props = self.file_properties(params)
        new_filename = file_props['filename']
        writable = file_props['write_over']
        file_path = os.path.join(self.attachments_path, new_filename)
        if not os.path.exists(file_path) and writable:
            self.write_file('creating', new_filename, file_path, part)
        elif writable:
            self.write_file('writing', new_filename, file_path, part)
        elif new_filename.startswith(self.config['subject']):
            print(f"filename '{new_filename}' already exists.")

    def mail_sweep(self, email_body):
        mail = email.message_from_string(email_body.decode())
        for part in mail.walk():
            if self.discard_parts(part):
                continue

            filename_ext = part.get_filename()

            if self.wanted(filename_ext):
                self.download_file(part)

    def iterate(self, data):
        # Iterating over all emails
        for msg_id in data:
            type_, message_parts = self.session.fetch(msg_id, '(RFC822)')

            if type_ != 'OK':
                print('Error fetching mail.')
                break

            self.mail_sweep(message_parts[0][1])

    def check_dir(self):
        if 'attachments' not in os.listdir(self.data_path):
            os.mkdir(self.data_path)

    def dispatch(self):
        self.check_dir()

        self.session.select(self.config['label'])
        since_date = datetime.today() - timedelta(days=7)
        since_date = since_date.strftime("%d-%b-%Y")
        type_, data = self.session.search(
            None,
            "ALL",  # f'(SUBJECT "{self.config["subject"]}")',
            f'SENTSINCE {since_date} FROM {self.config["sender"]}'
        )
        if type_ != 'OK':
            print('Error searching Inbox.')
            return

        data = data[0].split()
        data.sort()
        data.reverse()
        self.iterate(data)

    def close(self):
        self.session.close()
        self.session.logout()
