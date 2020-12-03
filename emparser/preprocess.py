# -*- coding: utf-8 -*-

"""Preprocess module for Extended Mizar Parser (emparser).

This module is used for preprocess for Extended Mizar Parser.
Preprocess means the process before ANTLR-generated parser.

Example:
    See test/test_preprocess

Todo:


"""

import os
import re
from emparser import PositionMap

RESERVED_WORDS = set(['according','aggregate','all','and','antonym','are','as',
  'associativity','assume','asymmetry','attr','be','begin','being','by',
  'canceled','case','cases','cluster','coherence','commutativity',
  'compatibility','connectedness','consider','consistency','constructors',
  'contradiction','correctness','def','deffunc','define','definition',
  'definitions','defpred','do','does','end','environ','equals','ex','exactly',
  'existence','for','from','func','given','hence','hereby','holds',
  'idempotence','identify','if','iff','implies','involutiveness',
  'irreflexivity','is','it','let','means','mode','non','not','notation',
  'notations','now','of','or','otherwise','over','per','pred','prefix',
  'projectivity','proof','provided','qua','reconsider','reduce','reducibility',
  'redefine','reflexivity','registration','registrations','requirements',
  'reserve','sch','scheme','schemes','section','selector','set','sethood','st',
  'struct','such','suppose','symmetry','synonym','take','that','the','then',
  'theorem','theorems','thesis','thus','to','transitivity','uniqueness',
  'vocabularies','when','where','with','wrt'])
"""set[string]: Reserved words that are defined in Mizar language.

See http://mizar.org/language/lexicon.html
"""

SPECIAL_SYMBOLS = {
    1: set([',', ';', ':', '(', ')', '[', ']', '{', '}', '=', '&']),
    2: set(['->', '.=', '$1', '$2', '$3','$4','$5','$6','$7','$8','$9', '(#', '#)']),
    3: set(['...', '$10'])
}
"""dict[set[string]]: Special symbols that are defined in Mizar language.

They are classfied with the length of symbol.
See http://mizar.org/language/lexicon.html
"""


IDENTIFIER_REG = re.compile(r"^[a-zA-Z_'][\w']*", re.ASCII)
"""re: Regex object to specify idenfifier in Mizar language.
"""

# NOT_BOUNDARY_REG = re.compile(r"^[\w']{2}", re.ASCII)
NOT_BOUNDARY_REG = re.compile(r"^[a-zA-Z0-9]{2}", re.ASCII)
"""re: Regex object to check if two character is boundary in Mizar language.
"""

NUMERAL_REG = re.compile(r"^[0-9]+", re.ASCII)
"""re: Regex object to specify idenfifier in Mizar language.
"""

BEGIN_LINE_REG = re.compile(r"^\s*begin[;\s]", re.ASCII)
"""re: Regex object to specify a line to start "begin" keyword in Mizar language.
"""

