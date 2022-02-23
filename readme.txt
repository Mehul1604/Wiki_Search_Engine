INDEX CREATION
script => index_creation.py

    PARSING
    - Characters are read from the title as well as the text tags in the xml and read into a string buffer
    - After each document is done , the read buffer is then cleaned
        - Punctuation is removed
        - Tokenized by spaces
        - Lowercased
        - Stop words removed
        - Stemmed using Pystemmer
    - The tokens are divided separately according to the fields (title,body,categories,referecnes,external links,infobox)
    - All the tokens are stored with the information about their document and the field they belong to in a Dictionary
    
    INITIAL_DIVISION
    - Total number of documents are 21384756
    - After 10000 documents are read , the processed Dictionary is dumped into a block file
    
    MERGING , SORTING AND ALPHABETICAL DIVISION
    - These block files are now merged again using the SPIMI (single pass in memory indexing) algorithm
    - During the merging , each of the tokens are put into separate files according to their first character
        - Example - index_file_a.txt , index_file_2.txt
    
    - Index is stored as 36 separate files
        - 10 files for characters 0 to 9
        - 26 for the alphabet
    
    - Format of posting list
        T - title , B - Body , I - infobox , C - categories , R - references , E - external links
        <token>:D<doc_id in hexadecimal>T<title frequency>B<body frequency in hexadecimal>.. and so on
        Eg. apple:D2e43T3B6I4f

SEARCH
script => search.py

    TOKEN SEARCH
    - The query is broken down into individual tokens (similar cleaning and stemming)
    - The appropriate file is accessed according to the first character of the token
    - A binary search is performed on the file
        - The file pointer is taken to the mid pointer
        - Then readline() is called to make sure it is at the starting of the linkreports
        - Complexity - O(log(size of file in bytes))
    - For each term and in each document , the term frequency is calculated using the following weights for differet fields -
        {
            "T": 20.5,
            "I": 5.5,
            "C": 2,
            "R": 0.8,
            "E": 0.8,
            "B": 1,
        }
    - Inverse document frequency is calculated as (Total number of documents) / (Number of documents the term is in (number of capital 'D's in the posting))
    - tf-idf weight is log_e(1 + term frequency) * log_e(Inverse document frequency)
    - For each document the sum of tf-idf weights of all query tokens is obtained
    - The documents are ranked in descending order according to these values and top 10 are taken

    - The titles are laoded through separate files

OTHER FILES/FOLDERS

    stats.txt
        - Size of index in Gb (20)
        - Number of inidex files split (36)
        - Total number of tokens (38082689)
    
    numdocs.txt
        - Only one line - number of total documents



    

