#!/usr/bin/env python
# coding: utf-8
import os
import argparse
import json
import urllib

URL_BASE = 'https://foia.state.gov/searchapp/'


def main():

    args = parse_options()
    ifile = args.json_results
    out_dir = args.out_dir

    with open(ifile) as f:
        data = json.load(f)

    print "Retrieving %s pdfs..." % len(data['Results'])

    for r in data['Results']:
        url = URL_BASE + r['pdfLink']
        pdfname = out_dir + '/' + os.path.basename(r['pdfLink'])
        if not os.path.isfile(pdfname):
            print "Retrieving %s -> %s" % (url, pdfname)
            urllib.urlretrieve(url, pdfname)
        else:
            print "Already exists %s" % pdfname


def parse_options():
     parser = argparse.ArgumentParser(description='Download Clinton email PDFs')
     parser.add_argument('-j', '--json_results', dest='json_results', action="store", metavar="FILE", required=True)
     parser.add_argument('-o', '--out_dir', dest='out_dir', action="store", metavar="DIR", required=True)

     return parser.parse_args()

if __name__ == '__main__':
    main()


