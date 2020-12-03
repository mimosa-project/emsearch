from gensim import corpora, models, similarities
import re
import pickle

def search(search_word, count_top):
    variable_check = []
    variable_check_append = variable_check.append
    with open("symbol.txt", "r") as f:
        while True:
            l = f.readline()
            if not l:
                break 
            variable_check_append(re.sub("[\n]","",l))
    
    variable_number = []
    variable_number_append = variable_number.append
    variable_type = 0
    input_doc = search_word.split()
    input_doc_append = input_doc.append

    for i in range(len(input_doc)):
        if input_doc[i] not in variable_check:
            variable_number_append(input_doc[i])
            input_doc[i] = "___"
    
    variable_type = len(set(variable_number))
    input_doc_append(str(len(variable_number)))
    input_doc_append(str(variable_type))
    input_doc = [i for i in input_doc if i != ""]

    tfidf = models.TfidfModel.load('tfidf.model') 
    lsi = models.LsiModel.load('lsi_topics300.model')
    dictionary = corpora.Dictionary.load('search_dictionary.dict')

    index = similarities.MatrixSimilarity.load('lsi_index.index')

    query_vector = dictionary.doc2bow(input_doc)

    vec_lsi = lsi[tfidf[query_vector]]
    sims = index[vec_lsi]
    
    sims = sorted(enumerate(sims), key=lambda item: -item[1])
    result = []
    result_append = result.append

    with open("tell.pkl", "rb") as f:
        tell = pickle.load(f)

    for idx in sims[:count_top:]:
        search_result = {}
        with open("dictionary_abs.txt", "rb") as f:
            f.seek(tell[idx[0]])
            doc_list = f.read(tell[idx[0]+1]-tell[idx[0]]-2).decode('utf-8').split() # -2は改行文字を除くため

        if doc_list[0] == "theorem":
            # doc_list[0] : theorem or definition
            #         [1] : line
            #         [2] : file_name
            #         [3] : label
            #         [4::] : text
            search_result["label"] = (doc_list[3])
            search_result["text"] = (" ".join(doc_list[4::]))
            search_result["relevance"] = (idx[1])
            search_result["filename"] = (doc_list[2])
            search_result["line_no"] = (doc_list[1])
        else:
            # doc_list[0] : theorem or definition
            #         [1] : line
            #         [2] : file_name
            #         [3:5] : label
            #         [5::] : text
            search_result["label"] = (doc_list[3:5])
            search_result["text"] = (" ".join(doc_list[5::]))
            search_result["relevance"] = (idx[1])
            search_result["filename"] = (doc_list[2])
            search_result["line_no"] = (doc_list[1])
        result_append(search_result)
    
    return result