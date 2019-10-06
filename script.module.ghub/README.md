Table of Contents
=================

- [Table of Contents](#table-of-contents)
- [Introduction](#introduction)
- [Ghub Api](#ghub-api)
    - [Variables](#variables)
    - [Functions](#functions)
        - [load](#def-loaduname-rname-branch-commitnone-path-period24)
    - [Classes](#classes)
 
 
Introduction
============
script.module.ghub is a KODI/XBMC addon module, that helps you to load a module from github in runtime.

[Return to TOC](#table-of-contents)
Ghub Api
========
Variables
----------

This file does not define any variables


Functions
----------

### def `load(uname, rname, branch, commit=None, path=[], period=24)`

Loads, caches, and arranges paths for a repo from github.
This module, downloads a github repo to 
userdata/addon_data/scirpt.module.gub/uname/package/branch/commit
It also updates the package automatically in a given period (24h default)
Note that this is not a package manager and does not do any dependency check

**Example:**
```python
    import ghub
    
    ghub.load("hbiyik", "script.module.boogie", "master", None, ["lib"])
    
    #now you can safely import this module
    import boogie

```
**Params:**

|param| description|
|---|---|
|uname|github username|
|rname|repository name|
|branch|github branch (ie master), if this parameter is None, latest tagged version is used.|
|commit|[optional,None] commit of the specified branch, if None is specified latest commit is fetched, if brach is None, this parameter is dismissed|
|path|[optional,[]] list of directories pointing to the root directory of source ie, if source is in lib/src folder path should be ["lib", "src"]|

**Returns:**
    None

[Return to TOC](#table-of-contents) 
----------

Classes
----------
This file does not define any classes functions
