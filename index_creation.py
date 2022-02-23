
import xml.sax
import regex as re
import nltk
from pprint import pprint
from collections import OrderedDict
import os
import sys
import Stemmer
import heapq
import time

start_time = time.time()

if len(sys.argv) != 3:
    print("invalid number of arguments" , flush=True)
    exit()

XML_FILE = sys.argv[1]
INDEX_FILES_DIR = sys.argv[2]

if(not os.path.exists(INDEX_FILES_DIR)): os.mkdir(INDEX_FILES_DIR)
if(not os.path.exists("./index_blocks")): os.mkdir("./index_blocks")

#title of docs
f_titles = open('./doc_titles.txt' , 'w')

# Regex for different sections  , stop words and stemmer
APOSTROPHE_PATTERN = "([a-zA-Z0-9])(\')([a-zA-Z0-9])"

CATEGORY_PATTERN = r"\[\[Category:(.*?)\]\]"

REF_PATTERN = "=+References=+"
LINK_PATTERN = r"=+\s*External links?\s*=+"
URL_PATTERN = r"\[[a-z]+[:.].*?(?=\s)"

STOP_WORDS = nltk.corpus.stopwords.words('english')
STOP_WORDS.extend(['reflist' , 'refend' , 'ref' ,  'jpg' , 'png'])
stemmer = Stemmer.Stemmer('english')

# parser to count pages
class PageCounter(xml.sax.ContentHandler):
    def __init__(self):
        self.cur_page = 0
    
    def startElement(self, tag, attrs):
        if tag == "page":
            self.cur_page = self.cur_page + 1
        
    def characters(self, content):
        pass

    def endElement(self, tag):
        pass


counter_parser = xml.sax.make_parser()

# turning off namespaces
counter_parser.setFeature(xml.sax.handler.feature_namespaces , 0)

counter_handler = PageCounter()
counter_parser.setContentHandler(counter_handler)

counter_parser.parse(XML_FILE)

# Total pages and number of pages per block
PAGE_COUNT = counter_handler.cur_page
PAGE_LIMIT = 10000
print("pages -> " , PAGE_COUNT , flush=True)


