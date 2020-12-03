# -*- coding: utf-8 -*-

"""Postprocess module for Extended Mizar Parser (emparser).

This module is used for postprocess for Extended Mizar Parser.
Postprocess means the process after ANTLR-generated parser.

Example:
    See test/test_postprocess

Todo:


"""

import re
import lxml.etree as ET


SYMBOL_PREFIX_REG = re.compile(r"\d", re.ASCII)
"""re: Regex object to specify symbol prefix.^(__[GKLMORUV]\d*_)
"""

FUNCTOR_PRIORITY_REG = re.compile(r"\d", re.ASCII)
"""re: Regex object to specify priority of functor symbol.^__O(\d*)_
"""

SYMBOL_TAGS = {'predicateSymbol', 'functorSymbol', 'leftFunctorBracket'
    'rightFunctorBracket', 'attributeSymbol', 'modeSymbol', 'structureSymbol',
    'selectorSymbol'}
"""set[str]: Symbol tags in CST.
"""

class CSTHandler:
    """CST (concrete syntax tree) Handler.
    
    The purpose of this class is to handle CST
    produced by ANTLR-generated parser. Its roles are:
    extract information, manipulate CST, and so on.
    """
    @classmethod
    def extract_vocabularies(cls, _root):
        """Extract vocabulary files in environment part

        Args:
            _root (ET.Element): xml node includes environment part,
                which is produced by ANTLR-generated parser.
        
        Returns:
            list[str]: list of vocabulary Mizar files
        """
        _vocablaries = _root.findall('.//vocabularyName')
        return [_vocablary.get('spelling') for _vocablary in _vocablaries]
    
    def adjust_type_expression(self, _root):
        """Modify and adjust type expression node into original syntax 
        
        Procedure:
            1. Shrink radixTypeExpression node

        Target structure:
            typeExpression : adjectiveCluster radixTypeExpression ;
            radixTypeExpression : '(' radixType ')'
                | radixType ;

        After conversion, the structure will be:
            typeExpression : '(' radixType ')'
                | adjectiveCluster typeExpression
                | radixType ;

        Args:
            _root (ET.Element): xml node includes typeExpressions under it.
        """
        _radix_type_expressions = _root.findall('.//radixTypeExpression')
        for _radix_type_expression in _radix_type_expressions:
            _type_expression = _radix_type_expression.getparent()
            assert _type_expression.tag == 'typeExpression'

            _children = _radix_type_expression.getchildren()
            _type_expression.remove(_radix_type_expression)
            _type_expression.extend(_children)


    def adjust_term_expression(self, _root):
        """Modify and adjust term expression node into original syntax 
        
        Procedure:
            1. Adjust precedence of functor symbols in termExpression
            2. Shrink unitaryTerm node
        
        Target structure:
            termExpression : arguments ? (functorSymbol + arguments) * functorSymbol + arguments ?
                | termExpression 'qua' typeExpression
                | unitaryTerm ;
            unitaryTerm : '(' termExpression ')'
                | leftFunctorBracket termExpressionList rightFunctorBracket
                | functorIdentifier '(' termExpressionList ? ')'
                | structureSymbol '(#' termExpressionList '#)'
                | 'the' structureSymbol 'of' termExpression
                | variableIdentifier
                | '{' termExpression  postqualification * ':' sentence '}'
                | 'the' 'set' 'of' 'all' termExpression postqualification *
                | NUMERAL
                | 'the' selectorSymbol 'of' termExpression
                | 'the' selectorSymbol
                | 'the' typeExpression
                | privateDefinitionParameter
                | 'it' ;
            arguments : unitaryTerm | '(' termExpressionList ')' ;

        After conversion, the structure will be:
            termExpression : '(' termExpression ')'
                | arguments ? functorSymbol arguments ?  // left recursion
                | leftFunctorBracket termExpressionList rightFunctorBracket
                | functorIdentifier '(' termExpressionList ? ')'
                | structureSymbol '(#' termExpressionList '#)'
                | 'the' structureSymbol 'of' termExpression
                | variableIdentifier
                | '{' termExpression  postqualification * ':' sentence '}'
                | 'the' 'set' 'of' 'all' termExpression postqualification *
                | NUMERAL
                | termExpression 'qua' typeExpression
                | 'the' selectorSymbol 'of' termExpression
                | 'the' selectorSymbol
                | 'the' typeExpression
                | privateDefinitionParameter
                | 'it' ;
            arguments : termExpression | '(' termExpressionList ')' ;
        
        Args:
            _root (ET.Element): xml node includes termExpressions under it.
        """
        # 1. Adjust precedence of functor symbols in termExpression
        _term_expressions = _root.findall('.//termExpression[functorSymbol]')

        for _term_expression in _term_expressions:
            _functors = _term_expression.findall('./functorSymbol')
            func2priorities = []
            for _functor in _functors:
                spelling = _functor.get('spelling')
                m = re.match(FUNCTOR_PRIORITY_REG, spelling)
                if m.group(1):
                    priority = int(m.group(1))
                else:
                    priority = 64
                func2priorities.append((_functor, priority))

            func2priorities.sort(key=lambda a: a[1], reverse=True)

            for i, f2p in enumerate(func2priorities):
                _functor = f2p[0]
                _prev = _functor.getprevious()
                _next = _functor.getnext()
                if i < len(func2priorities) - 1:
                    _sub_term = ET.Element('termExpression')
                    
                    if _prev is not None and _prev.tag != 'functorSymbol':
                        _term_expression.remove(_prev)
                        if _prev.tag != 'arguments':
                            _arguments = ET.Element('arguments')
                            _arguments.append(_prev)
                            _sub_term.append(_arguments)
                        else:
                            _sub_term.append(_prev)

                    _functor.addprevious(_sub_term)
                    _term_expression.remove(_functor)
                    _sub_term.append(_functor)
                    
                    if _next is not None and _next.tag != 'functorSymbol':
                        _term_expression.remove(_next)
                        if _next.tag != 'arguments':
                            _arguments = ET.Element('arguments')
                            _arguments.append(_next)
                            _sub_term.append(_arguments)
                        else:
                            _sub_term.append(_next)
                else:
                    # it is the last node
                    if _prev is not None and _prev.tag != 'arguments':
                        _arguments = ET.Element('arguments')
                        _prev.addprevious(_arguments)
                        _term_expression.remove(_prev)
                        _arguments.append(_prev)

                    if _next is not None and _next.tag != 'arguments':
                        _arguments = ET.Element('arguments')
                        _next.addprevious(_arguments)
                        _term_expression.remove(_next)
                        _arguments.append(_next)
        # 2. Shrink unitaryTerm node
        _unitary_terms = _root.findall('.//unitaryTerm')
        for _unitary_term in _unitary_terms:
            _parent = _unitary_term.getparent()

            if _parent.tag == 'termExpression':
                _children = _unitary_term.getchildren()
                for _child in _children:
                    _unitary_term.addprevious(_child)
                _parent.remove(_unitary_term)
            else:
                assert _parent.tag == 'arguments'
                _unitary_term.tag = 'termExpression'
            

    def remove_prefix(self, _root):
        """Remove prefix in spelling of symbol nodes 

        Args:
            _root (ET.Element): CST root node.
        """
        for element in _root.iter():
            spelling = element.get('spelling')
            if spelling is not None:
                m = re.match(SYMBOL_PREFIX_REG, spelling)
                if m is not None:
                    spelling = spelling[len(m.group(1)):]
                    element.set('spelling', spelling)



