from nltk import text
import regex as re
import nltk
import Stemmer
import sys
from pprint import pprint
import json
import math
import os
import time

from regex.regex import split

# from regex.regex import split

if len(sys.argv) < 2:
    print("invalid number of arguments")
    exit()

STOP_WORDS = nltk.corpus.stopwords.words('english')
stemmer = Stemmer.Stemmer('english')

# INDEX_FOLDER = "."
QUERY_FILE = sys.argv[1]

f_num = open('./numdocs.txt' , 'r')
TOTAL_DOCS = int(f_num.readline().strip('\n'))
f_num.close()


title_file_names = [ele for ele in os.listdir("./titles")]
title_file_names[:] = sorted([(int(ele[6:-4]) , ele) for ele in title_file_names])
title_file_names[:] = [ele[1] for ele in title_file_names]

TITLE_FILES = [open("./titles/" + tname , 'r') for tname in title_file_names]
TITLES_DICT = {}


index_file_names = os.listdir("./my_index")
index_file_names[:] = sorted([(ele[11:-4] , ele) for ele in index_file_names])
index_file_names[:] = [ele[1] for ele in index_file_names]

INDEX_FILES = [open("./my_index/" + iname , 'r') for iname in index_file_names]





def load_file(tnum):
    cur_doc = 50000*(tnum-1)
    offset = 1
    fp = TITLE_FILES[tnum - 1]
    for title in fp.readlines()[:-1]:
        TITLES_DICT[cur_doc+offset] = title.strip('\n')
        offset += 1




# binary search
def get_location(fp , x):
    x = x.strip('\n')
    
    fp.seek(0,2)
    sz = fp.tell()
    if not x:
        return sz
    l = 0
    r = sz-1
    mid = 0
    while l < r:
        mid = (l + r)//2
        if mid > 0:
            fp.seek(mid-1)
            fp.readline()
            mid_f = fp.tell()
        else:
            mid_f = 0
            fp.seek(mid_f)
        
        line = fp.readline()
        line = line.rstrip('\n')
        if line:
            line = line[:line.find(":")]
        if not line or x <= line:
            if not line:
                r = mid
            else:
                if x == line:
                    return mid_f
                r = mid
        else:
            l = mid+1
        
    if mid == l:
        return mid_f
    
    if l <= 0:
        return 0
    
    fp.seek(l - 1)
    fp.readline()
    return fp.tell()



WEIGHTS = {
    "T": 20,
    "I": 5,
    "C": 3,
    "R": 0.2,
    "E": 0.2,
    "B": 1,
}

def isNum(c):
    return c >= '0' and c <= '9'

def isCapital(c):
    return c >= 'A' and c <= 'Z'


def clean_string(text_string):
        s = text_string
        s = s.strip()
    
        s = ' '.join(re.split("[^A-Za-z0-9]" , s))
        s = re.sub("[^A-Za-z0-9\s\t]" , "" , s)
        s = re.sub(r'[\s]+' , ' ', s)
        s = s.strip()
        return s


def get_tokens(text_string):
    s = clean_string(text_string)
    
    s_list = s.split(" ")
    s_list[:] = [ele for ele in s_list if len(ele) > 0]
    tokens = []
    for word in s_list:
        token = word.lower()
        token = stemmer.stemWord(token)
        tokens.append(token)

    return tokens

def get_field_tokens(text_string):
    split_inds = [ele.start() for ele in list(re.finditer("[tbicrl]:" , text_string))]
    split_list = []
    all_tokens = []
    for i in range(len(split_inds)):
        if i != len(split_inds) - 1:
            split_list.append((text_string[split_inds[i]:split_inds[i]+1].upper() , text_string[split_inds[i]+2:split_inds[i+1]]))
        else:
            split_list.append((text_string[split_inds[i]:split_inds[i]+1].upper() , text_string[split_inds[i]+2:]))

    for part in split_list:
        field = part[0]
        if field == 'L':
            field = 'E'
        
        query_string = clean_string(part[1])
        toks = get_tokens(query_string)
        for tok in toks:
            all_tokens.append((field , tok))

    return (all_tokens)