# main handler for the xml parser
class MainHandler(xml.sax.ContentHandler):
    def __init__(self):
        self.currentTag = ""
        self.title = []
        self.text = []
        self.cur_page = 0

        self.stem_cache = {}
        self.unprocessed = {}
        self.cur_row = {}
        self.cur_infobox_indices = []
        self.cur_dict = {}
        self.cur_block = 0
    

    def clean_title(self , title_string):
        s = title_string
        s = re.sub(r'\n' , ' ' , s)
        s = re.sub(r'[\s]+' , ' ', s)
        s = s.strip()
        #store title
        f_titles.write(s + '\n')

        s = ' '.join(re.split("[^A-Za-z0-9]" , s))
        s = re.sub("[^A-Za-z0-9\s\t]" , "" , s)
        s = re.sub(r'[\s]+' , ' ', s)
        s = s.strip()
        return s
    
    def tokenize_title(self , title_string):
        s = title_string
        s = s.lower()
        s_list = s.split(" ")
        for t in s_list:
            self.unprocessed[t] = 1
        s_list[:] = [ele for ele in s_list if ele not in STOP_WORDS]

        for i in range(len(s_list)):
            try:
                s_list[i] = self.stem_cache[s_list[i]]
            except:
                self.stem_cache[s_list[i]] = stemmer.stemWord(s_list[i])
                s_list[i] = self.stem_cache[s_list[i]]
        
        return s_list
    
    def clean_string(self , text_string):
        s = text_string
        s = s.strip()
        
        s = re.sub(r'https?:\/\/\S+' , '' , s)
        s = ' '.join(re.split("[^A-Za-z0-9]" , s))
        s = re.sub("[^A-Za-z0-9\s\t]" , "" , s)
        s = re.sub(r'[\s]+' , ' ', s)
        s = s.strip()
        return s

    def tokenize_string(self , text_string):
        s = text_string
        s = s.lower()
        s_list = s.split(" ")
        for t in s_list:
            self.unprocessed[t] = 1
        s_list[:] = [ele for ele in s_list if ele not in STOP_WORDS]
        for i in range(len(s_list)):
            try:
                s_list[i] = self.stem_cache[s_list[i]]
            except:
                self.stem_cache[s_list[i]] = stemmer.stemWord(s_list[i])
                s_list[i] = self.stem_cache[s_list[i]]
        
        return s_list

    def remove_extra_whitespaces(self , text_string):
        s = text_string
        s = re.sub(r'\n' , ' ' , s)
        s = re.sub(r'[\s]+' , ' ', s)
        s = s.strip()
        return s
    
    def get_double_brackets_end(self , start_ind , s):
        cnt = 2
        cur = start_ind+2
        while cnt > 0 and cur < len(s):
            if s[cur] == '}':
                cnt -= 1
            elif s[cur] == '{':
                cnt += 1
            
            cur += 1
                
        return cur
    
    def get_infoboxes(self , text_string):
        s = text_string
        infboxes_list = []
        cur_start = 0
        while 1:
            ind = s[cur_start:].find("{{Infobox")
            if ind == -1:
                break
            ind += cur_start
            
            end_ind = self.get_double_brackets_end(ind , s)
            self.cur_infobox_indices.append((ind , end_ind))
            extracted_string = s[ind+9:end_ind-2]
            infboxes_list.append(extracted_string)
            cur_start = end_ind
            if cur_start >= len(s):
                break
        
        return infboxes_list
    
    def tokenize_infoboxes(self , infobox_list):
        infobox_string = ""
        for cur in infobox_list:
            cur_list = cur.split(" |")
            infobox_string += cur_list[0]
            
            for key_val in cur_list[1:]:
                
                eq_ind = key_val.find("=")
                if eq_ind != -1:
                    infobox_string += " "
                    infobox_string += key_val[eq_ind+1:]

            infobox_string += " "
        
        infobox_string = self.clean_string(infobox_string)
        infobox_tokens = self.tokenize_string(infobox_string)

        return infobox_tokens
    
    def tokenize_categories(self , text_string):
        s = text_string
        cat_list = []
        all_cats = re.findall(CATEGORY_PATTERN , s)
        cat_list.extend(all_cats)

        cat_string = " ".join(cat_list)

        cat_string = self.clean_string(cat_string)
        cat_tokens = self.tokenize_string(cat_string)

        return cat_tokens
    

    def get_section_string(self , text_string , pattern):

        s = text_string
        stop_pattern = CATEGORY_PATTERN + "|" + " =+([a-zA-Z0-9\s]+?)=+ "
        ind = re.search(pattern , s)
        sect_string = ""
        if ind:
            ind = ind.end()
            stop_ind = re.search(stop_pattern , s[ind:])
            if stop_ind:
                stop_ind = stop_ind.start()
                stop_ind += ind
            else:
                stop_ind = len(s)
            
            sect_string = s[ind:stop_ind]
        
        return sect_string

    def tokenize_references(self , text_string):
        reference_string = self.get_section_string(text_string , REF_PATTERN)
        parsed_string = ""
        
        if(len(reference_string) > 0):
            list_ind = reference_string.find("*")
            if list_ind != -1:
                parsed_string += reference_string[list_ind:]
        
        parsed_string = self.clean_string(parsed_string)
        reference_tokens = self.tokenize_string(parsed_string)

        return reference_tokens
    

    def tokenize_external_links(self , text_string):

        link_string = self.get_section_string(text_string , LINK_PATTERN)
        parsed_string = ""

        if(len(link_string) > 0):
            list_ind = link_string.find("*")
            if list_ind != -1:
                parsed_string += link_string[list_ind:]
        
        parsed_string = self.clean_string(parsed_string)
        link_tokens = self.tokenize_string(parsed_string)

        return link_tokens
    

    def tokenize_body(self , text_string):
        s = text_string
        s_cleaned = []
        body_string = ""
        st = 0
        for start_end in self.cur_infobox_indices:
            if st != start_end:
                s_cleaned.append(s[st:start_end[0]])
            st = start_end[1]
        
        if st != len(s):
            s_cleaned.append(s[st:len(s)])


        s = ''.join(s_cleaned)

        filter_pattern = LINK_PATTERN + "|" + REF_PATTERN + "|" + CATEGORY_PATTERN + "|" + "=+See also=+" + "|" + "=+Notes=+"
        found_ind = re.search(filter_pattern , s)
        if found_ind:
            found_ind = found_ind.start()
        else:
            found_ind = len(s)
        
        s = s[:found_ind]

        body_string = s

        body_string = self.clean_string(body_string)
        body_tokens = self.tokenize_string(body_string)

        return body_tokens
    
    def validToken(self , tok):
        if len(tok) == 0:
            return False
        
        return True
        
            

    def startElement(self, tag, attrs):
        self.currentTag = tag
        if tag == "page":
            self.cur_page = self.cur_page + 1

    def characters(self, content):
        if self.currentTag == "title":
            self.title.append(' ')
            self.title.append(content)
        elif self.currentTag == "text":
            self.text.append(' ')
            self.text.append(content)

    def endElement(self, tag):
        if tag == 'page':
            # saving in dictionary

            for k in list(self.cur_row.keys()):
                for tok in self.cur_row[k]:
                    if not self.validToken(tok):
                        continue
                    try:
                        self.cur_dict[tok][self.cur_page][k] += 1
                    except:
                        try:
                            self.cur_dict[tok][self.cur_page][k] = 1
                        except:
                            try:
                                self.cur_dict[tok][self.cur_page] = {}
                                self.cur_dict[tok][self.cur_page][k] = 1
                            except:
                                self.cur_dict[tok] = {}
                                self.cur_dict[tok][self.cur_page] = {}
                                self.cur_dict[tok][self.cur_page][k] = 1


                        
            if self.cur_page == PAGE_COUNT or self.cur_page%PAGE_LIMIT == 0:
                # write to a block
                self.cur_block += 1

                file_name = "./index_blocks/Block_{}.txt".format(self.cur_block)
                
                ordered_dict = OrderedDict(sorted(self.cur_dict.items()))

                fp = open(file_name , 'w')

                cur_line_string = ""
                for token in list(ordered_dict.keys()):
                    cur_line_string = ""
                    cur_line_string += (token + ":")
                    for doc in ordered_dict[token]:
                        cur_line_string += ("D" + hex(doc)[2:])
                        for query in ordered_dict[token][doc]:
                            if query != "Full Text":
                                cur_line_string += (query.upper()[0] + hex(ordered_dict[token][doc][query])[2:])
                        

                    cur_line_string += "\n"
                    fp.write(cur_line_string)
                
                fp.close()

                self.cur_dict = {}
                
        elif tag == 'title':
            title_string = ''.join(self.title)
            self.title = []
            title_string = self.clean_title(title_string)
            title_tokens = self.tokenize_title(title_string)
            self.cur_row['Title'] = title_tokens

        elif tag == "text":
            text_string = ''.join(self.text)
            self.text = []
            
            text_string = self.remove_extra_whitespaces(text_string)

            all_tokens = []
            all_tokens.extend(self.cur_row['Title'])

            #Infobox
            infobox_list = self.get_infoboxes(text_string)
            infobox_tokens = self.tokenize_infoboxes(infobox_list)
            all_tokens.extend(infobox_tokens)
            self.cur_row['Infobox'] = infobox_tokens

            #Caetgories
            category_tokens = self.tokenize_categories(text_string)
            all_tokens.extend(category_tokens)
            self.cur_row['Categories'] = category_tokens

            #References
            reference_tokens = self.tokenize_references(text_string)
            all_tokens.extend(reference_tokens)
            self.cur_row["References"]  = reference_tokens

            #External Links
            external_link_tokens = self.tokenize_external_links(text_string)
            all_tokens.extend(external_link_tokens)
            self.cur_row["External Links"] = external_link_tokens

            #Body
            body_tokens = self.tokenize_body(text_string)
            all_tokens.extend(body_tokens)
            self.cur_row['Body'] = body_tokens

            self.cur_infobox_indices = []

            #Full text
            self.cur_row['Full Text'] = all_tokens
        

