# hrc-email
Tools for analyzing the Hillary Clinton emails


The Hillary Clinton email archives being released by the US Department of State are an intriguing data set for analysis. They're too large to easily analyze by hand, but still small enough that we can process them on a laptop. They also present something of a challenge: the emails were released by the Clinton camp without a third-party to ov it's in their own best interest not to divulge anything incriminating, but . It's certainly in the best interest of the Clinton camp not to release any incriminating information, but as they're the source of the emails, we have to rely on them that they've turned over anything.

However, given the that it's in their own best interest not to release anything incriminating, a healthy dose of skepticism seems appropriate. So the question is, are there any discrepancies or suspicious characteristics in the emails?

Since this is not Serial, I'll cut to the chase: there's no smoking gun here. There are some things that look a little strange, but these are not the Nixon tapes. But, it's still an interesting data analysis exercise .

USE THIS TEXT:::
They were ordered to turn over all their emails from that time. But, they're highly incentivized to withhold any emails that are particularly incriminating and, to a large extent, there's no way to verify using external sources if they did. Presumably they did turn everything over, but it does present an interesting analysis challenge, to look for anything *within* the released portion of data that would indicate tampering or illicit activity.

and as the sole party with access to the original data, there's no outside source we can cross reference to know

All of the scripts used in this blog post are accessible from GitHub: https://github.com/agussman/hrc-email

I've divided the process into 4 Blog Posts:

1) Collection

2) Ingestion

3) Analysis* (*: Super bummed this ruined by "-tion" streak)

## Collection

https://foia.state.gov/Search/Results.aspx?collection=Clinton_Email
The US Department of State has been released 30,322 documents from Clinton's email from her time as Secretary of State. They are definitely doing this out of the kindness of their heart, and not because they are being sued by 10,000 different groups, including other branches of the US Government.

The foia.state.gov website provides the documents via a paginated table interface. Each row links to individual PDFs of the documents. This interface supports basic searching and manual inspection of specific documents, but it's not amenable for analysis of text data en masse. I wasn't able to find a way to download the emails in bulk, which means we'll need to another way of getting all the PDFs.

It appears as if the emails were rendered as images, manually redacted by drawing boxes on them, then saved as a PDF and OCR'd.

My first instinct in a situation like this is to scrape the site using BeautifulSoup (http://www.crummy.com/software/BeautifulSoup/). But, by using Chrome's Develop Tools  (*: Firefox's would work just as well. IE or Safari, YMMV) I was able to find a shortcut. If we monitor what happens when the page loads in the Network tab, we see a call to a search service [01_AJAX_call.png]. Upon further inspection of the URL endpoint, it looks like a pretty standard RESTful query:

https://foia.state.gov/searchapp/Search/SubmitSimpleQuery?_dc=1443406695348&searchText=*&beginDate=false&endDate=false&collectionMatch=Clinton_Email&postedBeginDate=false&postedEndDate=false&caseNumber=false&page=1&start=0&limit=20

The astute reader may notice that the website only displays 20 search results at one time, and that the URL happens to include a 'limit=20' variable. If we increase that value to, oh, I dunno, say 17,000, and curl it from the command line:

$ curl 'https://foia.state.gov/searchapp/Search/SubmitSimpleQuery?_dc=1443406695348&searchText=*&beginDate=false&endDate=false&collectionMatch=Clinton_Email&postedBeginDate=false&postedEndDate=false&caseNumber=false&page=1&start=0&limit=99000' > search_result.out

we get a sweet, sweet JSON response! "High Five!" is totally what we would say to each other, if in fact that *was* a well formatted JSON response. But, any normal, self-respecting json parser is going to vomit all over itself because of sections like:

"docDate":new Date(1278043200000)

and

"docDate":new Date(-62135578800000)

The Dates aren't represented as Strings or as normal epoch integers, they're actually variables (WHAT IS THIS FORMAT CALLED? Some sort of javascript object dump?). Fortunately this is pretty fixable. I used Perl (which in modern developer terms is kind of like telling people, "I speak Coptic") to remove the parts I didn't want and create a parseable JSON document:

$  perl -p -e 's/new Date\((-?\d+)\)/$1/g' data/search_result.out > data/response.json

From here, it's pretty straightforward to write a python script that iterates over every record in the json and download the corresponding PDF:

```
code
```

To run it (and any of the other scripts), we'll want to create a virtualenv and install the requirements.txt:

Then, to launch the script:

(hrc-email)hrc-email $ python bin/download_hrc_pdfs.py -j data/response.json -o data/pdf

The above isn't particularly efficient and will likely take several hours to finish downloading all the emails.

It's worth mentioning that there are a few pdfs that share the same name. I spot checked a few of these and they appear to be identical documents that were (for reasons unknown to me) included in multiple monthly releases.

## Ingestion

My best guess is that the redaction process the State Department used went something like:

1) Print email chain
2) Scan printed email as image PDF
2) Draw boxes on the image to redact sensitive text
3) Print redacted email
4) Scan and OCR redacted email

So, the text information included in the PDF isn't the original text, it's (twice) scanned text. In order to analyze the PDFs, we'll need to extract the text component.

There are a lot of options available to this. I went with poppler [http://poppler.freedesktop.org/] because it includes a handy `Pdftotext` utility.

I installed poppler on my Mac w/ brew:
```
$ brew install poppler
```
And then wrote a simple bash script to run it against every PDF file we downloaded:
```
CODE
```
To run:
```
(hrc-email)hrc-email $ ./bin/extract_text_from_pdfs.sh ../../data/ data/text/
```

Recall that most of the "email" documents the State Department released are actually chains of email conversations that terminate with Hillary Clinton.

There's a lot of header and footer cruft that was added. We don't want to include this in our analysis, so let's strip it out:

(hrc-email)hrc-email $ ./bin/strip_statedept_headers.py -f 'data/text/*' -o data/strip_statedept_headers

Things to clean up still:
data/strip_statedept_headers/C05798118.txt:DIA/NRO/NGA,B5,B6

Now that we have each document in text form, we'll want to break them up into individual emails that were sent. To do this I'm leveraging code I got from the talon https://pypi.python.org/pypi/talon/1.0.2.

Who were the Top 10 most popular individuals in the dataset?
MATCH (n)-[r]-()  WITH n, COUNT(r) as c RETURN n, c ORDER BY c DESC LIMIT 10

Link to my Graph Gist
https://gist.github.com/agussman/1d755128d6e0f1928cfb

LOAD CSV WITH HEADERS FROM "https://raw.githubusercontent.com/agussman/hrc-email/master/data/neo4j_export.10k.csv" AS row
MERGE (From:EmailAddress { name: row.From})
MERGE (To:EmailAddress { name: row.To})
MERGE (From)-[r:EMAILED {timestamp: row.Sent}]->(To)

MATCH (m {name:"h"}) RETURN m;

MATCH (m)-[r]->(n)
WHERE m.name IN ["h", "mills, cheryl d", "mills, cheryl d ", "abedin, huma ", "abedin, huma", "h ", "h ", "h ", "'abedinh@state.gov'", "cheryl mills"]
AND n.name IN ["h", "mills, cheryl d", "mills, cheryl d ", "abedin, huma ", "abedin, huma", "h ", "h ", "h ", "'abedinh@state.gov'", "cheryl mills"]
RETURN m, r, n;

MATCH (m)-[r]->(n)
WHERE m.name IN ["h", "mills, cheryl d"]
AND n.name IN ["h", "mills, cheryl d"]
RETURN r;

MATCH (m)-[r]->(n)
WHERE m.name IN ["H", "Mills, Cheryl D", "Abedin, Huma <AbedinH@state.gov>"]
AND n.name IN ["H", "Mills, Cheryl D", "Abedin, Huma <AbedinH@state.gov>"]
RETURN r;

MATCH (FROM)-[r]-()  WITH FROM, COUNT(r) AS c RETURN FROM, c ORDER BY c DESC LIMIT 10


RELEASE IN PART B4,B5,B6

TEXT B6,B7(C),B7(E),B7(F),B6

re.sub(r'(\s*B\d(\([A-F]\))?,)*\s*B\d(\([A-F]\))?$', '', line)


def clean_and_enumerate(txt):
    """
    Generator to perform some basic REGEX cleaning on each line of text
    Strip trailing classification marks
    :param txt:
    :return:
    """
    for i, line in enumerate(txt):
        # Stagger these so they "cut down" to the next case
        # RELEASE IN PART B5 > RELEASE IN PART > RELEASE IN
        # Ending in B5 or B6 or B5,B6, etc
        line = re.sub(r'(\s*B\d,)?\s*B\d$', '', line)
        # Ending in FULL or PART
        yield i, line


def clean_and_enumerate(txt):
    for i, line in enumerate(txt):
        yield i, re.sub(r'o$', '', line)