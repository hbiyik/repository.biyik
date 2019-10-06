#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
    Repository, addons.xml and addons.xml.md5 structural generator

        Modifications:

        - by Rodrigo@TVADDONS: Zip plugins/repositories to a "zip" folder
        - BartOtten: Create a repository addon, skip folders without addon.xml, user config file
        - Twilight0: See changelog from version 1.1.2+

    This file is provided "as is", without any warranty whatsoever. Use at your own risk
exists"""
from __future__ import print_function, absolute_import

from re import sub
import os
import hashlib
import zipfile
import shutil
import datetime
from xml.dom import minidom

try:
    from ConfigParser import SafeConfigParser
except ImportError:
    from configparser import SafeConfigParser

__version__ = '1.2.1'

# Load the configuration:
config = SafeConfigParser()
config.read('config.ini')
tools_path = os.path.abspath(os.path.join(os.path.dirname(os.path.realpath(__file__))))
output_path = config.get('locations', 'output_path')
addonid = config.get('addon', 'id')
name = config.get('addon', 'name')
version = config.get('addon', 'version')
author = config.get('addon', 'author')
summary = config.get('addon', 'summary')
description = config.get('addon', 'description')
url = config.get('locations', 'url')

# Script settings:
ask_for_exit_input = False  # asks user to press enter to exit the information window (stdout)
overwrite_existing = True  # this will overwrite existing zip files in output directory
rename_old = False  # will rename older zip files in output directory
copy_additional = True  # will copy additional files such as changelog.txt, icon.png, fanart.jpg
replace_ampersand = True  # will replace solo ampersands (&) with &amp; in order to pass xml validation
compress = True  # Setting this to True will compress with ZIP_DEFLATED method, if False it will use ZIP_STORED
prefix_output = False  # Will prefix output path with an underscore

# Prefix path with underscore in case we need it for quick visual identification of the output path
if prefix_output:
    output_path = ''.join(['_', output_path])

# Ignored files and folders:
ignored_dirs = ['.git', '.idea', '__MACOSX', '.svn', '.vscode']
ignored_files = ['.gitignore', 'gitattributes', '.gitkeep', '.github']
ignored_exts = ['.pyc', '.pyo']

ignored_dirs.extend([output_path, tools_path])


class Generator:

    """
        Generates a new addons.xml file from each addons addon.xml file
        and a new addons.xml.md5 hash file. Must be run from a subdirectory (eg. _tools) of
        the checked-out repo. Only handles single depth folder structure.
    """

    def __init__(self):

        # travel path one up
        os.chdir(os.path.abspath(os.path.join(tools_path, os.pardir)))

        # generate files
        self._pre_run()
        self._generate_repo_files()
        self._generate_addons_file()
        self._generate_md5_file()
        self._generate_zip_files()

    def _pre_run(self):

        # create output  path if it does not exists
        if not os.path.exists(output_path):
            os.makedirs(output_path)

    def _generate_repo_files(self):

        print("Create repository addon")

        with open(tools_path + os.path.sep + "template.xml", "r") as f:
            template_xml = f.read()

        repo_xml = template_xml.format(
            addonid=addonid,
            name=name,
            version=version,
            author=author,
            summary=summary,
            description=description,
            url=url,
            output_path=output_path
        )

        # save file
        if not os.path.exists(addonid):
            os.makedirs(addonid)

        self._save_file(repo_xml, file=addonid + os.path.sep + "addon.xml")

    def _generate_zip_files(self):

        global version, addonid

        addons = os.listdir(".")

        # loop thru and add each addons addon.xml file
        for addon in addons:

            # create path
            _path = os.path.join(addon, "addon.xml")

            # skip path if it has no addon.xml
            if not os.path.isfile(_path):
                continue

            try:

                # skip any file or .git folder
                if not (os.path.isdir(addon) or addon in ignored_dirs):
                    continue

                # create path
                _path = os.path.join(addon, "addon.xml")

                # split lines for stripping
                document = minidom.parse(_path)

                for parent in document.getElementsByTagName("addon"):
                    version = parent.getAttribute("version")
                    addonid = parent.getAttribute("id")

                self._generate_zip_file(addon, version, addonid)

            except Exception as e:

                print(e)

    def _generate_zip_file(self, path, version, addonid):

        print("Generate zip file for " + addonid + " " + version)

        filename = path + "-" + version + ".zip"

        compression = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED

        try:

            zip = zipfile.ZipFile(filename, 'w', compression=compression)

            for root, dirs, files in os.walk(path + os.path.sep):

                for ignored_dir in ignored_dirs:
                    if ignored_dir in dirs:
                        dirs.remove(ignored_dir)

                for ignored_file in ignored_files:
                    if ignored_file in files:
                        files.remove(ignored_file)

                zip.write(os.path.join(root))

                for file in files:
                    skip = False
                    for ignored_ext in ignored_exts:
                        if file.endswith(ignored_ext):
                            skip = True
                            break
                    if not skip:
                        zip.write(os.path.join(root, file))
            zip.close()

            if not os.path.exists(output_path + addonid):
                os.makedirs(output_path + addonid)

            destination = output_path + addonid + os.path.sep + filename
            output_exists = os.path.isfile(destination)

            if output_exists and rename_old:
                os.rename(destination, destination + "." + datetime.datetime.now().strftime("%Y%m%d%H%M%S"))

            if output_exists and overwrite_existing:

                shutil.move(filename, destination)

            elif output_exists and not overwrite_existing:

                os.remove(filename)

            else:

                shutil.move(filename, destination)

        except Exception as e:

            print(e)

    def _generate_addons_file(self):
        print("Generating addons.xml file")
        # addon list
        addons = os.listdir(".")
        # final addons text
        addons_xml = u"<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<addons>\n"
        # loop thru and add each addons addon.xml file
        for addon in addons:
            # create path
            _path = os.path.join(addon, "addon.xml")
            # skip path if it has no addon.xml
            if not os.path.isfile(_path):
                continue
            try:
                # split lines for stripping
                try:
                    with open(_path, "r") as f:
                        xml_lines = f.read().splitlines()
                except UnicodeDecodeError:
                    # noinspection PyArgumentList
                    with open(_path, "r", encoding='utf-8') as f:
                        xml_lines = f.read().splitlines()
                # new addon
                addon_xml = ""
                # loop thru cleaning each line
                for line in xml_lines:
                    # skip encoding format line
                    if line.find("<?xml") >= 0:
                        continue
                    # replace "&" with &amp; in order to pass xml validation:
                    if replace_ampersand:
                        line = sub(r'&(?!amp;)', r'&amp;', line)
                    # add line
                    try:
                        addon_xml += unicode(line.rstrip() + "\n", "utf-8")
                    except NameError:
                        addon_xml += line.rstrip() + "\n"
                # we succeeded so add to our final addons.xml text
                addons_xml += addon_xml.rstrip() + "\n\n"
            except Exception as e:
                # missing or poorly formatted addon.xml
                print("Excluding %s for %s" % (_path, e,))
        # clean and add closing tag
        addons_xml = addons_xml.strip() + u"\n</addons>\n"
        # save file
        self._save_file(addons_xml, file=output_path + "addons.xml")

    def _generate_md5_file(self):

        print("Generating addons.xml.md5 file")

        try:

            # create a new md5 hash
            try:
                # noinspection PyArgumentList
                with open(output_path + "addons.xml", encoding='utf-8') as f:
                    addons_xml = f.read()
            except TypeError:
                with open(output_path + "addons.xml") as f:
                    addons_xml = f.read()

            try:
                m = hashlib.md5(addons_xml).hexdigest()
            except TypeError:
                # noinspection PyArgumentList
                m = hashlib.md5(bytes(addons_xml, encoding='utf-8')).hexdigest()

            m = m + '  ' + 'addons.xml'

            # save file
            self._save_file(m, file=output_path + "addons.xml.md5")
        except Exception as e:
            # oops
            print("An error occurred creating addons.xml.md5 file!\n%s" % (e,))

    def _save_file(self, data, file):

        try:

            # write data to the file
            try:
                with open(file, "w") as f:
                    f.write(data)
            except UnicodeEncodeError:
                with open(file, "wb") as f:
                    try:
                        # noinspection PyArgumentList
                        f.write(bytes(data, encoding='utf-8'))
                    except TypeError:
                        f.write(data.encode('utf-8'))

        except Exception as e:
            # oops
            print("An error occurred saving %s file!\n%s" % (file, e,))


class Copier:

    def __init__(self):

        self._copy_additional_files()

    def _copy_additional_files(self):

        os.chdir(os.path.abspath(os.path.join(tools_path, os.pardir)))
        addons = os.listdir(".")

        for addon in addons:

            xml_file = os.path.join(addon, "addon.xml")

            if not os.path.isfile(xml_file):
                continue
            if not (os.path.isdir(addon) or addon in ignored_dirs):
                continue

            document = minidom.parse(xml_file)

            for parent in document.getElementsByTagName("addon"):

                version = parent.getAttribute("version")

                # Changelog.txt
                try:
                    if os.path.isfile(output_path + addon + os.path.sep + "changelog-" + version + ".txt") and overwrite_existing:
                        shutil.copy(addon + os.path.sep + "changelog.txt", output_path + addon + os.path.sep + "changelog-" + version + ".txt")
                    else:
                        shutil.copy(addon + os.path.sep + "changelog.txt", output_path + addon + os.path.sep + "changelog-" + version + ".txt")
                except IOError:
                    pass

                # Icon.png
                try:
                    if os.path.isfile(output_path + addon + os.path.sep + "icon.png") and overwrite_existing:
                        shutil.copy(addon + os.path.sep + "icon.png", output_path + addon + os.path.sep + "icon.png")
                    else:
                        shutil.copy(addon + os.path.sep + "icon.png", output_path + addon + os.path.sep + "icon.png")
                except IOError:
                    pass

                # Fanart.jpg
                try:
                    if os.path.isfile(output_path + addon + os.path.sep + "fanart.jpg") and overwrite_existing:
                        shutil.copy(addon + os.path.sep + "fanart.jpg", output_path + addon + os.path.sep + "fanart.jpg")
                    else:
                        shutil.copy(addon + os.path.sep + "fanart.jpg", output_path + addon + os.path.sep + "fanart.jpg")
                except IOError:
                    pass


if __name__ == "__main__":

    print('Repository bootstrapper script, version: {0}'.format(__version__))

    Generator()

    if copy_additional:
        Copier()

    print("Process completed")

    if ask_for_exit_input:

        try:

            input("Press enter to exit")

        except SyntaxError:

            pass