'''
class CST2AST:
    """XML Converter from CST to AST.
    
    The purpose of this class is to provide converter from
    CST (concrete syntax tree) to AST (abstract syntax tree).

    Naming rule in source code:
        convert_abc()   ->  create a top node for the tag in the function
        _convert_abc()  ->  Do not create a top node for the tag in the function

        node   -> AST node
        _node  -> CST node

    Naming rule of AST grammar comments
        abc -> create tag in this function
        _abc -> do not create tag in this function
        <abc> -> convet_abc() is called
        <_abc> -> _convet_abc() is called

        _tag : -> AST node is not created for the tag
    """
    def convert(self, _root):
        """Convert CST to AST

        Args:
            _root (ET.Element): CST root node produced
                by mainprocess.parse()
        
        Returns:
            list[ET.Element]: corresponding AST nodes
        """
        root = ET.Element('root')
        if _root.tag == 'environmentDeclaration':
            self.convert_environ(root, _root)
        elif _root.tag == 'textProper':
            self.convert_text_proper(root, _root)
        elif _root.tag == 'textItem':
            self._convert_text_item(root, _root)
        else:
            print("There is no corresponding converter for {}".format(_root.tag))
        
        return root.findall('./*')

    def convert_environ(self, parent, _environ):
        """Convert environment part of CST to AST

        CST grammar:
            environmentDeclaration : 'environ' directive * ;
            directive : vocabularyDirective | libraryDirective | requirementDirective ;
            vocabularyDirective : 'vocabularies' vocabularyName ( ',' vocabularyName ) * ';' ;
            vocabularyName : FILE_NAME ;
            libraryDirective : ( 'notations' | 'constructors' | 'registrations' | 'definitions' | 'expansions' | 'equalities' | 'theorems' | 'schemes' )
                articleName ( ',' articleName ) * ';' ;
            articleName : FILE_NAME ;
            requirementDirective : 'requirements' requirement ( ',' requirement ) * ';' ;
            requirement : FILE_NAME ;

        AST grammar:
            environ : directive * ;
            directive : article * ;

        AST node attributes:
            environ
            directive[name]
                name : "notations" | "constructors" | "registrations" | "definitions"
                    | "expansions" | "equalities" | "theorems" | "schemes"
            article[spelling, line, col]
                spelling: FILENAME

        Mapping AST <- CST:
            environ <- environmentDeclaration
            directive <- directive
            article <- vocabularyDirective/vocabularyName,
                   | requirementDirective/requirement,
                   | libraryDirective/articleName

        Args:
            parent (ET.Element): AST parent node
            _environ (ET.Element): CST node
        
        Returns:
            list[ET.Element]: corresponding AST nodes
        """
        environ = ET.SubElement(parent, 'environ')
        for _directive in _environ:
            if _directive.tag != 'directive':
                continue
            _keyword = _directive.find('.//keyword')
            directive_name = _keyword.get('spelling')
            directive = ET.SubElement(environ, 'directive', {'name': directive_name})
            if directive_name == 'vocabularies':
                _names = _directive.findall('./vocabularyDirective/vocabularyName')
            elif directive_name == 'requirements':
                _names = _directive.findall('./requirementDirective/requirement')
            else:
                _names = _directive.findall('./libraryDirective/articleName')
            
            for _name in _names:
                ET.SubElement(directive, 'articleName', attrib=self.std_attrib(_name))

    def convert_text_proper(self, parent, _text_proper):
        """Convert text proper part of CST to AST

        CST grammar:
            textProper : section + ;
            section : 'begin' textItem * ;

        AST grammar:
            textProper : ( sectionPragma <_textItem> * ) *  ;
        
        AST node attributes:
            textProper
            sectionPragma[spelling, line, col]
                spelling : "begin"
        
        Mapping AST <- CST:
            textProper <- textProper
            sectionPragma <- section/'begin'
            <_textItem> <- section/textItem

        Args:
            parent (ET.Element): AST parent node
            _text_proper (ET.Element): CST node
        """
        text_proper = ET.SubElement(parent, 'textProper')
        for _section in _text_proper:
            _begin = _section[0]
            ET.SubElement(text_proper, 'sectionPragma', attrib=self.std_attrib(_begin))
            
            for _text_item in _section[1:]:
                self._convert_text_item(text_proper, _text_item)

    def _convert_text_item(self, parent, _text_item):
        """Convert textItem CST to AST

        CST grammar:
            textItem : reservation | definitionalItem | registrationItem
                | notationItem | theorem | schemeItem | auxiliaryItem ;

        AST grammar:
            _textItem : <_reservation> | <definitionalItem> | <registrationItem>
                | <notationItem> | <theorem> | <schemeItem> | <auxiliaryItem> ;
        
        Mapping AST <- CST:
            _textItem <- textItem
            <_reservation> <- reservation
            <definitionalItem> <- definitionalItem
            <registrationItem> <- registrationItem
            <notationItem> <- notationItem
            <theorem> <- theorem
            <schemeItem> <- schemeItem
            <auxiliaryItem> <- auxiliaryItem

        Args:
            parent (ET.Element): AST parent node
            _text_item (ET.Element): CST node
        """
        for _child in _text_item:
            if _child.tag == 'reservation':
                self._convert_reservation(parent, _child)
            elif _child.tag == 'definitionalItem':
                self.convert_definitional_item(parent, _child)
            elif _child.tag == 'registrationItem':
                self.convert_registration(parent, _child)
            elif _child.tag == 'notationItem':
                self.convert_notation(parent, _child)
            elif _child.tag == 'theorem':
                self.convert_theorem(parent, _child)
            elif _child.tag == 'schemeItem':
                self.convert_scheme(parent, _child)
            elif _child.tag == 'auxiliaryItem':
                self.convert_auxiliary(parent, _child)
            else:
                print("There is no corresponding converter for {}".format(_child.tag))

    def _convert_reservation(self, parent, _reservation):
        """Convert reservation CST to AST

        CST grammar:
            reservation : 'reserve' reservationSegment (',' reservationSegment) * ';' ;
            reservationSegment : reservedIdentifiers 'for' typeExpression ;
            reservedIdentifiers : reservedIdentifier (',' reservedIdentifier ) *;
            reservedIdentifier: IDENTIFIER ;

        AST grammar:
            _ : reservation + ;
            reservation : (variable + <typeExpression>)) + ;

        AST node attributes:
            reservation
            variable[spelling, line, col]

        Mapping AST <- CST:
            _ <- reservation
            reservation <- reservationSegment
            variable <- reservationSegment/reservedIdentifier
            <typeExpression> <- typeExpression

        Args:
            parent (ET.Element): AST parent node
            _reservation (ET.Element): CST node
        """
        for _reservation_segment in _reservation:
            if _reservation_segment.tag != 'reservationSegment':
                continue
            reservation = ET.SubElement(parent, 'reservation')

            _variables = _reservation_segment.findall('./reservedIdentifiers/reservedIdentifier')
            for _variable in _variables:
                ET.SubElement(reservation, 'variable', attrib=self.std_attrib(_variable))
            
            _type_expression = _reservation_segment.find('./typeExpression')
            self.convert_type_expression(reservation, _type_expression)

    def convert_definitional_item(self, parent, _definitional_item):
        # TODO
        _definitional_block = _definitional_item.find('./definitionalBlock')
        # definitional_block = ET.SubElement(parent, 'definitionalBlock')
        # _definitional_block.findall()

    def convert_registration(self, parent, _registration):
        # TODO
        _registrational_block = _registration.find('./registrationBlock')
        _registration_keyword = _registrational_block.find('./keyword[@spelling="registration"]')
        ET.SubElement(parent, 'registration', attrib=self.std_attrib(_registration_keyword))

    def convert_notation(self, parent, _notation):
        # TODO
        _notation_block = _notation.find('./notationBlock')
        _notation_keyword = _notation_block.find('./keyword[@spelling="notation"]')
        ET.SubElement(parent, 'notation', attrib=self.std_attrib(_notation_keyword))

    def convert_theorem(self, parent, _theorem):
        # TODO
        """Convert theorem CST to AST

        Args:
            parent (ET.Element): AST parent node
            _theorem (ET.Element): CST node
        """
        _theorem_keyword = _theorem.find('./keyword[@spelling="theorem"]')
        ET.SubElement(parent, 'theorem', attrib=self.std_attrib(_theorem_keyword))
        # TODO

    def convert_scheme(self, parent, _scheme):
        # TODO
        _scheme_block = _scheme.find('./schemeBlock')
        _scheme_keyword = _scheme_block.find('./keyword[@spelling="scheme"]')
        ET.SubElement(parent, 'scheme', attrib=self.std_attrib(_scheme_keyword))
    
    def convert_auxiliary(self, parent, _auxiliary):
        # TODO
        ET.SubElement(parent, 'auxiliary')

    def convert_type_expression(self, parent, _type_expression):
        """Convert type expression CST to AST

        CST grammar:
            typeExpression : '(' radixType ')'
                | adjective + typeExpression
                | radixType ;

        AST grammar:
            typeExpression : <adjective> * <radixType> ;

        AST node attributes:
            typeExpression

        Mapping AST <- CST:
            typeExpression <- typeExpression
            <adjective> <- adjective
            <radixType> <- radixType

        Args:
            parent (ET.Element): AST parent node
            _reservation (ET.Element): CST node
        """
        type_expression = ET.SubElement(parent, 'typeExpression')
        _adjectives = _type_expression.findall('./adjective')
        for _adjective in _adjectives:
            self.convert_adjective(type_expression, _adjective)
        
        _radix_type = _type_expression.find('.//radixType')
        self._convert_radix_type(type_expression, _radix_type)
    
    def convert_adjective(self, parent, _adjective):
        """Convert adjective CST to AST
        
        CST grammar:
            adjective : 'non' ? adjectiveArguments ? attributeSymbol ;
            adjectiveArguments : termExpressionList | '(' termExpressionList ')' ;
            attributeSymbol : ATTRIBUTE_SYMBOL ;

        AST grammar:
            adjective : attributeNagation ? <termExpression> * attributeSymbol ;

        AST node attributes:
            adjective
            attributeNagation[spelling, line, col]
            attributeSymbol[spelling, line, col]

        Mapping AST <- CST:
            attributeNagation <- 'non'
            <termExpression> <- adjectiveArguments/termExpressionList/termExpression
            attributeSymbol <- attributeSymbol
        
        Args:
            parent (ET.Element): AST parent node
            _adjective (ET.Element): CST node
        """
        adjective = ET.SubElement(parent, 'adjective')

        _non = _adjective.find('./keyword[@spelling="non"]')
        if _non is not None:
            ET.SubElement(adjective, 'attributeNegation', attrib=self.std_attrib(_non))
        
        _term_expressions = _adjective.findall('./adjectiveArguments/termExpressionList/termExpression')
        for _term_expression in _term_expressions:
            self.convert_term_expression(adjective, _term_expression)
        
        _attribute_symbol = _adjective.find('./attributeSymbol')
        ET.SubElement(adjective, 'attributeSymbol', attrib=self.std_attrib(_attribute_symbol))

    def _convert_radix_type(self, parent, _radix_type):
        """Convert radixType CST to AST

        CST grammar:
            radixType : modeSymbol ( 'of' termExpressionList ) ?
                | structureSymbol ( 'over' termExpressionList ) ? ;
        
        AST grammar:
            _radixType : mode | structure ;
            mode : <termExpression> * ;
            structure : <termExpression> * ;
        
        AST node attributes:
            modeType[spelling, line, col]
            structureType[spelling, line, col]

        Mapping AST <- CST:
            _radixType <- radixType
            modeType <- modeSymbol
            structureType <- structureSymbol
            <termExpression> <- termExpressionList/termExpression

        Args:
            parent (ET.Element): AST parent node
            _radix_type (ET.Element): CST node
        """
        _first_node = _radix_type[0]
        if _first_node.tag == 'modeSymbol':
            top_tag = 'modeType'
        elif _first_node.tag == 'structSymbol':
            top_tag = 'structType'
        
        top_node = ET.SubElement(parent, top_tag,
                                 attrib=self.std_attrib(_first_node))

        _term_expressions = _radix_type.findall('./termExpressionList/termExpression')
        for _term_expression in _term_expressions:
            self.convert_term_expression(top_node, _term_expression)

    def convert_term_expression(self, parent, _term_expression):
        """Convert termExpression CST to AST

        Args:
            parent (ET.Element): AST parent node
            _term_expression (ET.Element): CST node
        """
        term_expression = ET.SubElement(parent, 'termExpression')
        self._convert_term_expression(term_expression, _term_expression)

    def _convert_term_expression(self, parent, _term_expression):
        """Convert termExpression CST to AST

        CST grammar:
            termExpression : arguments ? (functorSymbol + arguments) * functorSymbol + arguments ?
                | termExpression 'qua' typeExpression
                | unitaryTerm ;
            arguments : unitaryTerm | '(' termExpressionList ')' ;

        AST grammar:
            _termExpression : (<unitaryTerm> | <termExpressionList>) ?
                    (functorTerm + (<unitaryTerm> | <termExpressionList>)) *
                    functorTerm + (<unitaryTerm> | <termExpressionList>) ?
                | typeCast
                | <unitaryTerm> ;
            typeCast : <termExpression> <typeExpression> ;

        AST node attributes:
            functorTerm[spelling, line, col]
            typeCast[spelling, line, col]

        Mapping AST <- CST:
            _termExpression <- termExpression
            functorTerm <- functorSymbol
            <unitaryTerm> <- unitaryTerm
            <termExpressionList> <- termExpressionList
            <termExpression> <- termExpression/termExpression
            <typeExpression> <- termExpression/typeExpression
            typeCast <- 'qua'

        Args:
            parent (ET.Element): AST parent node
            _term_expression (ET.Element): CST node
        """
        _first_tag = _term_expression[0].tag
        if _first_tag == 'arguments':
            # TODO : Adjust functor priority
            # arguments ? (functorSymbol + arguments) * functorSymbol + arguments ?
            for _child in _term_expression:
                if _child.tag == 'arguments':
                    # arguments : unitaryTerm | '(' termExpressionList ')'
                    if _child[0].tag == 'unitaryTerm':
                        self._convert_unitary_term(parent, _child[0])
                    else:
                        self.convert_term_expression_list(parent, _child[1])
                elif _child.tag == 'functorSymbol':
                    ET.SubElement(parent, 'functorTerm', attrib=self.std_attrib(_child))
        elif _first_tag == 'termExpression':
            # termExpression 'qua' typeExpression
            type_cast = ET.SubElement(parent, 'typeCast', attrib=self.std_attrib(_term_expression[1]))
            self.convert_term_expression(type_cast, _term_expression[0])
            self.convert_type_expression(type_cast, _term_expression[2])
        elif _first_tag == 'unitaryTerm':
            # unitaryTerm
            self._convert_unitary_term(parent, _term_expression[0])

    def convert_term_expression_list(self, parent, _term_expression_list):
        """Convert termExpressionList CST to AST

        The details are implemented in _convert_term_expression_list()

        Args:
            parent (ET.Element): AST parent node
            _term_expression_list (ET.Element): CST node
        """
        term_expression_list = ET.SubElement(parent, 'termExpressionList')
        self._convert_term_expression_list(term_expression_list, _term_expression_list)

    def _convert_term_expression_list(self, parent, _term_expression_list):
        """Convert termExpressionList CST to AST

        CST grammar:
            termExpressionList : termExpression ( ',' termExpression ) * ;

        AST grammar:
            _ : <termExpression> + ;

        Mapping AST <- CST:
            _ <- termExpressionList
            <termExpression> <- termExpression

        Args:
            parent (ET.Element): AST parent node
            _term_expression_list (ET.Element): CST node
        """
        for _term_expression in _term_expression_list:
            self.convert_term_expression(parent, _term_expression)
    
    def _convert_unitary_term(self, parent, _unitary_term):
        """Convert unitaryTerm CST to AST

        CST grammar:
            unitaryTerm : '(' termExpression ')'
                | leftFunctorBracket termExpressionList rightFunctorBracket
                | functorIdentifier '(' termExpressionList ? ')'
                | structureSymbol '(#' termExpressionList '#)'
                | 'the' structureSymbol 'of' termExpression
                | variableIdentifier
                | '{' termExpression  postqualification * ':' sentence '}'
                | 'the' 'set' 'of' 'all' termExpression postqualification *
                | NUMERAL
                | 'the' selectorSymbol 'of' termExpression
                | 'the' selectorSymbol
                | 'the' typeExpression
                | privateDefinitionParameter
                | 'it' ;
            typeExpression : '(' radixType ')'
                | adjective + typeExpression   // left recursion repaired
                | radixType ;
            privateDefinitionParameter : '$1' | '$2' | '$3' | '$4' | '$5' | '$6' | '$7' | '$8' | '$9' | '$10' ;

        AST grammar:
            _ : <termExpression>
                | bracketFunctorTerm
                | privateFunctorTerm
                | structureComposedTerm
                | structureInstance
                | variable
                | intensionalStatement
                | collection
                | numeral
                | selectorInstance
                | typeInstance
                | privateDefinitionParameter
                | it ;
            bracketFunctorTerm : leftfunctorBracket <termExpressionList> rightFunctorBracket
            privateFunctorTerm : <_termExpressionList>
            structureComposedTerm : <_termExpressionList>
            structureInstance : <_termExpression>
            intensionalStatement : <termExpression> <postqualification> * <sentence>
            collection : <termExpression> <postqualification> *
            selectorInstance : <_termExpression> ?
            typeInstance : <typeExpression>

        AST node attributes:
            bracketFunctorTerm
            privateFunctorTerm[spelling, line, col]
            structureComposedTerm[spelling, line, col]
            structureInstance[spelling, line, col]
            variable[spelling, line, col]
            intensionalStatement[spelling, line, col]
            collection[spelling, line, col]
            numeral[spelling, line, col]
            selectorInstance[spelling, line, col]
            typeInstance[line, col]
            privateDefinitionParameter[spelling, line, col]
            it[spelling, line, col]
            leftfunctorBracket[spelling, line, col]
            termExpressionList
            rightFunctorBracket[spelling, line, col]





        Mapping AST <- CST:
            _ <- unitaryTerm
            termExpression <- termExpression
            leftfunctorBracket <- leftfunctorBracket
            privateFunctorTerm <- functorIdentifier
            structureComposition <- structureSymbol '(#'
            structureInstance <- 'the' structureSymbol 'of'
            variable <- variableIdentifier
            numeral <- NUMERAL

        Args:
            parent (ET.Element): AST parent node
            _term_expression_list (ET.Element): CST node
        """
        _child_0 = _unitary_term[0]
        

    def std_attrib(self, node):
        """Extract standard attribute from node

        Standard attributes are 'spelling', 'line' and 'col'.
        Functor prefixes are removed here.

        Args:
            node (ET.Element): CST node
        
        Returns:
            dict[str,str]: attributes extracted from input node
        """
        spelling = node.get('spelling')
        if node.tag in SYMBOL_TAGS:
            m = re.match(SYMBOL_PREFIX_REG, spelling)
            if m is not None:
                prefix = m.group(1)
                spelling = spelling[len(prefix):]
        
        return {'spelling': spelling,
                'line': node.get('line'),
                'col': node.get('col')}
'''