#!/usr/bin/python

"""
pydocmd generates Python Module / script documentation in the Markdown (md)
format. It was written to automatically generate documentation that can be put
on Github or Bitbucket.

It is as of yet not very complete and is more of a Proof-of-concept than a
fully-fledged tool. Markdown is also a very restricted format and every
implementation works subtly, or completely, different. This means output
may be different on different converters.

Usage
-----

    ./pydocmd file.py > file.md

Example output
--------------

* https://bitbucket.org/fboender/pydocmd/wiki/Example
* https://bitbucket.org/fboender/pydocmd/wiki/Example2

"""


import sys
import os
import imp
import inspect
import re


__author__ = "Ferry Boender"
__copyright__ = "Copyright 2014, Ferry Boender"
__license__ = "MIT (expat) License"
__version__ = "0.1"
__maintainer__ = "Ferry Boender"
__email__ = "ferry.boender@gmail.com"


def fmt_link(link):
    link = re.sub(r'[\(\)\{\}\[\]\*\`\n\#\.\,\=\:\;\\\/]', "", link)
    link = link.strip()
    link = link.lower()
    link = link.replace(" ", "-")
    return link


def insp_mod(mod_name, mod_inst):
    """
    Inspect a module return doc, vars, functions and classes.
    """
    info = {
        'name': mod_name,
        'inst': mod_inst,
        'author': {},
        'doc': '',
        'vars': [],
        'functions': [],
        'classes': [],
    }

    # Get module documentation
    mod_doc = inspect.getdoc(mod_inst)
    if mod_doc:
        info['doc'] = mod_doc

    for attr_name in ['author', 'copyright', 'license', 'version', 'maintainer', 'email']:
        if hasattr(mod_inst, '__%s__' % (attr_name)):
            info['author'][attr_name] = getattr(mod_inst, '__%s__' % (attr_name))

    # Get module global vars
    for member_name, member_inst in inspect.getmembers(mod_inst):
        if not member_name.startswith('_') and \
           not inspect.isfunction(member_inst) and \
           not inspect.isclass(member_inst) and \
           not inspect.ismodule(member_inst) and \
           member_name not in mod_inst.__builtins__:
            info['vars'].append( (member_name, member_inst) )

    # Get module functions
    functions = inspect.getmembers(mod_inst, inspect.isfunction)
    if functions:
        for func_name, func_inst in functions:
            info['functions'].append(insp_method(func_name, func_inst))

    classes = inspect.getmembers(mod_inst, inspect.isclass)
    if classes:
        for class_name, class_inst in classes:
            info['classes'].append(insp_class(class_name, class_inst))

    return info


def insp_class(class_name, class_inst):
    """
    Inspect class and return doc, methods.
    """
    info = {
        'name': class_name,
        'inst': class_inst,
        'doc': '',
        'methods': [],
    }

    # Get class documentation
    class_doc = inspect.getdoc(class_inst)
    if class_doc:
        info['doc'] = class_doc

    # Get class methods
    methods = inspect.getmembers(class_inst, inspect.ismethod)
    for method_name, method_inst in methods:
        info['methods'].append(insp_method(method_name, method_inst))

    return info


def insp_method(method_name, method_inst):
    """
    Inspect a method and return arguments, doc.
    """
    info = {
        'name': method_name,
        'inst': method_inst,
        'args': [],
        'doc': ''
    }

    # Get method arguments
    method_args = inspect.getargspec(method_inst)
    for arg in method_args.args:
        if arg != 'self':
            info['args'].append(arg)

    # Apply default argumument values to arguments
    if method_args.defaults:
        a_pos = len(info['args']) - len(method_args.defaults)
        for pos, default in enumerate(method_args.defaults):
            info['args'][a_pos + pos] = '%s=%s' % (info['args'][a_pos + pos], default)

    # Print method documentation 
    method_doc = inspect.getdoc(method_inst)
    if method_doc:
        info['doc'] = method_doc

    return info


