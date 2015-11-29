#!/usr/bin/env python
# coding: utf-8

import os
import json
import urllib


# In[20]:

ifile = "response_cleaned.json"


# In[21]:

with open(ifile) as f:
    data = json.load(f)


# In[22]:

len(data['Results'])


# In[16]:

ifile = "cleaned_7945.json"


# In[17]:

with open(ifile) as f:
    data = json.load(f)


# In[18]:

len(data['Results'])


# In[24]:

url_base = 'https://foia.state.gov/searchapp/'


# In[29]:

for r in data['Results']:
    url = url_base + r['pdfLink']
    pdfname = 'data/' + os.path.basename(r['pdfLink'])
    if not os.path.isfile(pdfname):
        print "Retrieving %s -> %s" % (url, pdfname)
        urllib.urlretrieve(url, pdfname)
    else:
        print "Already exists %s" % pdfname


# In[ ]:



