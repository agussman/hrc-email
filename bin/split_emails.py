#!/usr/bin/env python
# coding: utf-8
"""
split_emails.py -

 Input: Cleaned text email chains from `strip_statedept_headers.py`

 Output: Individual files for each email

"""
import os
import argparse
from glob import glob
import re
from time import mktime, strptime
from datetime import datetime
from dateutil.parser import parse

import talon
from talon import quotations
from talon.utils import get_delimiter
talon.init()


# Regexes taken from talon

RE_ON_DATE_SMB_WROTE = re.compile(
    u'(-*[ ]?({0})[ ].*({1})(.*\n){{0,2}}.*({2}):?-*)'.format(
        # Beginning of the line
        u'|'.join((
            # English
            'On',
            # French
            'Le',
            # Polish
            'W dniu',
            # Dutch
            'Op',
            # German
            'Am'
        )),
        # Date and sender separator
        u'|'.join((
            # most languages separate date and sender address by comma
            ',',
            # polish date and sender address separator
            u'użytkownik'
        )),
        # Ending of the line
        u'|'.join((
            # English
            'wrote', 'sent',
            # French
            u'a écrit',
            # Polish
            u'napisał',
            # Dutch
            'schreef','verzond','geschreven',
            # German
            'schrieb'
        ))
    ))
# Special case for languages where text is translated like this: 'on {date} wrote {somebody}:'
RE_ON_DATE_WROTE_SMB = re.compile(
    u'(-*[ ]?({0})[ ].*(.*\n){{0,2}}.*({1})[ ]*.*:)'.format(
        # Beginning of the line
        u'|'.join((
        	'Op',
        	#German
        	'Am'
        )),
        # Ending of the line
        u'|'.join((
            # Dutch
            'schreef','verzond','geschreven',
            # German
            'schrieb'
        ))
    )
    )

RE_FROM_COLON_OR_DATE_COLON = re.compile(u'(_+\r?\n)?[\s]*(:?[*]?{})[\s]?:[*]? .*'.format(
    u'|'.join((
        # "From" in different languages.
        'From', 'Van', 'De', 'Von', 'Fra',
        # "Date" in different languages.
        #'Date', 'Datum', u'Envoyé' #AARON: Disabled. Getting false positives on split.
    ))), re.I)



# TODO: Figure out how to handle "Original Message" lines
SPLITTER_PATTERNS = [
    #RE_ORIGINAL_MESSAGE,
    # <date> <person>
    re.compile("(\d+/\d+/\d+|\d+\.\d+\.\d+).*@", re.VERBOSE),
    RE_ON_DATE_SMB_WROTE,
    RE_ON_DATE_WROTE_SMB,
    RE_FROM_COLON_OR_DATE_COLON,
    re.compile('\S{3,10}, \d\d? \S{3,10} 20\d\d,? \d\d?:\d\d(:\d\d)?'
               '( \S+){3,6}@\S+:')
    ]


FOR_COLON = re.compile('For:', re.I)

# TODO: Improve this to use actual keys that you see in emails
# from, sent, to, subject, attachments, cc, e.g.
# TODO: Somehow make ':' options, see Pdftotext-layout/C05739675.txt
HEADER_KEY_COLON = re.compile('(\w+):(.*)')


SENT_DATE_FORMATS = [
    '''
    '%A, %B %d, %Y %I:%M %p',   # Wednesday, September 12, 2012 07:46 AM (dateutil.parser OK)
    '%A, %B %d,%Y %I:%M %p',    # Wednesday, September 12,2012 12:44 PM (du.p OK)
    '%A, %B %d %Y %I:%M %p',    # Tuesday, September 11 2012 1:31 PM
    '%A, %B %d, %Y %I:%M %p',   # Sunday, March 13, 2011 10:55 AM
    #'%A, %B %d %Y %I%M %p',     # Wednesday, September 12 2012 700 PM -> DATE_MISSING_COLON
    '%a %b %d %H:%M:%S %Y',      # Sun Mar 27 12:12:03 2011
    '%B %d, %Y, %I:%M:%S %p %Z', # October 1, 2012, 8:10:03 PM EDT
    #'%A, %B %-d,%Y %I:%M %p',   # Friday. April 1,2011 11:53 AM
    '%a, %d %b %Y %H:%M:%S',     # Mon, 6 Dec 2010 04:41:49
    '%a, %d %b %Y %H:%M:%S %z',  # Tue, 7 Dec 2010 10:48:52 -0500
    '%a, %b %d, %Y %I:%M %p',    # Wed, Dec 15, 2010 1:21 PM
    '%m/%d/%Y %I:%M %p',         # 12/14/2010 03:31 PM
    '''
    #'%a %d %b %Y %H:%M:%S %z',  # Tue 7 Dec 2010 10:48:52 -0500
]


DATE_MISSING_COLON = re.compile('(\d?\d) ?(\d\d .M)$')

def partition(alist, indices):
    """
    Break up a list into sublists, given a list of indices
    Taken from: http://stackoverflow.com/questions/1198512/split-a-list-into-parts-based-on-a-set-of-indexes-in-python
    """
    return [alist[i:j] for i, j in zip([0]+indices, indices+[None])]

# This is a redone version of talon.quotations.mark_message_lines()
def mark_message_lines(lines):
    """
    Mark which lines represent transitions from email to email
    :param lines:
    :return:
    """
    markers = ['x'] * len(lines)

    i = 0
    while i < len(lines):
        if not lines[i].strip():
            markers[i] = 'e'  # empty line

        else:
            # Check if transition/forward
            for pattern in SPLITTER_PATTERNS:
                matcher = re.match(pattern, lines[i])
                if matcher:
                    # If the previous line is 'For:', don't mark it
                    if re.match(FOR_COLON, lines[i-1]):
                        continue
                    markers[i] = 's'
        i += 1

    return markers