def process_line(line , field=None):
    doc_dict = {}
    posting = line[line.find(":")+1:]
    cur_doc = ""
    cur_freq = ""
    cur_query = ""
    reading_queries = False
    for i in range(len(posting)):
        if isCapital(posting[i]):
            if posting[i] != 'D':
                cur_query = posting[i]
            
        else:
            if reading_queries:
                cur_freq += posting[i]
            else:
                cur_doc += posting[i]
            
            if i == len(posting)-1 or (isCapital(posting[i+1])):
                if reading_queries:
                    cur_freq = int(cur_freq , 16)
                    if not field:
                        try:
                            doc_dict[cur_doc] += (WEIGHTS[cur_query] * cur_freq)
                        except:
                            doc_dict[cur_doc] = (WEIGHTS[cur_query] * cur_freq)
                    else:
                        if cur_query == field:
                            try:
                                doc_dict[cur_doc] += cur_freq
                            except:
                                doc_dict[cur_doc] = cur_freq

                else:
                    cur_doc = int(cur_doc , 16)
                    doc_dict[cur_doc] = 0
                    
                
                if i == len(posting)-1 or posting[i+1] == 'D':
                    cur_doc = ""
                    reading_queries = False
                else:
                    cur_freq = ""
                    reading_queries = True


    return doc_dict

def tf_idf(doc_dict_list):
    tf_idf_dict = {}
    cnt = 0
    for doc_dict in doc_dict_list:
        cnt += 1
        num_docs = len(list(doc_dict.keys()))
        term_idf = math.log(TOTAL_DOCS/num_docs)
        for doc in list(doc_dict.keys()):
            s = doc_dict[doc]
            
            term_tf = math.log(1+s)

            weight = term_tf * term_idf
            try:
                tf_idf_dict[doc] += weight
            except:
                tf_idf_dict[doc] = weight
    
    return tf_idf_dict
        




f_out = open("./queries_op.txt" , 'w')

f_queries = open(QUERY_FILE , 'r')

QUERY = f_queries.readline()

while QUERY:
    start_time = time.time()
    
    if QUERY.find(":") == -1:
        query_tokens = get_tokens(QUERY)
        doc_dict_list = []
        for tok in query_tokens:
            first = tok[0]
            first_ind = -1
            if not( first >= 'a' and first <= 'z'):
                first_ind = ord(first) - ord('0')
            else:
                first_ind = ord(first) - ord('a') + 10
            
            fp = INDEX_FILES[first_ind]
            loc = get_location(fp , tok)
            fp.seek(loc)
            line = fp.readline()
            doc_dict_list.append(process_line(line))
    else:
        query_tokens = get_field_tokens(QUERY)
        doc_dict_list = []
        for field_tok in query_tokens:
            tok = field_tok[1]
            field = field_tok[0]
            first = tok[0]
            first_ind = -1
            if not( first >= 'a' and first <= 'z'):
                first_ind = ord(first) - ord('0')
            else:
                first_ind = ord(first) - ord('a') + 10
            
            fp = INDEX_FILES[first_ind]
            loc = get_location(fp , tok)
            fp.seek(loc)
            line = fp.readline()
            doc_dict = process_line(line , field=field)
            doc_dict_list.append(doc_dict)

        

    tf_idf_dict = tf_idf(doc_dict_list)
    tf_idf_dict = {k: v for k, v in sorted(tf_idf_dict.items(), key=lambda item: item[1] , reverse=True)}
    top_docs = list(tf_idf_dict.keys())[:10]

    if(len(top_docs) == 0):
        f_out.write("No documents matched!" + '\n\n')
    else:
        loaded_title_files = set()
        for td in top_docs:
            quo = math.ceil(td/50000)
            if quo not in loaded_title_files:
                load_file(quo)
                loaded_title_files.add(quo)
            
            title = TITLES_DICT[td]
            f_out.write(str(td) + ", " + title.strip() + '\n')
        
        end_time = time.time()
        f_out.write(str(end_time - start_time) + '\n\n')
        print(QUERY.strip("\n ") , " DONE!")



    
    
    QUERY = f_queries.readline()


f_queries.close()
for f in INDEX_FILES:
    f.close()

for f in TITLE_FILES:
    f.close()

f_out.close()