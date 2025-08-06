# *- coding: utf-8 -*-
# send_txt_msg.py
# 04-02-2021 03:08:34 EDT
# (c) 2021 acamso

"""Sends TXT message with GMail.

This is a demonstration on how to send an text message with Python.
In this example, we use GMail to send the SMS message,
but any host can work with the correct SMTP settings.
Each carrier has a unique SMS gateway hostname.
This method is completely free and can be useful in a variety of ways.

Video: https://youtu.be/hKxtMaa2hwQ
Turn on: https://myaccount.google.com/lesssecureapps
"""

import asyncio
import re
from email.message import EmailMessage
from typing import Collection, List, Tuple, Union
from dotenv import dotenv_values

import aiosmtplib

env = dotenv_values(".env")

HOST = "smtp.gmail.com"
# https://kb.sandisk.com/app/answers/detail/a_id/17056/~/list-of-mobile-carrier-gateway-addresses
# https://www.gmass.co/blog/send-text-from-gmail/
CARRIER_MAP = {
    "verizon": "vtext.com",
    "tmobile": "tmomail.net",
    "sprint": "messaging.sprintpcs.com",
    "at&t": "txt.att.net",
    "boost": "smsmyboostmobile.com",
    "cricket": "sms.cricketwireless.net",
    "uscellular": "email.uscc.net",
}


def truncate_message(msg: str, max_length: int = 160, add_ellipsis: bool = True) -> str:
    """Truncate message to fit SMS character limits."""
    if len(msg) <= max_length:
        return msg
    
    if add_ellipsis:
        # Reserve space for ellipsis
        truncated = msg[:max_length - 3] + "..."
    else:
        truncated = msg[:max_length]
    
    return truncated


# pylint: disable=too-many-arguments
async def send_txt(
    num: Union[str, int], carrier: str, email: str, pword: str, msg: str, subj: str,
    max_length: int = 160, split_long_messages: bool = True
) -> List[Tuple[dict, str]]:
    to_email = CARRIER_MAP[carrier]
    
    # Split message if it's too long
    if split_long_messages and len(msg) > max_length:
        messages = []
        
        # Calculate how much space the part indicator will take
        # Estimate based on worst case: "(999/999) " = 10 characters
        total_parts_estimate = (len(msg) + max_length - 1) // max_length
        part_indicator_length = len(f"({total_parts_estimate}/{total_parts_estimate}) ")
        effective_max_length = max_length - part_indicator_length
        
        # Recalculate with the effective length
        total_parts = (len(msg) + effective_max_length - 1) // effective_max_length
        
        for i in range(0, len(msg), effective_max_length):
            part_num = (i // effective_max_length) + 1
            chunk = msg[i:i + effective_max_length]
            
            # Add part indicator if message is split
            if total_parts > 1:
                part_msg = f"({part_num}/{total_parts}) {chunk}"
            else:
                part_msg = chunk
                
            messages.append(part_msg)
    else:
        messages = [msg]
    
    results = []
    send_kws = dict(username=email, password=pword, hostname=HOST, port=587, start_tls=True)
    
    for i, message_text in enumerate(messages):
        # build message
        message = EmailMessage()
        message["From"] = email
        message["To"] = f"{num}@{to_email}"
        # Only include subject in the first message of a multi-part series
        if i == 0:
            message["Subject"] = subj
        message.set_content(message_text)

        # send
        res = await aiosmtplib.send(message, **send_kws)  # type: ignore
        status = "failed" if not re.search(r"\sOK\s", res[1]) else "succeeded"
        print(f"Message part {i+1}/{len(messages)} {status}")
        results.append(res)
        
        # Small delay between messages to avoid rate limiting
        if len(messages) > 1 and i < len(messages) - 1:
            await asyncio.sleep(3)
    
    return results


async def send_txts(
    nums: Collection[Union[str, int]], carrier: str, email: str, pword: str, msg: str, subj: str,
    max_length: int = 160, split_long_messages: bool = True
) -> List[List[Tuple[dict, str]]]:
    tasks = [send_txt(n, carrier, email, pword, msg, subj, max_length, split_long_messages) for n in set(nums)]
    return await asyncio.gather(*tasks)

async def send_email(
    to_email: str, subject: str, body: str, email: str, pword: str
) -> Tuple[dict, str]:
    """Send a simple email."""
    message = EmailMessage()
    message["From"] = email
    message["To"] = to_email
    message["Subject"] = subject
    message.set_content(body)
    
    send_kws = dict(username=email, password=pword, hostname=HOST, port=587, start_tls=True)
    
    return await aiosmtplib.send(message, **send_kws)

if __name__ == "__main__":
    _num = env.get("PHONE_NUMBER", "")
    _carrier = "verizon"
    _email = env.get("SENDER_EMAIL", "")
    _pword = env.get("GMAIL_KEY", "")
    _msg = "123456789101214161820222426283032343638404244648505254565860626466686870727476787980828486888990929496989912345678910121416182022242628303234363840424464850525456586062646668687072747678798082848688899092949698991234567891012141618202224262830323436384042446485052545658606264666868707274767879808284868889909294969899"
    _subj = "Dummy subj"
    
    # Option 1: Split long messages automatically (default behavior)
    # coro = send_txt(_num, _carrier, _email, _pword, _msg, _subj)
    email = env.get("SENDER_EMAIL", "")
    email_coro = send_email(email, _subj, _msg, _email, _pword)
    
    # Option 2: Disable splitting and truncate manually
    # truncated_msg = truncate_message(_msg, max_length=160)
    # coro = send_txt(_num, _carrier, _email, _pword, truncated_msg, _subj, split_long_messages=False)
    
    # _nums = {"999999999", "000000000"}
    # coro = send_txts(_nums, _carrier, _email, _pword, _msg, _subj)
    asyncio.run(email_coro)