def split_emails(msg_body):
    """
    :param text: plain text email chain
    :return: ???
    """

    delimiter = get_delimiter(msg_body)
    msg_body = quotations.preprocess(msg_body, delimiter)
    lines = msg_body.splitlines()

    markers = mark_message_lines(lines)

    # Get the indices for all markers denoting a quoted section
    transitions = [i for i, x in enumerate(markers) if x == 's']

    sections = partition(lines, transitions)

    return sections

def extract_features(emails):
    """
    For each email, extract the relevant features
    :param emails:
    :return:
    """
    features = []
    for sect_num, sect_lines in enumerate(emails):

        headers = {}
        i = 0

        m = re.match(HEADER_KEY_COLON, sect_lines[i])
        while m is not None and i < len(sect_lines):
            key = m.group(1).lower()
            val = m.group(2).strip()
            headers[key] = val
            #print "%s -> %s" % (key, val)
            i += 1
            if i < len(sect_lines):
                m = re.match(HEADER_KEY_COLON, sect_lines[i])
            #if key == 'to':
            #    print "%s\tto\t(%s)" % (sect_num, val)
        #print ''
        headers['text'] = "\n".join(sect_lines[i:])
        #print headers['text']
        features.append(headers)

    return features

def sent_to_datetime(date_str):
    """
    Do a bunch of stuff to try and parse the "Sent" field in the email to a datetime
    :param parts:
    :return:
    """

    # Replace all non-: punctuation characters with space, they aren't needed for dateutil.parse
    # Keep - for timezone offset
    date_str = re.sub('[^\w:-]', ' ', date_str)
    # Remove adjacent spaces
    date_str = " ".join(date_str.split())

    # OCR tends to drop the colon from ##:## XM
    # '(\d?\d)(\d\d) ([A|P]M)'
    date_str = re.sub(DATE_MISSING_COLON, r"\1:\2", date_str)

    # Space gets dropped a lot between year and hour 201306:54 PM
    # NOTE hour must be 2-digits, otherwise could be ambiguous eg 20112:00
    date_str = re.sub('(\d{4})(\d\d:\d\d .M)', r"\1 \2", date_str)


    # Sometimes the redacted marker ends up on the line as well. Remove it.
    # NOTE: Think this can be removed now
    # date_str = re.sub('\s+B\d$', "", date_str)

    # Remove ' at ' if its in there
    date_str = re.sub('\s+at\s+', ' ', date_str)

    # If it ends in "Eastern Standard Time", replace it with EST
    date_str = re.sub('Eastern Standard Time', 'EST', date_str, flags=re.I)


    # Try to parse it w/ dateutil function
    try:
        dt = parse(date_str)
        return dt
    except ValueError:
        pass

    for date_format in SENT_DATE_FORMATS:
        try:
            dt = datetime.fromtimestamp(mktime(strptime(date_str, date_format)))
            return dt
        except ValueError:
            pass


    print "UNPARSABLE DATE: {}".format(date_str)
    return None


def parse_features(features):

    parsed_parts = []
    for sect_num, section in enumerate(features):

        parts = {
            'sect_num': sect_num,
        }

        # OCR Pretty consistently misses the 'H' in the To: line
        # Can only really safely do it on first section,
        # if it's missing in lower sections it could be the result of a redaction
        # Note that subsequent sections might not have a 'To' field
        if sect_num == 0 and not section.get('to'):
            parts['to'] = ['H']
        elif section.get('to'):
            # Split the 'to' field on semicolon
            parts['to'] = [x.strip() for x in section.get('to', '').split(';')]

        # Same for 'cc'
        if section.get('cc'):
            parts['cc'] = [x.strip() for x in section.get('cc', '').split(';')]

        # Store 'sent', or use 'date' if that's present instead
        if section.get('sent'):
            parts['sent'] = section.get('sent')
        elif section.get('date'):
            parts['sent'] = section.get('date')

        # Copy these over if they exist
        for key in ['from', 'subject', 'text', 'attachments']:
            if section.get(key):
                parts[key] = section.get(key)

        # Do a whole bunch of stuff to try and turn the sent into a datetime object
        if parts.get('sent'):
            parts['timestamp'] = sent_to_datetime(parts.get('sent'))

        parsed_parts.append(parts)

    return parsed_parts



def main():

    args = parse_options()
    out_dir = args.out_dir
    input_glob = args.input_glob

    # Track some things


    #for fname in glob(input_glob):
    #for fname in glob(input_glob)[:10]:
    for fname in glob(input_glob)[-1000:]:

        basename = os.path.splitext(os.path.basename(fname))[0]
        oname = os.path.join(out_dir, basename+".txt")

        # Read in the entire file
        txt = open(fname).read()

        # Split into individual sections (skip empty first email)
        emails = split_emails(txt)[1:]

        # Extract features
        features = extract_features(emails)

        parsed = parse_features(features)

        #pprint(parsed)


        #print "{} {} {} {}".format(fname, oname, len(txt), len(emails))




def parse_options():
     parser = argparse.ArgumentParser(description='Split email chains')
     parser.add_argument('-o', '--out_dir', dest='out_dir', action="store", metavar="DIR", required=True)
     parser.add_argument('-f', '--files', dest='input_glob', action="store", metavar="GLOB", required=True)

     return parser.parse_args()

if __name__ == '__main__':
    main()