main_parser = xml.sax.make_parser()

# turning off namespaces
main_parser.setFeature(xml.sax.handler.feature_namespaces , 0)

main_handler = MainHandler()
main_parser.setContentHandler(main_handler)

main_parser.parse(XML_FILE)


f_titles.close()






## MERGING BLOCK FILES AND RESDISTRIBUTING AS LETTER FILES
## -------------------------------------------------------------------------------------------------------------------------------------------##
## -------------------------------------------------------------------------------------------------------------------------------------------##

class IndexLine:
    def __init__(self , token , text , block):
        self.token = token
        self.text = text
        self.block = block
    
    def __lt__(self ,  nxt):
        if self.token != nxt.token:
            return self.token < nxt.token
        else:
            return self.block < nxt.block

## MERGING THE BLOCKS TO FORM ONE FILE ##

block_files = os.listdir('./index_blocks')
block_files[:] = [(int(ele[6: ele.find(".")]) , ele) for ele in block_files]
block_files[:] = sorted(block_files)
block_files[:] = [ele[1] for ele in block_files]
block_files[:] = [open("./index_blocks/" + ele , 'r') for ele in block_files]


def get_first(s):
    c = s[0]
    return c

def get_line(file_num):
    f = block_files[file_num]
    line = f.readline().strip('\n')
    if line:
        tok = line[:line.find(":")]
        text = line[line.find(":")+1:]
        i = file_num
        return IndexLine(tok , text , i)
    else:
        return None
    

HEAP = []

for file_num in range(len(block_files)):
    line_obj = get_line(file_num)
    heapq.heappush(HEAP , line_obj)

index_files = [open(INDEX_FILES_DIR + "/index_" + alphabet + '.txt' , 'w+') for alphabet in "0123456789abcdefghijklmnopqrstuvwxyz"]

while len(HEAP):
    top_line = HEAP[0]
    cur_merged = ""

    while len(HEAP) and top_line.token == HEAP[0].token:
        cur_merged += HEAP[0].text
        file_num = HEAP[0].block
        heapq.heappop(HEAP)

        next_word = get_line(file_num)

        if next_word:
            heapq.heappush(HEAP , next_word)
    

    cur_merged = top_line.token + ":" + cur_merged
    file_no = get_first(top_line.token)
    if file_no >= '0' and file_no <= '9':
        index_files[ord(file_no) - ord('0')].write(cur_merged)
        index_files[ord(file_no) - ord('0')].write("\n")
    else:
        index_files[ord(file_no) - ord('a') + 10].write(cur_merged)
        index_files[ord(file_no) - ord('a') + 10].write('\n')


for f in index_files:
    f.close()

end_time = time.time()