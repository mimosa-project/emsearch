from gensim import corpora, models, similarities
from parse_abs import is_variable, processing_variables_with_emparser
import re
import pickle
from collections import defaultdict

def search(search_word, count_top):

    search_word = search_word.replace(",", " ")
    search_word = search_word.replace(";", "")
    input_doc = processing_variables_with_emparser(search_word.split())
    input_doc = input_doc.split()

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

    for idx in sims[:count_top]:
        search_result = {}
        with open("abs_dictionary.txt", "rb") as f:
            f.seek(tell[idx[0]])
            doc_list = f.read(tell[idx[0]+1]-tell[idx[0]]-2).decode('utf-8').split() # -2は改行文字を除くため

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

        result_append(search_result)
    
    return result