class Lexer:
    """Lexical Analyser for Extended Mizar Parser.
    
    The purpose of this class is to read raw Mizar text and write modified
    Mizar-like text that is easier for ANTLR to analyze. The purpose is similar
    to preprocessor of WS-Mizar, but the context may not be.
    This lexer estimates the boundary between two words by "adhoc rules",
    and, in its output text they are cleary splitted with space or return.
    
    The "adhoc rules" are used because we do not want to use environment part. 
    (As you know, Mizar is context-sensitive grammar and symbols are varied 
    with included .miz files) Since this project is aimed at providing a Mizar 
    parser for search engine, it is necessary that the environment part can
    be omitted.

    Attributes:
        symbol_dict (dict[str, tuple[str]]): dictonary of symbol name and its properties.
                The propeties are consist of type, file name, and priority.
                the priority is optional.
        len2symbol (dict[int, set[str]]): mapping of symbol length and symbol name.

    """

    def __init__(self):
        self.clear()
    
    def clear(self):
        self.symbol_dict = {}
        self.len2symbol = {}

    def separate_env_and_text_proper(self, lines):
        """Separate the envronment part and the text prpoer part of .miz file

        This function searches "begin" keyword and separates two parts there.

        Note:
            If "begin" keyword starts after some word in the line,
            this function returns wrong lists.
            If a line that starts from "begin" keyword is not found,
            this function consider every line is in the environment part.

        Args:
            lines (list[str]): 

        Returns:
            (list[str], list[str]): pair of environment part and text proper part
        """

        # Search "begin" keyword 
        for i, line in enumerate(lines):
            m = re.match(BEGIN_LINE_REG, line)
            if m is not None:
                # begin keyword is found
                return lines[:i], lines[i:]
        
        # a line that starts from "begin" keyword is not found
        return lines, []

    def load_symbol_dict(self, mml_vct, miz_files=None):
        """Load symbol dictonary from mml.vct file

        This function read mml.vct and create symbol dictionary that includes
        whole symbols declared in MML.

        The format of mml.vct is like the following:

        #ALGSEQ_1                       <-- file name
        G0 K0 L0 M1 O0 R1 U1 V1         <-- number of each type of symbols
        Vfinite-Support                 <-- type and symbol 
        MAlgSequence
        Ris_at_least_length_of
        Oleq 32                         <-- functor may have priority
        #ALGSPEC1
        G0 K0 L0 M2 O1 R2 U0 V0 
        O-indexing
        Mrng-retract
        Rform_a_replacement_in
        MExtension
        Rrun runs                       <-- some symbol may have two expression

        Args:
            mml_vct (str): path for mml.vct file, which is located in
                the directory that includes mizar binaries.
            miz_files (list[str]): Mizar filenames in which vocabularies are declared 
        """
        if miz_files is not None:
            miz_files = set(miz_files)
            miz_files.add('HIDDEN')
        
        self.symbol_dict = {}
        
        # load symbols from voc_file
        lines = None
        with open(mml_vct) as f:
            lines = f.readlines()
            assert len(lines) > 0
        
        ignore_next_line = False
        ignore_this_file = False
        for line in lines:
            line = line.rstrip()
            if line[0] == "#":
                filename = line[1:]
                ignore_next_line = True
                if miz_files and filename not in miz_files:
                    ignore_this_file = True
                else:
                    ignore_this_file = False
            elif ignore_next_line:
                # number of each type of symbols are written here -> ignore
                ignore_next_line = False
            elif len(line) > 0 and not ignore_this_file:
                # symbol is written in this line
                self.load_symbol_in_line(line, filename)
    
    def load_symbol_in_line(self, line, filename):
        """Read symbol written in a line of mml.vct file and add to symbol_dict.

        This function read one or two symbol written in a line of mml.vct file.
        The format example of mml.vct is shown at the comment of create_symbol_dict().

        Args:
            line (str): A line of mml.vct file. Other redundant lines are 
            filename (str): File name in which the symbol is defined
        """
        assert len(line) > 1

        symbol_type = line[0]
        values = line[1:].split(' ')
        name = values[0]
        assert name not in self.symbol_dict
        if len(values) == 1:
            # only one symbol is defined
            self.symbol_dict[name] = {'type': symbol_type, 'filename': filename}
        else:
            assert len(values) == 2
            if symbol_type == 'O' and values[1].isdigit():
                # priority is included
                self.symbol_dict[name] = {'type': symbol_type, 
                                          'filename': filename,
                                          'priority': values[1]}
            else:
                # two names are defined
                self.symbol_dict[name] = {'type': symbol_type, 
                                          'filename': filename}

                assert values[1] not in self.symbol_dict
                self.symbol_dict[values[1]] = {'type': symbol_type, 
                                               'filename': filename}

    def build_len2symbol(self):
        """Build mapping between symbol length and symbol name from symbol_dict.

        Todo:
            Change the data structure to Radix tree
            See https://en.wikipedia.org/wiki/Radix_tree
        """
        # load special symbols in advance
        for symbols in SPECIAL_SYMBOLS.values():
            for name in symbols:
                self.symbol_dict[name] = {'type': 'special'}

        self.len2symbol = {}
        for name in self.symbol_dict:
            length = len(name)
            if length not in self.len2symbol:
                self.len2symbol[length] = set([name])
            else:
                self.len2symbol[length].add(name)
    
    def remove_comment_in_a_line(self, line):
        """Remove comment in a line

        Args:
            line (str): a line which may or may not include comments
        
        Returns:
            str: a line removed comment
        """
        n = line.find('::')
        if n >= 0:
            return line[:n]
        else:
            return line

    def remove_comment(self, lines):
        """Remove comment in lines

        Args:
            lines (list[str]): lines which may or may not include comments
        
        Returns:
            list[str]: lines from which removed comment
        """
        return [self.remove_comment_in_a_line(line) for line in lines]

    def lex(self, lines, is_environment_part=False,
            first_line_number=1):
        """Lexical analyzer.

        Args:
            lines (list[str]): lines to be processed
            is_environment_part (bool): if lines are environment part or not
            first_line_number (int): line number of index zero

        Returns:
            list[str]: tokenized lines
            (dict[(int,int), (int,int)]): line-column number mapping
                between before and after lex() 
        """

        class LexerStateMachine:
            def __init__(self, parent, is_environment_part=False):
                self.next_is_variable = 'no'
                self.next_for_is_relevant_to_variable = True
                self.is_environment_part = is_environment_part
                self.nest_level = 0
                self.nest2variables = {0: set()}
                self.parent = parent
       
            def cut(self, line):
                """Cut a left-most token in a line

                Args:
                    line (str): strings to cut

                Returns:
                    (str, str): left-most token and the rest of line if found
                    None: otherwise (illegal)
                """
                call_functions = None
                if self.next_is_variable == 'yes':
                    call_functions = [self.cut_identifier]
                elif self.next_is_variable in ['maybe', 'no']:
                    call_functions = [
                        self.cut_symbol,
                        self.cut_reserved_word,
                        self.cut_numeral,
                        self.cut_identifier
                    ]
                for func in call_functions:
                    res = func(line)
                    if res:
                        return res
                
                # error
                return None

            def is_special_symbol(self, symbol):
                """Check if it is a special symbol

                Args:
                    symbol (str): symbol to be checked

                Returns:
                    True if it is a special symbol, otherwise False
                """
                i = len(symbol)
                return i in SPECIAL_SYMBOLS and symbol in SPECIAL_SYMBOLS[i]

            def cut_symbol(self, line):
                """Cut a first token symbol in a line

                Args:
                    line (str): strings to cut symbol

                Returns:
                    (str, str): first token symbol and the rest of line if found
                    None: otherwise
                """
                res = self.parent.cut_symbol(line)
                if self.is_environment_part and res is not None:
                    if res[0] not in [',', ';']:
                        return None

                # variable flag maintenance
                if self.next_is_variable == 'maybe':
                    if res is not None and res[0] == ',':
                        self.next_is_variable = 'yes'
                    else:
                        self.next_is_variable = 'no'

                if not self.next_for_is_relevant_to_variable:
                    if res is not None and res[0] == ';':
                        self.next_for_is_relevant_to_variable = True

                if res is not None:
                    for variables in self.nest2variables.values():
                        if res[0] in variables:
                            # The same name as declared variable
                            # -> it is not symbol name
                            return None

                return res

            def cut_reserved_word(self, line):
                """Cut a first token reserved word in a line

                Args:
                    line (str): strings to cut reserved word

                Returns:
                    (str, str): first token reserved word and the rest of line if found
                    None: otherwise
                """
                res = self.parent.cut_reserved_word(line)
                if res is not None:
                    if res[0] in ['synonym', 'antonym', 'cluster', 'reserve']:
                        self.next_for_is_relevant_to_variable = False
                    elif res[0] == 'for' and self.next_for_is_relevant_to_variable:
                        self.next_is_variable = 'yes'
                    elif res[0] == 'environ':
                        self.is_environment_part = True
                    elif res[0] == 'begin':
                        self.is_environment_part = False
                    elif res[0] in ['let', 'given', 'consider', 'ex', 'reserve']:
                        self.next_is_variable = 'yes'
                    elif res[0] in ['definition', 'registration', 'notation', 'scheme',
                        'case', 'suppose', 'hereby', 'now', 'proof']:
                        self.nest_level += 1
                        self.nest2variables[self.nest_level] = set()
                    elif res[0] == 'end':
                        del self.nest2variables[self.nest_level]
                        self.nest_level -= 1
                return res
            
            def cut_numeral(self, line):
                """Cut a first token numeral in a line

                Args:
                    line (str): strings to cut numeral

                Returns:
                    (str, str): first token numeral and the rest of line if found
                    None: otherwise
                """
                return self.parent.cut_numeral(line)
            
            def cut_identifier(self, line):
                """Cut a first token identifier in a line

                Args:
                    line (str): strings to cut identifier

                Returns:
                    (str, str): first token identifier and the rest of line if found
                    None: otherwise
                """
                res = self.parent.cut_identifier(line)
                if self.next_is_variable == 'yes':
                    assert res is not None
                    self.nest2variables[self.nest_level].add(res[0])
                    self.next_is_variable = 'maybe'
                return res
            
        stateMachine = LexerStateMachine(self, is_environment_part)
        tokenized_lines = []
        position_map = PositionMap()

        for i, line in enumerate(lines):
            tokens = []

            after_column = 1

            buffer = line
            while buffer:
                buffer = buffer.lstrip()
                if not buffer:
                    continue
                
                before_pos = (first_line_number+i, len(line) - len(buffer) + 1)
                
                res = stateMachine.cut(buffer)
                if res is None:
                    print('Error in lexer pos={}, buffer={}'.format(before_pos, buffer))
                    assert False
                tokens.append(res[0])
                buffer = res[1]

                after_pos = (i+1, after_column)
                after_column += len(res[0]) + 1

                position_map.set_position(before_pos, after_pos)

            tokenized_lines.append(' '.join(tokens))

        return (tokenized_lines, position_map)

    def read_until_space(self, line):
        """Read line until space.

        Note:
            The first character should not be spaces.
            Apply lstrip() beforehand.

        Returns:
            str: longest left strings that does not include spaces
        """
        for i in range(len(line)):
            if line[i].isspace():
                return line[:i]
        return line

    def read_identifier(self, line):
        """Read identifier from the left side of line.

        Note:
            The first character should not be spaces.
            Apply lstrip() beforehand.

        Args:
            line (str): line to read

        Returns:
            str: left side identifier of the line
                Empty string will be returned if identifier is not found.
        """
        m = re.match(IDENTIFIER_REG, line)
        if m is None:
            return ""
        else:
            return m.group(0)

    def is_word_boundary(self, a, b):
        """Check if the boundary between a and b is a word bounary.

        Args:
            a (str): a character
            b (str): a character

        Returns:
            bool: If it is a word boundary, returns True. Otherwise False.
        """
        m = re.match(NOT_BOUNDARY_REG, a+b)
        return m is None

    def cut_symbol(self, line):
        """Cut symbol from the left side of line.

        Args:
            line (str): line to be cut

        Returns:
            (str, str): symbol and the rest of line if found
            None: Otherwise
        """
        chunk = self.read_until_space(line)
        length = len(chunk)

        i = length
        while i > 0:
            if i not in self.len2symbol or \
            chunk[:i] not in self.len2symbol[i]:
                # symbol is not appeared
                i -= 1
                continue

            if i != length and \
            not self.is_word_boundary(chunk[i-1], chunk[i]):
                # substring cannot be divided as symbol
                i -= 1
                continue
            
            # symbol is found
            symbol = chunk[:i]
            attrs = self.symbol_dict[symbol]
            if attrs['type'] != 'special':
                prefix = '__' + attrs['type']
                if 'priority' in attrs:
                    prefix += attrs['priority']
                prefix += '_'
                symbol = prefix + symbol

            return symbol, line[i:]

        # not found
        return None

    def cut_reserved_word(self, line):
        """Cut reserved word from the left side of line.

        Args:
            line (str): line to be cut

        Returns:
            (str, str): reserved word and the rest of line if found
            None: Otherwise
        """
        word = self.read_identifier(line)
        if word in RESERVED_WORDS:
            return word, line[len(word):]
        else:
            return None

    def cut_identifier(self, line):
        """Cut identifier from the left side of line.

        Args:
            line (str): line to be cut

        Returns:
            (str, str): identifier and the rest of line if found
            None: Otherwise
        """
        word = self.read_identifier(line)
        if word:
            return word, line[len(word):]
        else:
            return None

    def cut_numeral(self, line):
        """Cut numeral from the left side of line.

        Args:
            line (str): line to be cut

        Returns:
            (str, str): numeral string and the rest of line if found
            None: Otherwise
        """
        m = re.match(NUMERAL_REG, line)
        if m is None:
            return None
        else:
            word = m.group(0)
            if len(word) > 1 and word[0] == '0':
                return None
            else:
                return (word, line[len(word):])
