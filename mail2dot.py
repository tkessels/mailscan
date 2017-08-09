#!/usr/bin/python3
# -*- coding: utf-8 -*-
import os
import email
import hashlib
import sys
import re
import subprocess
nodes={}

basepath=sys.argv[1]
basecount=len(basepath.split(os.sep))-1
for root, dirs, files in os.walk(basepath):
    path = root.split(os.sep)
    relpath = os.sep.join(root.split(os.sep)[basecount:])
    for file in files:
        filename=root+os.sep+file
        relfilename=relpath+os.sep+file
        try:

            # file_handle=open(root+os.sep+file)
            # print(file)
            output=subprocess.run(["file",filename],stdout=subprocess.PIPE).stdout.decode('utf-8')
            filetype=output.split(":")[1]
            if "RFC 822 mail" in filetype:
                encoding='utf-8'
                encoding='latin-1'
                if "ISO-8859" in filetype:
                    encoding='iso-8859-1'
                    encoding='latin-1'
                elif "ASCII" in filetype:
                    encoding='latin-1'
                print(file + ":" + filetype,end='')
                msg=email.message_from_file(open(filename,'r',encoding=encoding))
                if "From" in msg.keys():
                    # msg_from=msg.get("From").replace(";",",")
                    print(msg.get("From"))
                    decoded_type=type(email.header.decode_header(msg.get("From"))[0][0])
                    print(decoded_type)
                    print(email.header.decode_header(msg.get("From"))[0][0])
                    if type(email.header.decode_header(msg.get("From"))[0][0]) is bytes:
                        print(email.header.decode_header(msg.get("From"))[0][0].decode("utf-8"))
                    else:
                        print(email.header.decode_header(msg.get("From")))[0][0]
                else:
                    msg_from="UNKNOWN"
                    if "Date" in msg.keys():
                        msg_date=msg.get("Date").replace(";",",")
                    else:
                        msg_date="UNKNOWN"

                if msg.is_multipart():
                    i=0
                    for part in msg.walk():
                        if "From" in part.keys():
                            i+=1
                            # msg_from=msg.get("From").replace(";",",")
                            # print("MULTI: "+part.get("From"))
                        else:
                            # print("MULTI: PART WITHOUT FROM")
                            msg_from="UNKNOWN"
                            if "Date" in msg.keys():
                                msg_date=msg.get("Date").replace(";",",")
                            else:
                                msg_date="UNKNOWN"
                    if i>1 : print ("MAIL WITH MULTIPLE FROMS :" + relfilename)
                    # for part in msg.walk():
                    #     if part.get_filename() is not None:
                    #         att_hash=hashlib.md5(part.get_payload(decode=True)).hexdigest()
                    #         att_filename=part.get_filename().replace(";",",")
                    #         att_mimetype=part.get_content_type().replace(";",",")
                    #         msg_filename=relfilename.replace(";",",")
                    #         print("%s;%s;%s;%s;%s;%s" % (att_filename,att_mimetype,att_hash,msg_date,msg_from,msg_filename))
                    #         # print("%s;%s" % (part.get_filename(),md5.hexdigest()))
                else:
                    pass
# =?utf-8?B?RGlyZWN0b3JhdGUgRGlyZWN0b3IgKERyLiBMw6FzemzDsyBGYXpla2FzKQ==?=
# =?utf-8?Q?Combat=20Helicopter=202017?=


        except Exception as e:
            print("-"+filename)
            print (e)
