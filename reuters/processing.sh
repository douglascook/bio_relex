#!/bin/bash
# This needs to be run from the Stanford NER folder, or maybe needs the classpaths fixed...

# don't use spaces!
FILES=/Users/Dug/Imperial/individual_project/code/reuters/stanford_input_ORIG/*
EXT=.out

# $ means you want to use the value of the variable
for f in $FILES
do
    #echo $f
    #echo $f$EXT
    java -Xmx2g -cp stanford-ner.jar edu.stanford.nlp.ie.crf.CRFClassifier -loadClassifier classifiers/english.all.3class.distsim.crf.ser.gz -textFile $f -outputFormat inlineXML >> $f$EXT 
done
