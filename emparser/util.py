# -*- coding: utf-8 -*-

"""Utility module for Extended Mizar Parser (emparser).

The purpose of this module is to provide utility classes and functions
that are used in plural modules.

Example:
    See test/test_util

Todo:


"""

import lxml.etree as ET
from xml.dom import minidom


def pretty_xml(et_node):
    """convert XML ET.Element to pretty format

    Args:
        et_node (ET.Element): top node to convert

    Returns:
        str: xml text in pretty format
    """
    lines = minidom.parseString(ET.tostring(et_node)).toprettyxml(indent=' ').split('\n')
    return '\n'.join([line for line in lines if line.strip()])