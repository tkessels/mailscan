#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Eml - Wrapper class for email-objects

This Class is supposed to add needed decoding and formating to the email objects.
Furthermore file attachments get hashed.

In the Future these objects are supposed to be items in searchable catalogue.

@author tke
"""
import email
import hashlib
import inspect
import multiprocessing as mp
import os
import re
from email.header import decode_header
from functools import lru_cache

# from anytree import Node, RenderTree, AsciiStyle, PreOrderIter
# from anytree.importer import DictImporter
from dateutil.parser import parse
from pytz import timezone


def depricated(fn):
    def wraper(*args, **kwargs):
        print(f'''>{inspect.stack()[1].function} called depricated function {fn.__name__}''')
        return fn(*args, **kwargs)

    return wraper


class Eml(object):
    re_pat_email = r'''(?:[a-z0-9!#$%&'*+/=?^_`{|}~-]+(?:\.[a-z0-9!#$%&'*+/=?^_`{|}~-]+)*|"(?:[
    \x01-\x08\x0b\x0c\x0e-\x1f\x21\x23-\x5b\x5d-\x7f]|\\[\x01-\x09\x0b\x0c\x0e-\x7f])*")@(?:(?:[a-z0-9](?:[a-z0-9-]*[
    a-z0-9])?\.)+[a-z0-9](?:[a-z0-9-]*[a-z0-9])?|\[(?:(?:25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(?:25[0-5]|2[
    0-4][0-9]|[01]?[0-9][0-9]?|[a-z0-9-]*[a-z0-9]:(?:[\x01-\x08\x0b\x0c\x0e-\x1f\x21-\x5a\x53-\x7f]|\\[
    \x01-\x09\x0b\x0c\x0e-\x7f])+)\]) '''
    re_pat_ipv4 = r"""((25[0-5]|2[0-4][0-9]|[01]?[0-9]{1,2})\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9]{1,2})"""

    received_p_from_details = r'''\((?P<fqdn>[^\[\] ]+)?\s?(\[(?P<ip>\S+)\])?\s*(\([^\)]+\))?\)\s*(\([^\)]+\))?\s*'''
    received_p_from = r'''from (?P<from>\S+)\s*''' + received_p_from_details
    received_p_by = r'''\s*by\s+(?P<by>\S+)\s*(\([^\)]+\))?'''
    received_p_with = r'''\s*(with\s+(?P<with>.*))?'''
    received_p_id = r'''\s*(id\s+(?P<id>\S+))\s*(\([^\)]+\))?'''
    received_p_for = r'''\s*(for\s+(?P<for>\S*))?'''
    received_p_date = r''';\s*(?P<date>\w+,\s\d+\s\w+\s\d+\s[\d:]+\s[\d+-]+\s\(\w+\)).*\s*(\([^\)]+\))?'''
    re_pat_f_received = received_p_from + received_p_by + \
                        received_p_with + received_p_id + received_p_for + received_p_date

    re_pattern = {
        'email': re_pat_email,
        'ipv4': re_pat_ipv4,
        'received': re_pat_f_received
    }

    def get_header(self, field):
        """Get a decoded list of all values for given header field."""
        return [self.__decode(value) for value in self.get_header_raw(field)]

    def get_header_raw(self, field):
        """Get list of all raw values for given header field."""
        # msg=self.get_eml()
        items = []
        for key, value in self.header:
            if key.lower() == field.lower():
                items.append(value)
        return items

    @lru_cache(maxsize=2)
    def get_eml(self):
        """Get email.email Object for this email."""
        return email.message_from_binary_file(open(self.filename, 'rb'))

    def __get_from_struct(self, fieldname, struct=None):
        if struct is None:
            struct = self.struct
        if fieldname in struct and struct[fieldname] is not None:
            yield struct[fieldname]
        if "children" in struct and len(struct["children"]) > 0:
            for child in struct["children"]:
                for hit in self.__get_from_struct(fieldname, child):
                    yield hit

    def __get_sub_struct(self, msg_part):
        tmp_struct = {
            "content_type": msg_part.get_content_type(),
            "is_multipart": msg_part.is_multipart(),
            # "boundary": msg_part.get_boundary(),
            "filename": self.__decode(msg_part.get_filename()),
            # "default_type": msg_part.get_default_type(),
            "content_disposition": msg_part.get_content_disposition()
        }
        if msg_part.is_multipart():
            tmp_struct["children"] = [self.__get_sub_struct(part) for part in msg_part.get_payload()]
        else:
            data = msg_part.get_payload(decode=True)
            tmp_struct["md5"] = hashlib.md5(data).hexdigest()
            tmp_struct["sha256"] = hashlib.sha256(data).hexdigest()
        return tmp_struct

    @property
    def struct(self):
        """Get structure of email as dictionary."""
        if self._struct is None:
            self._struct = self.__get_sub_struct(self.get_eml())
        return self._struct

    def get_mail_path(self):
        """Get mail delivery path as reconstructed from received fields as list."""
        pass

    def get_timeline(self):
        """Get all timebased events for the mail as a list."""
        pass

    def get_date(self, tz='UTC'):
        """Get date of mail converted to timezone. Default is UTC."""
        date = [parse(x, fuzzy=True) for x in self.get_header("Date")]
        if len(date) > 0:
            if not tz is None:
                date = [self.__convert_date_tz(d, tz) for d in date]
            return date[0] if len(date) == 1 else date
        else:
            return None

    def get_from(self):
        """Get all sender indicating fields of mail as dictionary"""
        # from
        # reply-to
        # return-path
        # received envelope info
        pass

    def get_to(self):
        """Get all recipient indicating fields of mail as a dictionary"""

        pass

    def get_subject(self):
        """Get subject line of mail"""
        pass

    def get_index(self):
        """Get tokenized index of all parsable text. A bit like linux strings."""
        pass

    def get_hash(self, part='all', hash_type='md5'):
        """
        Get hash for selected parts.

        part = (all,body,attachments,index) index from get_struct
        type = (md5,sha256)
        """
        hashes = []
        if part == "all" or part == "attachments":
            hashes.extend([x for x in self.__get_from_struct(hash_type)])
        return hashes

    def get_attachments(self, filename=None):
        """Get list of attachments as list of dictionaries. (filename,mimetype,md5,sha256,rawdata)"""
        pass

    def get_lang(self):
        """Get a guess about content language."""
        pass

    def get_iocs(self, ioc_type='all'):
        """Get dictionary of iocs"""
        pass

    def as_string(self, formatstring):
        """Return string representation of mail based on formatstring."""
        pass

    def has_attachments(self):
        """Return True if mail has Files Attached."""
        return len(self.attachments) > 0

    def contains_hash(self, string):
        """Return True if the hash of any part of the Mail equals supplied string"""
        if len(string) == 64:
            return string.lower() in self.get_hash(hash_type='sha256')
        if len(string) == 32:
            return string.lower() in self.get_hash()
        return False

    def contains_string(self, string: str) -> bool:
        """Return True if mail contains string in its text."""
        return string.lower() in self.get_index()

    def check_spoof(self) -> bool:
        '''Perform spoof Check on mail an return result'''
        return False

    def check_sig(self) -> bool:
        '''Perform valide smime if available and return result'''
        return False

    def check_dkim(self) -> bool:
        '''Perform check on dkim signature if available return result'''
        return False

    def check_header(self) -> bool:
        '''Perform consistancy check on header fields result'''
        return False

    def extract_from_text(self, text, pattern='email'):
        pat = re.compile(self.re_pattern["email"], re.IGNORECASE)
        match = pat.findall(text)
        return match

    def __decode(self, string):
        '''Decode string as far as possible'''
        if isinstance(string, str):
            text, encoding = decode_header(string)[0]
            if encoding is None:
                return text
            else:
                return text.decode(encoding)
        if isinstance(string, bytes):
            for encoding in ['utf-8-sig', 'utf-16', 'cp1252']:
                try:
                    return string.decode(encoding)
                except UnicodeDecodeError:
                    pass

    def __convert_date_tz(self, datetime, tz='UTC'):
        return datetime.astimezone(tz=timezone(tz))

    def __str__(self):
        output = self.filename + ":\n"
        if "done" in self.status:
            output += "From: %s\n" % self.froms
            output += "To: %s\n" % self.tos
            output += "Date: %s\n" % self.date
            output += "Subject: %s\n" % self.subject
        return output

    def __init__(self, filename, hash_attachments=True):
        self.status = "new"
        self.filename = filename
        try:
            # self.msg = self.get_eml()
            self.header = self.get_eml().items()
            self.status = "processing_header"
            self.froms = self.get_header("from")
            self.tos = self.get_header("To")
            self.ccs = self.get_header("CC")
            self.subject = self.get_header("Subject")
            self.id = self.get_header("Message-ID")
            self.date = self.get_date()
            self.received = self.get_header("Received")
            self.status = "processing_attachments"
            self.attachments = []
            self._struct = None
            self.struct
            # if hash_attachments:
            #     for part in self.get_eml().walk():
            #         if part.get_filename() is not None:
            #             self.status = self.status + "."
            #             attachment = {}
            #             attachment["filename"] = self.__decode(part.get_filename())
            #             attachment["mimetype"] = part.get_content_type()
            #             # attachment["mimetype"] = part.get_content_type()
            #             attachment['rawdata'] = part.get_payload(decode=True)
            #             attachment["md5"] = hashlib.md5(attachment['rawdata']).hexdigest()
            #             attachment["sha256"] = hashlib.sha256(attachment['rawdata']).hexdigest()
            #             self.attachments.append(attachment)
            self.status = "done"
        except Exception as e:
            print(e)
            self.status = "not_parsable" + str(e)


def create_newmail(filename):
    return Eml(filename)


def scan_folder(basepath):
    list_of_mail = []
    base_count = len(basepath.split(os.sep)) - 1
    if os.path.isfile(basepath):
        e = Eml(basepath)
        print(e)
    else:
        with mp.Pool(processes=mp.cpu_count()) as pool:

            for root, dirs, files in os.walk(basepath):
                path = root.split(os.sep)
                relpath = os.sep.join(root.split(os.sep)[base_count:])

                new_mails = pool.map(create_newmail, [root + os.sep + s for s in files])
                list_of_mail.extend(new_mails)

        pool.close()
        pool.join()
    return list_of_mail


if __name__ == '__main__':
    a = scan_folder('/media/data/cases/testmails')
    b = [x for x in a if x.status == 'done']
    print(len(a))
    print(len(b))
    hashes = {}
    for x in b:
        for h in x.get_hash():
            if h in hashes:
                hashes[h].append(x)
            else:
                hashes[h] = [x]

    print(len(hashes))
    max = 0
    max_hash = ""
    for x in hashes:
        if len(hashes[x]) > max:
            max = len(hashes[x])
            max_hash = x

    print(max)
