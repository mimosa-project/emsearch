import os
from emparser.preprocess import Lexer
import re
import pickle

DATA_DIR = '/mnt/c/emparser/build/lib.linux-x86_64-3.6/emparser/data' # 適宜変更
MML_VCT = os.path.join(DATA_DIR, 'mml.vct')

lexer = Lexer()
lexer.load_symbol_dict(MML_VCT)
lexer.build_len2symbol()

path = "./abstr"
files = os.listdir(path)
files_file = [f for f in files if os.path.isfile(os.path.join(path, f))]
files_file.sort()

variable_check = []
with open("symbol.txt", "r") as f:
    while True:
        l = f.readline()
        if not l:
            break 
        variable_check.append(re.sub("[\n]","",l))

variable_number = []
variable_type = 0

for number_files_file in range(len(files_file)):
    with open("dictionary_abs.txt", "a") as file_dictionary_abs:
        with open("./abstr/"+files_file[number_files_file], "r") as name_file:
            definition_flag = 0
            theorem_flag = 0
            count_line = 0
            count_definition = 0
            definition_count_line = 0
            theorem_count_line = 0
            theorem_count_comment = 0
            common_definition = []
            value_definition = []
            while True:
                count_line += 1   
                read_name_file = name_file.readline()
                if not read_name_file:
                    break
                read_name_file_split = read_name_file.split()
                for number_read_name_file in range(len(read_name_file_split)):
                    if read_name_file_split[number_read_name_file] == "::" and number_read_name_file==0 and definition_flag == 0 and theorem_flag == 0:
                        break
                    elif read_name_file_split[number_read_name_file] == "theorem" and number_read_name_file == 0:
                        theorem_flag = 1
                        file_dictionary_abs.write("theorem ")
                        file_dictionary_abs.write(str(count_line))
                        file_dictionary_abs.write(" ")
                        file_dictionary_abs.write(str(files_file[number_files_file]))
                        file_dictionary_abs.write(" ")
                        theorem_count_line = count_line
                    elif theorem_flag == 1:
                        if read_name_file_split[number_read_name_file] == "::":
                            if theorem_count_line != count_line:
                                break
                            else:
                                theorem_count_comment += 1
                            continue
                        if theorem_count_comment >= 2 and theorem_count_line == count_line:
                            theorem_count_comment = 0
                            break
                        if theorem_count_line != count_line:
                            file_dictionary_abs.write(" ")
                        file_dictionary_abs.write(read_name_file_split[number_read_name_file])
                        if theorem_count_line != count_line:
                            file_dictionary_abs.write(" ")
                        if ";" in read_name_file_split[number_read_name_file]:
                            file_dictionary_abs.write("\n")
                            theorem_flag = 0
                            theorem_count_comment = 0
                    elif read_name_file_split[number_read_name_file] == "definition" and number_read_name_file == 0:
                        definition_flag = 1
                    elif definition_flag == 1:
                        if read_name_file_split[number_read_name_file] == "end;":
                            definition_flag = 0
                            count_definition = 0
                            common_definition = []
                            value_definition = []
                            break
                        if read_name_file_split[number_read_name_file] == ":::":
                            break
                        if count_definition == 0 and read_name_file_split[number_read_name_file] != "::" and read_name_file_split[number_read_name_file] != "":
                            common_definition.append(read_name_file[:-1])
                            value_definition = []
                            break
                        elif count_definition == 1 and read_name_file[-2] != ";" and read_name_file != "":
                            value_definition.append(read_name_file[:-1])
                            break
                        elif read_name_file_split[number_read_name_file] == "::" and count_definition == 0 and read_name_file != "":
                            count_definition = 1
                            definition_count_line = count_line
                            value_definition.append(read_name_file[:-1].split("::")[1])
                            if len(common_definition) >= 1:
                                value_definition.append(common_definition.pop())
                            break
                        elif read_name_file[-2] == ";"  and count_definition == 1 and read_name_file != "":
                            value_definition.append(read_name_file[:-1])
                            count_definition = 0
                            file_dictionary_abs.write("definition ")
                            file_dictionary_abs.write(str(definition_count_line))
                            file_dictionary_abs.write(" ")
                            file_dictionary_abs.write(str(files_file[number_files_file]))
                            file_dictionary_abs.write(" ")
                            file_dictionary_abs.write(value_definition[0][2:])
                            file_dictionary_abs.write(" ")
                            definition_count_line = count_line
                            for i in range(len(common_definition)):
                                file_dictionary_abs.write(common_definition[i])
                                file_dictionary_abs.write(" ")
                            for i in range(1,len(value_definition)):
                                file_dictionary_abs.write(value_definition[i])
                                file_dictionary_abs.write(" ")
                            file_dictionary_abs.write("\n")
                            break

with open("parsed_abs.txt", "w") as file_parsed_abs:
    with open("dictionary_abs.txt", "r") as file_dictionary_abs:
         while True:   
            line = file_dictionary_abs.readline()
            line = line.split()
            if not line:
                break
            if line[0] == "theorem":
                lines = ("begin\n " + str(line[0]) + "\n " + " ".join(line[4::])).split(" ")
                env_lines, text_proper_lines = lexer.separate_env_and_text_proper(lines)
                env_lines = lexer.remove_comment(env_lines)
                text_proper_lines = lexer.remove_comment(text_proper_lines)
                tokenized_lines, position_map = lexer.lex(text_proper_lines)
                for i in range(2, len(tokenized_lines)):
                    tokenized_lines_split = tokenized_lines[i].split(" ")
                    for j in range(len(tokenized_lines_split)):
                        tokenized_lines_split[j] = re.sub("__[^_]+_","",tokenized_lines_split[j])
                        if tokenized_lines_split[j] not in variable_check:
                            variable_number.append(tokenized_lines_split[j])
                            tokenized_lines_split[j] = "___"
                        file_parsed_abs.write(tokenized_lines_split[j] + " ")
                variable_type = len(set(variable_number))
                file_parsed_abs.write(str(len(variable_number)) + " " + str(variable_type))
                file_parsed_abs.write("\n")
                variable_number = []
            elif line[0] == "definition":
                lines = ("begin\n " + str(line[0]) + "\n " + " ".join(line[5::])).split(" ")
                env_lines, text_proper_lines = lexer.separate_env_and_text_proper(lines)
                env_lines = lexer.remove_comment(env_lines)
                text_proper_lines = lexer.remove_comment(text_proper_lines)
                tokenized_lines, position_map = lexer.lex(text_proper_lines)
                for i in range(2, len(tokenized_lines)):
                    tokenized_lines_split = tokenized_lines[i].split(" ")
                    for j in range(len(tokenized_lines_split)):
                        tokenized_lines_split[j] = re.sub("__[^_]+_","",tokenized_lines_split[j])
                        if tokenized_lines_split[j] not in variable_check:
                            variable_number.append(tokenized_lines_split[j])
                            tokenized_lines_split[j] = "___"
                        file_parsed_abs.write(tokenized_lines_split[j] + " ")
                variable_type = len(set(variable_number))
                file_parsed_abs.write(str(len(variable_number)) + " " + str(variable_type))
                file_parsed_abs.write("\n")
                variable_number = []

with open("dictionary_abs.txt", "rb") as f:
    tell = []
    tell_append = tell.append
    tell_append(0)
    with open("tell.pkl", "wb") as fi:
        while True:
            a = f.readline()
            if not a:
                break
            tell_append(f.tell())
            
        pickle.dump(tell, fi)