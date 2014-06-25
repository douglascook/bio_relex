import nltk
import csv  # used for accessing data held in CSV format
import os.path  # need this to use relative filepaths
import sys  # using sys for std out
import re

import preprocessing

import nltk.tokenize.punkt as punkt


def collate_texts():
    """
    Create one record per text fragment, with lists for all drugs and companies
    Only keep those texts that mention at least one of the drugs and one of the companies
    """

    # set filepath to input
    basepath = os.path.dirname(__file__)
    file_in = 'data/reuters/press_releases/PR_drug_company_500.csv'
    file_in = os.path.abspath(os.path.join(basepath, '..', '..', file_in))
    file_out = os.path.abspath(os.path.join(basepath, '..', 'reuters_new/single_records_clean.csv'))

    with open(file_in, 'rb') as csv_in:
        with open(file_out, 'wb') as csv_out:
            csv_reader = csv.DictReader(csv_in, delimiter=',')
            csv_writer = csv.writer(csv_out, delimiter=',')

            drugs = set([])
            companies = set([])
            src = '174077'
            text = ''

            csv_writer.writerow(['SOURCE_ID', 'DRUGS', 'COMPANIES', 'FRAGMENT'])

            # think that the dict reader skips header row automagically
            for row in csv_reader:
                if row['SOURCE_ID'] != src:

                    # first check if the text contains at least on of each drug and company tagged
                    d_relevant = False
                    c_relevant = False
                    for d in drugs:
                        if d in text:
                            d_relevant = True
                            break

                    if d_relevant:
                        for c in companies:
                            if c in text:
                                c_relevant = True
                                break

                    if d_relevant and c_relevant:
                        csv_writer.writerow([src, list(drugs), list(companies), nltk.clean_html(text)])

                    # reset lists
                    drugs = set([])
                    companies = set([])

                # append drugs and companies to lists
                drugs.add(row['DRUG_NAME'])
                companies.add((row['COMPANY_NAME']))
                src = row['SOURCE_ID']
                text = row['FRAGMENT']


def clean_and_tag_all():
    """ Create new CSV containing tagged versions of all sentences """

    # set filepath to input
    basepath = os.path.dirname(__file__)
    file_in = os.path.abspath(os.path.join(basepath, '..', 'reuters_new/single_records.csv'))
    file_out = os.path.abspath(os.path.join(basepath, '..', 'reuters_new/sentences_POS.csv'))

    # set up sentence splitter with custom parameters
    punkt_params = punkt.PunktParameters()
    # sentences are not split ending on the given parameters, using {} creates a set literal
    punkt_params.abbrev_types = {'inc', '.tm', 'tm', 'no', 'i.v', 'dr', 'drs', 'u.s', 'u.k', 'ltd', 'vs', 'vol', 'corp',
                                 'jan', 'feb', 'mar', 'apr', 'jun', 'jul', 'aug', 'sep', 'sept', 'oct', 'nov', 'dec',
                                 'pm', 'p.m', 'am', 'a.m', 'mr', 'mrs', 'ms', 'i.e'}
    # the tokenizer has to be unpickled so better do it once here than every time it is used
    sentence_splitter = punkt.PunktSentenceTokenizer(punkt_params)

    with open(file_in, 'rb') as csv_in:
        with open(file_out, 'wb') as csv_out:
            csv_reader = csv.DictReader(csv_in, ['SOURCE_ID', 'DRUGS', 'COMPANIES', 'SENTENCE'], delimiter=',')
            csv_writer = csv.DictWriter(csv_out, ['SOURCE_ID', 'SENT_NUM', 'SENTENCE', 'NO_PUNCT',
                                                  'DRUGS', 'COMPANIES', 'POS_TAGS'], delimiter=',')
            csv_writer.writeheader()

            for row in csv_reader:
                # use stdout to avoid spaces and newlines
                sys.stdout.write('.')
                # need to flush the buffer to display immediately
                sys.stdout.flush()

                # clean up html tags
                plaintext = nltk.clean_html(row['SENTENCE'])
                # this in particular seems to be screwing up some of the sentence splitting
                plaintext = plaintext.replace('Inc .', 'Inc.')
                # split into sentences
                sentences = sentence_splitter.tokenize(plaintext)

                if len(sentences) > 0:
                    for i, s in enumerate(sentences):

                        # need to do the NE recognition before removing punctuation
                        # TODO integrate stanford output into this
                        # tokens = nltk.word_tokenize(s)
                        # tags = nltk.pos_tag(tokens)
                        #ne_chunks = nltk.ne_chunk(tags, binary=True)

                        # want to keep hyphenated words but none of the other hyphens
                        # replace any hyphenated words' hyphens with underscores
                        for hyphen in re.findall(r'\w-\w', s):
                            underscore = hyphen.replace('-', '_')
                            s = s.replace(hyphen, underscore)

                        # remove punctuation, still want to add original sentence to CSV though
                        #no_punct = re.findall(r'[\w\$\xc2()-]+', s)
                        no_punct = re.findall(r'[\w\$\xc2_]+', s)
                        no_punct = ' '.join(no_punct)
                        # put the hyphens back
                        s = s.replace('_', '-')

                        tokens = nltk.word_tokenize(no_punct)
                        tags = nltk.pos_tag(tokens)

                        # put the hyphens back after tokenisation so tokens turn out better
                        no_punct = no_punct.replace('_', '-')

                        # TODO parse tree info, something to do with stemming?
                        # ignore any rogue bits of punctuation etc
                        if len(tags) > 1:
                            # write row to file for each sentence
                            new_fields = {'SENT_NUM': i, 'SENTENCE': s, 'NO_PUNCT': no_punct, 'POS_TAGS': tags}
                            row.update(new_fields)
                            csv_writer.writerow(row)

    print 'Written to sentences_POS.csv'