def api_md(file_i):
    apiname = file_i['name'] + " API"
    outstr = apiname.title() + "\n"
    outstr += "%s" % "="*len(apiname)
    tocstr = "%s- [%s](#%s)\n" % ("    " * 0, apiname.title(), fmt_link(apiname))
    author = ''
    if 'author' in file_i['author']:
        author += file_i['author']['author'] + ' '
    if 'email' in file_i['author']:
        author += '<%s>' % (file_i['author']['email'])
    if author:
        outstr += "\n\n* __Author__: %s \n" % (author)

    author_attrs = [
        ('Version', 'version'),
        ('Copyright', 'copyright'),
        ('License', 'license'),
    ]
    for attr_friendly, attr_name in author_attrs:
        if attr_name in file_i['author']:
            outstr += "* __%s__: %s\n" % (attr_friendly, file_i['author'][attr_name])

    outstr += "\nVariables\n----------\n\n"
    tocstr += "%s- [%s](#%s)\n" % ("    " * 1, "Variables", "variables")
    if not file_i['vars']:
        outstr += "This file does not define any variables\n\n"
    for var_name, var_inst in file_i['vars']:
        line = "* `%s`: %s\n" % (var_name, var_inst)
        tocstr += "%s- [%s](#%s)\n" % ("    " * 2, var_name, fmt_link(line))
        outstr += line

    outstr += "\nFunctions\n----------\n\n"
    tocstr += "%s- [%s](#%s)\n" % ("    " * 1, "Functions", "functions")
    if not file_i['functions']:
        outstr += "This file does not define any top-level functions\n\n"
    for function_i in file_i['functions']:
        if function_i['name'].startswith('_'):
            continue
        line = "### def `%s(%s)`\n\n" % (function_i['name'], ', '.join(function_i['args']))
        tocstr += "%s- [%s](#%s)\n" % ("    " * 2, function_i['name'], fmt_link(line))
        outstr += line
        if function_i['doc']:
            outstr += "%s\n" % (inline(function_i['doc']))
            outstr += "\n[Return to TOC](#table-of-contents) \n"
        else:
            outstr += "No documentation for this function\n"
        outstr += "----------\n"

    outstr += "\nClasses\n----------\n"
    tocstr += "%s- [%s](#%s)\n" % ("    " * 1, "Classes", "classes")
    if not file_i['classes']:
        outstr += "This file does not define any classes functions\n"
    for class_i in file_i['classes']:
        line = "\n\n### class `%s()`\n" % (class_i['name'])
        tocstr += "%s- [%s](#%s)\n" % ("    " * 2, class_i['name'], fmt_link(line))
        outstr += line
        if class_i['doc']:
            outstr += "%s\n" % (inline(class_i['doc']))
            outstr += "\n[Return to TOC](#table-of-contents) \n"
        else:
            outstr += "No documentation for this class\n"
        outstr += "----------\n"

        outstr += "\nMethods:\n"
        for method_i in class_i['methods']:
            if method_i['name'].startswith('_'):
                continue
            mname = class_i["name"] + "." + method_i['name']
            line = "#### def `%s(%s)`\n" % (mname, ', '.join(method_i['args']))
            outstr += line
            tocstr += "%s- [%s](#%s)\n" % ("    " * 3, mname, fmt_link(line))
            outstr += "%s\n" % (inline(method_i['doc']))
            outstr += "\n[Return to TOC](#table-of-contents) \n\n"
            outstr += "----------\n"

    return tocstr, outstr


def inline(text):
    text = re.sub("\nExample\:\s*?\n", "\nExample:\n```python\n", text)
    text = re.sub("\nParams\:\s*?\n", "\n```\nParams:\n", text)
    text = re.sub("\nAttributes\:\s*?\n", "\n```\nAttributes:\n", text)

    def params(matchobj):
        body = "\nParams:\n\n|param| description|\n|---|---|\n"
        val = ""
        arg = None
        for line in matchobj.group(1).splitlines():
            line = line.strip()
            m = re.match("([a-zA-Z_\*]*?):", line)
            if m:
                if arg:
                    body += "|%s|%s|\n" % (arg, val.strip())
                arg, val = line.split(":")[:2]
            else:
                val += " " + line
        return body + "\nReturns:\n"
    text = re.sub("\n\s*?Params:\s*?\n(.*?)\n\s*?Returns:\s*?\n", params, text, flags=re.DOTALL)
    for header in ["Example", "Params", "Attributes", "Returns"]:
        text = re.sub("\n%s:\n" % header, "\n**%s:**\n" % header, text)
    return text


def create(modules, pages, readme):
    outstr = "\n"
    tocstr = "Table of Contents\n"
    tocstr += "=================\n\n"
    tocstr += "%s- [%s](#%s)\n" % ("    " * 0, "Table of Contents", "table-of-contents")
    for page in pages:
        with open(page) as f:
            fname = page.split(os.path.sep)[0].split(".")[0]
            outstr += fname.title() + "\n"
            outstr += "%s" % "="*len(fname)
            outstr += "\n%s\n\n" % f.read()
            outstr += "[Return to TOC](#table-of-contents)\n"
            tocstr += "%s- [%s](#%s)\n" % ("    " * 0, fname.title(), fmt_link(fname))
    for mod in modules:
        mtoc, mout = api_md(insp_mod(mod.__name__, mod))
        tocstr += mtoc
        outstr += mout
    with open(readme, "w") as f:
        f.write("%s \n %s" % (tocstr, outstr))