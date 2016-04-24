#!/usr/bin/env python
# coding: utf-8
"""
extract_json_field.py - Print out the value of a json field

  Input: Json files, field to extract

  Output: print out values for the field

"""

import argparse
from glob import glob
import json

def main():

    args = parse_options()
    input_glob = args.input_glob
    key = args.key

    for fname in glob(input_glob)[:10]:
        with open(fname) as data_file:
            data = json.load(data_file)

            print data[key]


def parse_options():
    parser = argparse.ArgumentParser(description='Split email chains')
    parser.add_argument('-f', '--files', dest='input_glob', action="store", metavar="GLOB", required=True)
    parser.add_argument('-k', '--key', dest='key', action="store", metavar="KEY", required=True)

    return parser.parse_args()

if __name__ == '__main__':
    main()