def drug_and_company_entities():
    """
    Locate named drugs and companies, indexed by word
    """

    # set filepath to input
    basepath = os.path.dirname(__file__)
    file_in = os.path.abspath(os.path.join(basepath, '..', 'reuters_new/sentences_POS.csv'))
    file_out = os.path.abspath(os.path.join(basepath, '..', 'reuters_new/entities_marked.csv'))

    with open(file_in, 'rb') as csv_in:
        with open(file_out, 'wb') as csv_out:
            csv_reader = csv.DictReader(csv_in, delimiter=',')
            csv_writer = csv.DictWriter(csv_out, ['SOURCE_ID', 'SENT_NUM', 'SENTENCE', 'DRUGS', 'COMPANIES',
                                                  'POS_TAGS'], delimiter=',')
            csv_writer.writeheader()

            for row in csv_reader:
                tags = eval(row['POS_TAGS'])
                # find indices for drugs and companies mentioned in the row
                drug_dict = entity_indices(eval(row['DRUGS']), tags)
                comp_dict = entity_indices(eval(row['COMPANIES']), tags)
                row.update({'DRUGS': drug_dict})
                row.update({'COMPANIES': comp_dict})

                # remove this field, think pop is the only way to do it
                row.pop('NO_PUNCT')
                csv_writer.writerow(row)

    print 'Written to entities_marked.csv'


def entity_indices(entities, tags):
    """
    Given entities return indices in tags where their first words are found
    Return dictionary with entities as keys and indices as values
    """

    entity_dict = {}

    for entity in entities:
        # TODO fix this method, sometimes first word makes sense but sometimes identifies incorrect entities
        # locate first word if entity is made of multiple words
        space = entity.find(' ')
        if space > 0:
            head_word = entity[:space]
        else:
            head_word = entity
        # underscores are used in the tokens so need to replace before searching
        if head_word.find('-') > 0:
            head_word = head_word.replace('-', '_')

        # add indices of head word to dict entry for this drug
        # TODO does casting everything as lower case give correct results?
        #indices = [i for i, x in enumerate(tags) if x[0].lower() == head_word.lower()]
        indices = [i for i, x in enumerate(tags) if x[0] == head_word]
        if len(indices) > 0:
            entity_dict[entity] = indices

    return entity_dict


def stanford_entity_recognition():
    """
    Produce NE chunks from POS tags - this uses the Stanford tagger implementation
    This is actually too slow to be of any use, there must be a way to batch it but for now just using bash script
    """

    # set filepath to input
    basepath = os.path.dirname(__file__)
    file_in = os.path.abspath(os.path.join(basepath, '..', 'reuters_new/sentences_POS.csv'))
    file_out = os.path.abspath(os.path.join(basepath, '..', 'reuters_new/sentences_NE.csv'))

    # set up tagger
    st = nltk.tag.stanford.NERTagger(
        '/Users/Dug/Imperial/individual_project/tools/stanford_NLP/stanford-ner-2014-06-16/classifiers/english.all.3class.distsim.crf.ser.gz',
        '/Users/Dug/Imperial/individual_project/tools/stanford_NLP/stanford-ner-2014-06-16/stanford-ner.jar')

    with open(file_in, 'rb') as csv_in:
        with open(file_out, 'wb') as csv_out:
            csv_reader = csv.DictReader(csv_in, delimiter=',')
            csv_writer = csv.writer(csv_out, delimiter=',')

            # write column headers on first row
            csv_writer.writerow(['SOURCE_ID', 'SENTENCE', 'DRUGS', 'COMPANIES', 'POS_TAGS', 'NE_CHUNKS'])

            for row in csv_reader:
                ne_chunks = st.tag(row['NO_PUNCT'].split())
                csv_writer.writerow([row['SOURCE_ID'], row['SENTENCE'], row['DRUGS'], row['COMPANIES'],
                                     row['POS_TAGS'], ne_chunks])

    print 'Written to sentences_NE.csv'


def nltk_entity_recognition():
    """
    Produce NE chunks from POS tags - this NLTK implementation is not great though so should use Stanford output instead
    This needs to be done before the punctuation is removed
    """

    # set filepath to input
    basepath = os.path.dirname(__file__)
    file_in = os.path.abspath(os.path.join(basepath, '..', 'reuters_new/sentences_POS.csv'))
    file_out = os.path.abspath(os.path.join(basepath, '..', 'reuters_new/sentences_NE.csv'))

    with open(file_in, 'rb') as csv_in:
        with open(file_out, 'wb') as csv_out:
            csv_reader = csv.DictReader(csv_in, delimiter=',')
            csv_writer = csv.writer(csv_out, delimiter=',')

            # write column headers on first row
            csv_writer.writerow(['SOURCE_ID', 'SENTENCE', 'DRUGS', 'COMPANIES', 'POS_TAGS', 'NE_CHUNKS'])

            for row in csv_reader:
                print row
                # use NLTK NE recognition, binary means relations are not classified
                # it's based on the ACE corpus so may not work completely as desired...
                tags = eval(row['POS_TAGS'])
                ne_chunks = nltk.ne_chunk(tags, binary=True)
                row.append(ne_chunks)
                csv_writer.writerow(row)
                # csv_writer.writerow([row['SOURCE_ID'], row['SENTENCE'], row['DRUGS'], row['COMPANIES'],
                # row['POS_TAGS'], ne_chunks])


if __name__ == '__main__':
    #collate_texts()
    #clean_and_tag_all()
    drug_and_company_entities()
    #stanford_entity_recognition()
