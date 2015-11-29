#!/bin/bash -e

#
# extract_text_from_pdfs.sh <dir of pdfs> <output dir>
#

PDF_DIR=$1
OUT_DIR=$2

if ! [[ -d $PDF_DIR && -d $OUT_DIR ]]; then
    echo "RUN AS: extract_text_from_pdfs.sh <dir of pdfs> <output dir>"
    exit 1
fi

for i in `find $PDF_DIR -name '*.pdf' -maxdepth 1`; do
    echo $i
    BASE=`basename $i .pdf`
    Pdftotext -layout $i $OUT_DIR/$BASE.txt
done