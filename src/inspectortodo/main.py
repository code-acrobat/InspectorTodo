# Copyright 2018 TNG Technology Consulting GmbH, Unterföhring, Germany
# Licensed under the Apache License, Version 2.0 - see LICENSE.md in project root directory

import logging
import os

import click

from .config import load_or_create_configfile, get_config_value, get_config_value_as_list, get_multiline_config_value_as_list, set_config_value
from .todo_finder import TodoFinder
from .todo_validation import validate_todos

log = logging.getLogger()


@click.command()
@click.argument('ROOT_DIR', required=True)
@click.argument('ISSUE_PATTERN', required=True)
@click.option('--version-pattern', help='Regular expression for version references in todos.')
@click.option('--version', help='Current version.')
@click.option('--versions', help='List of versions allowed in todos.'
                                 'Versions are separated by comma and increase from left to right.')
@click.option('--configfile', help='Config file to be used. If file does not exist, default config is created.'
                                   'If not set, all config values are treated as None.')
@click.option('--jira-user', help="Jira username")
@click.option('--jira-password', help="Jira password")
@click.option('--xml', help="Output file for JUnit like xml which contains all found todos.")
@click.option('--log-level', default='INFO', help="Set the log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)")
def main(root_dir, issue_pattern, version_pattern, version, versions, configfile, jira_user, jira_password, xml,
         log_level):
    r"""
    ROOT_DIR is the directory to inspect recursively.

    ISSUE_PATTERN is a regular expression for issue references in todos. The regular expression has to match the entire
    issue reference, e.g. IT-\d+
    """

    logging.basicConfig(level=log_level.upper(), format='[%(levelname)s] %(message)s')

    root_dir = os.path.normpath(os.path.abspath(root_dir))
    issue_pattern = issue_pattern.strip()
    versions = versions.split(',') if versions else versions

    if configfile:
        load_or_create_configfile(configfile)
    if jira_user:
        set_config_value('jira_server', 'username', jira_user)
    if jira_password:
        set_config_value('jira_server', 'password', jira_password)

    paths_whitelist = []
    if get_config_value('files', 'whitelist'):
        paths_whitelist = get_multiline_config_value_as_list('files', 'whitelist')

    todo_finder = TodoFinder(root_dir, paths_whitelist)
    todos = todo_finder.find()

    if todos:
        validate_todos(todos, issue_pattern, version_pattern, version, versions)

    if xml:
        todos_with_category = categorize_todos(todos)
        for category in todos_with_category.keys():
            xml_suffix = '' if category == 'default' else "." + category
            write_xml_file(xml + xml_suffix, todos_with_category[category])

def categorize_todos(todos):
    result = {}
    for t in todos:
        category = get_effective_category(t)
        if not category in result:
            result[category] = []
        result[category].append(t)
    return result

def get_effective_category(todo):
    mapped_categories = get_config_value_as_list('category', 'mapped')
    return 'default' if not todo.get_category() in mapped_categories else todo.get_category()

def write_xml_file(filename, todos):
    with open(filename, 'w', encoding='UTF-8') as xml_file:
        print_xml(xml_file, todos)


def print_xml(xml_file, todos):
    num_failed = len([todo for todo in todos if not todo.is_valid])

    xml_file.write('<?xml version="1.0" encoding="UTF-8"?>\n')
    xml_file.write('<testsuite name="InspectorTodo" tests="{}" failures="{}">\n'.format(len(todos), num_failed))
    for todo in todos:
        todo.print_xml(xml_file)
    xml_file.write('</testsuite>\n')
