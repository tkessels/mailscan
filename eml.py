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
from functools import lru_cache

import chardet
import magic
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
        for v in self.get_header_raw(field):
            for value,encoding in email.header.decode_header(v):
                if encoding != None:
                    value=value.decode(encoding)
                else:
                    value=self.__decode(value)
                yield ' '.join(value.split())
            

    def get_header_raw(self, field):
        """Get list of all raw values for given header field."""
        # msg=self.get_eml()
        items = []
        for key, value in self.header:
            if key.lower() == field.lower():
                items.append(value)
        return items

    @property
    @lru_cache()
    def md5(self):
        return hashlib.md5(self.rawdata).hexdigest()

    @property
    @lru_cache()
    def sha1(self):
        return hashlib.sha1(self.rawdata).hexdigest()

    @property
    @lru_cache()
    def sha256(self):
        return hashlib.sha256(self.rawdata).hexdigest()

    @lru_cache(maxsize=2)
    def get_eml(self):
        """Get email.email Object for this email."""
        return email.message_from_bytes(self.rawdata)

    @property
    def rawdata(self):
        data = open(self.filename, 'rb').read()
        return data


    def __get_from_struct(self, fieldname, struct=None):
        if struct is None:
            struct = self.struct
        if fieldname in struct and struct[fieldname] is not None:
            yield struct[fieldname]
        if "parts" in struct and len(struct["parts"]) > 0:
            for child in struct["parts"]:
                for hit in self.__get_from_struct(fieldname, child):
                    yield hit

    def __get_sub_struct(self, msg_part):
        tmp_struct = {}
        tmp_struct['content_type'] = msg_part.get_content_type()
        tmp_struct['content_disposition'] = msg_part.get_content_disposition()
        
        if msg_part.is_multipart():
            tmp_struct["parts"] = [self.__get_sub_struct(part) for part in msg_part.get_payload()]
        else:
            data = msg_part.get_payload(decode=True)
            tmp_struct['data'] = data
            if msg_part.get_filename():
                tmp_struct['filename'] = (self.__decode(msg_part.get_filename()))
                tmp_struct['size'] = len(tmp_struct['data'])
            try:
                tmp_struct['mime'] = magic.from_buffer(data,mime=True)
                tmp_struct['magic'] = magic.from_buffer(data)
            except:
                pass
            tmp_struct["md5"] = hashlib.md5(data).hexdigest()
            tmp_struct["sha1"] = hashlib.sha1(data).hexdigest()
            tmp_struct["sha256"] = hashlib.sha256(data).hexdigest()
        return tmp_struct

    @property
    def struct(self):
        """Get structure of email as dictionary."""
        if self._struct is None:
            self._struct = self.__get_sub_struct(self.get_eml())
        return self._struct

    @property
    def flat_struct(self):
        """Get structure of email as array."""
        return self.__flatten_struct(self.struct)

    def __flatten_struct(self, struct, index=0):
        x = struct
        x['index'] = index
        yield x
        if 'parts' in x:
            for y in x['parts']:
                for element in self.__flatten_struct(y):
                    index += 1
                    element['index'] = index
                    yield element

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
        return self.get_header("from")
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
        type = (md5,sha1,sha256)
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
            text, encoding = email.header.decode_header(string)[0]
            if encoding is None:
                return text
            else:
                return text.decode(encoding)
        if isinstance(string, bytes):
            encodings = ['utf-8-sig', 'utf-16', 'iso-8859-15']
            detection = chardet.detect(string)
            if "encoding" in detection and len(detection["encoding"]) > 2:
                encodings.insert(0,detection["encoding"])
            for encoding in encodings:
                try:
                    return string.decode(encoding)
                except UnicodeDecodeError:
                    pass

    def __convert_date_tz(self, datetime, tz='UTC'):
        return datetime.astimezone(tz=timezone(tz))

    def __struct_str(self,struct,level=0,index=0):
        content_disposition = struct['content_disposition'] if struct['content_disposition'] else ''
        if 'attachment' in content_disposition:
            content_disposition='📎'
        output = ''
        output += '{}{} {}\n'.format(" "*level,struct['content_type'],content_disposition)
        if 'filename' in struct:
            output += '{} filename : {}\n'.format(" "*level,struct['filename'])
        if 'size' in struct:
            output += '{} size     : {}\n'.format(" "*level,struct['size'])
        if 'mime' in struct:
            if struct['mime'] != struct['content_type']:
                output += '{} !MIME!   : {}\n'.format(" "*level,struct['mime'])
        if 'magic' in struct:
            if struct['magic'] != struct['content_type']:
                output += '{} magic    : {}\n'.format(" "*level,struct['magic'][:180])
        if 'md5' in struct:
            output += '{} md5      : {}\n'.format(" "*level,struct['md5'])
        if 'sha1' in struct:
            output += '{} sha1     : {}\n'.format(" "*level,struct['sha1'])
        if 'sha256' in struct:
            output += '{} sha256   : {}\n'.format(" "*level,struct['sha256'])
        if 'parts' in struct and len(struct['parts'])>0:
            for x in struct['parts']:
                output += self.__struct_str(x,level=level+4)
        return output

    def __str__(self):
        output = f"╦═══>{self.full_filename}<\n"
        output +=f"╟╌┄MD5    : {self.md5}\n"
        output +=f"╟╌┄SHA1   : {self.sha1}\n"
        output +=f"╙╌┄SHA256 : {self.sha256}\n"
        if "done" in self.status:
            for f in self.froms:
                output += "From   : {}\n".format(f)
            for t in self.tos:
                output += "To     : {}\n".format(t)
            output += "Date   : %s\n" % self.date
            for s in self.subject:
                output += "Subject: {}\n".format(s)
            output += "MAIL-PARTS  ⮷ \n{}".format(self.__struct_str(self.struct,level=2))


        return output

    def __init__(self, filename, hash_attachments=True):
        self.status = "new"
        self.filename = filename
        self.full_filename = os.path.abspath(filename)
        try:
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
    import argparse
    parser=argparse.ArgumentParser()
    parser.add_argument('mail',help="Mail you want to analyze")
    args=parser.parse_args()
    malmail=Eml(args.mail)
    print(malmail)


