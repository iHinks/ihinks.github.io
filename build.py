#!/usr/bin/env python3

import os
import re
import sys
import json
import inspect
import subprocess
import collections

from typing import Dict, List
from datetime import datetime

Config = collections.namedtuple(
    "Config", ["verbosity", "prefix", "target", "templates"]
)


def cleanup():
    for f in [
        f"{config.target}/index.html",
        f"{config.target}/news.html",
        f"{config.target}/pubs.html",
        f"{config.target}/main.css",
    ]:
        try:
            os.remove(f)
        except Exception as _:
            pass


# for printing with colours
class bcolors:
    SUCCESS = "\033[92m"
    OKCYAN = "\033[96m"
    OKBLUE = "\033[94m"
    WARNING = "\033[93m"
    ERROR = "\033[91m"
    BOLD = "\033[1m"
    ENDC = "\033[0m"


# Helper functions
def status(msg: str, priority=1):
    if priority <= config.verbosity:
        if priority == 0:
            divider = "*" * len(msg)
            msg = f"{divider}\n{msg}\n{divider}"
            print(f"{bcolors.BOLD}{bcolors.OKBLUE}{msg}{bcolors.ENDC*2}")
        elif priority == 1:
            print(f"{bcolors.BOLD}{bcolors.OKCYAN}{msg}{bcolors.ENDC*2}")
        else:
            print(f"{bcolors.OKCYAN}{msg}{bcolors.ENDC}")


def success(msg: str):
    msg = f"SUCCESS: {msg}"
    divider = "*" * len(msg)
    msg = f"{divider}\n{msg}\n{divider}"

    print(f"{bcolors.SUCCESS}{msg}{bcolors.ENDC}")


def warning(msg: str):
    msg = f"WARNING: {msg}"
    divider = "*" * len(msg)
    msg = f"{divider}\n{msg}\n{divider}"

    print(f"{bcolors.WARNING}{msg}{bcolors.ENDC}")


def error(msg: str):
    msg = f"ERROR: {msg}"
    divider = "*" * len(msg)
    msg = f"{divider}\n{msg}\n{divider}"

    print(f"{bcolors.ERROR}{msg}{bcolors.ENDC}")
    cleanup()
    exit(1)


def warn_if_not(cond: bool, msg: str):
    if not cond:
        warning(msg)


def fail_if_not(cond: bool, msg: str):
    if not cond:
        error(msg)


def fill_if_missing(json: Dict[str, str], field: str, default=""):
    if not field in json:
        json[field] = default

    return json


def is_federicos(name):
    try:
        repo_url = subprocess.getoutput(
            f"git -C {config.prefix} config --get remote.origin.url"
        ).split()[0]
    except Exception as _:
        repo_url = ""

    federicos_url = "git@github.com:FedericoAureliano/FedericoAureliano.github.io.git"
    federicos_name = "Federico Mora Rocha"

    return name == federicos_name and repo_url == federicos_url


def check_tracker(tracker):
    status("- Sanity check on tracker script")

    fail_if_not(
        "federicoaureliano" not in tracker,
        "Please use your own tracker in data/meta.json",
    )


def check_cname():
    status("- Sanity check on CNAME")

    path = os.path.join(config.target, "CNAME")
    try:
        with open(path) as f:
            cname = f.read()
    except Exception as _:
        status(f"  - Couldn't load CNAME---treating it as empty.", 1)
        cname = ""

    fail_if_not(
        "federico.morarocha.ca" != cname, f"Please use your own CNAME at {path}"
    )


def read_data(json_file_name: str, optional: bool):
    path = os.path.join(config.prefix, json_file_name)
    try:
        with open(path) as f:
            status(f"- loading {path}")
            data = json.load(f)
    except Exception as _:
        fail_if_not(
            optional,
            f"Failed to parse {path}. Check your commas, braces, and if the file exists.",
        )
        # fail_if_not will exit if needed so the code below will only run if this data is optional
        status(f"Failed to load {path}---treating it as empty.", 0)
        data = {}

    return data


def read_template(template_file_name: str, optional: bool):
    path = os.path.join(config.prefix, template_file_name)
    try:
        with open(path) as f:
            status(f"- loading {path}")
            data = f.read()
    except Exception as _:
        fail_if_not(optional, f"Failed to read {path}. Does it exist?")
        # fail_if_not will exit if needed
        status(f"Couldn't load {path}---treating it as empty.", 0)
        data = ""

    return data


def write_file(file_name: str, contents: str):
    path = os.path.join(config.prefix, file_name)
    if contents == "":
        return

    with open(path, "w") as target:
        status(f"- writing {path}")
        target.write(contents)


def replace_placeholders(text: str, map: Dict[str, str]):
    newtext = text

    for k in map:
        newtext = newtext.replace(k + "-placeholder", map[k])

    return newtext


# Define functions for website pieces


def header(has_dark):
    if has_dark:
        button = """<label class="switch-mode">
    <input type="checkbox" id="mode">
    <span class="slider round"></span>
    </label>
    <script src="mode.js"></script>
    """
    else:
        button = ""

    out = '<header><div id="scroller"></div>\n%s</header>\n' % button
    return out


def build_news(news: List[Dict[str, str]], count: int, standalone: bool):
    if count > len(news):
        count = len(news)

    if count <= 0:
        return ""

    status("\nAdding news:")
    news_list = ""

    for n in news[:count]:
        status("- " + n["date"])
        news_map = {
            "news-date": n["date"],
            "news-text": n["text"],
        }
        news_list += replace_placeholders(news_item_html, news_map)

    news_html = '<div class="section">\n'

    if count != len(news):
        link = '<a href="./news.html">See all posts</a>'
        news_html += (
            '<h1>Recent News <small style="font-weight: 300; float: right; padding-top: 0.23em">(%s)</small></h1>\n'
            % link
        )
    elif standalone:
        link = '<a href="./index.html">%s</a>' % meta_json["name"]
        news_html += (
            '<h1>News <small style="font-weight: 300; float: right; padding-top: 0.23em">%s</small></h1>\n'
            % link
        )
    else:
        news_html += "<h1>News</h1>\n"

    news_html += '<div class="hbar"></div>\n'
    news_html += '<div id="news">\n'
    news_html += news_list
    news_html += "</div>\n"  # close news
    news_html += "</div>\n"  # close section

    return news_html


# Helper function to decide what publication sections to include
def get_pub_titles(pubs: List[Dict[str, str]]):
    titles = set()
    for p in pubs:
        titles.add(p["section"])

    return sorted(list(titles))


def some_not_selected(pubs: List[Dict[str, str]]):
    for p in pubs:
        if not p["selected"]:
            return True

    return False


def build_authors(authors):
    item = ""

    authors_split = [
        "%s%s%s"
        % (
            a["first"][0] + ". ",
            a["middle"][0] + ". " if "middle" in a and a["middle"] else "",
            a["last"],
        )
        for a in authors
    ]
    for i in range(len(authors_split)):
        entry = authors_split[i]
        if i < len(authors_split) - 2:
            entry += ",\n"
        if i == len(authors_split) - 2:
            entry += " and\n"
        authors_split[i] = entry

    if len("".join(authors_split)) > 80:
        authors_split.insert(len(authors_split) // 2, '<br class="bigscreen">')
    item += "".join(authors_split)
    return item


def build_icons(p):
    item = ""
    item += (
        '<a href="'
        + p["link"]
        + '" alt="[PDF] " target="_blank" rel="noopener noreferrer"><img class="paper-icon" src="%s"/><img class="paper-icon-dark" src="%s"/></a>'
        % (style_json["paper-img"], style_json["paper-img-dark"])
        if p["link"]
        else ""
    )
    item += (
        '<a href="'
        + p["extra"]
        + '" alt="[Extra] " target="_blank" rel="noopener noreferrer"><img class="paper-icon" src="%s"/><img class="paper-icon-dark" src="%s"/></a>'
        % (style_json["extra-img"], style_json["extra-img-dark"])
        if p["extra"]
        else ""
    )
    item += (
        '<a href="'
        + p["slides"]
        + '" alt="[Slides] " target="_blank" rel="noopener noreferrer"><img class="paper-icon" src="%s"/><img class="paper-icon-dark" src="%s"/></a>'
        % (style_json["slides-img"], style_json["slides-img-dark"])
        if p["slides"]
        else ""
    )
    item += (
        '<a href="'
        + p["bibtex"]
        + '" alt="[Bibtex] " target="_blank" rel="noopener noreferrer"><img class="paper-icon" src="%s"/><img class="paper-icon-dark" src="%s"/></a>'
        % (style_json["bibtex-img"], style_json["bibtex-img-dark"])
        if p["bibtex"]
        else ""
    )
    return item


def build_pubs_inner(pubs: List[Dict[str, str]], title: str, full: bool):
    if title == "":
        return ""

    pubs_list = ""

    for p in pubs:
        if title == p["section"] and (p["selected"] or full):
            status("- " + p["title"])

            paper_conference = p["venue"]["short"] + " '" + p["year"][-2:]
            if len(paper_conference) > 8:
                paper_conference = f'<div class="bigscreen"><small>{paper_conference}</small></div><div class="smallscreen">{paper_conference}</div>'

            title_split = p["title"].split()
            if len(p["title"]) >= 80:
                title_split.insert(len(title_split) // 2, '<br class="bigscreen">')
            paper_title = " ".join(title_split)

            paper_map = {
                "paper-title": paper_title,
                "paper-authors": build_authors(p["authors"]),
                "paper-conference": paper_conference,
                "paper-icons": build_icons(p),
            }
            pubs_list += replace_placeholders(paper_html, paper_map)

    pubs_html = '<h3 id="%spublications">%s</h3>' % (title, title)
    pubs_html += pubs_list

    return pubs_html


def build_pubs(pubs: List[Dict[str, str]], full: bool):
    if len(pubs) == 0:
        return ""

    status("\nAdding publications:")

    pubs_html = '<div class="section">\n'

    if some_not_selected(pubs) and not full:
        pubs_html += '<h1>Selected Publications <small style="font-weight: 300; float: right; padding-top: 0.23em">(<a href="./pubs.html">See all publications</a>)</small></h1>'
    elif full:
        link = '<a href="./index.html">%s</a>' % meta_json["name"]
        pubs_html += (
            '<h1>Publications <small style="font-weight: 300; float: right; padding-top: 0.23em">%s</small></h1>\n'
            % link
        )
    else:
        pubs_html += "<h1>Publications</h1>"

    pubs_html += '<div class="hbar"></div>\n'
    pubs_html += '<div id="publications">\n'

    titles = get_pub_titles(pubs)

    for i in range(len(titles)):
        title = titles[i]
        pubs_html += build_pubs_inner(pubs, title, full)

    pubs_html += "</div>\n"  # close pubs
    pubs_html += "</div>\n"  # close section

    return pubs_html

def build_name_header(profile: Dict[str, str]):

    # Name at top
    #name_header_html = '<div class="name">\n' # name at top
    #name_header_html += '<h1>' + profile["name"] + '</h1>\n'
    #name_header_html += "</div>\n"  # close name div

    # Menu of main links under name
    name_header_html = '<div class="main_links">\n' # main links
    name_header_html += '<div class="row">\n' # start single row
    name_header_html += '<div class="left_col"> <h1>' + profile["name"] + '</h1> </div>' # name
    name_header_html += '<div class="right_col">\n' 
    name_header_html += '<h1><a href="%s" target="_blank" rel="noopener noreferrer">CV</a>' % profile["cv"] + ' | ' + '<a href="%s" target="_blank" rel="noopener noreferrer">Google Scholar</a>' % profile["scholar"] + ' | ' + '<a href="%s" target="_blank" rel="noopener noreferrer">GitHub</a>' % profile["github"] + ' | ' + '<a href="mailto:%s">email</a>' % profile["email"] + '</h1>\n'
    # name_header_html += '<object width="800px" height="400px" data="https://s3.amazonaws.com/dq-blog-files/pandas-cheat-sheet.pdf"></object>'
    # name_header_html += '<script src="https://coolors.co/palette-widget/widget.js"></script><script data-id="02654346318810674">new CoolorsPaletteWidget("02654346318810674", ["F6F0DE","C65B30","42A677","333E8C","F6B144"]); </script>'
    # name_header_html += '<h1><a href="%s">CV</a>' % profile["cv"] + '</h1>' +  '<h1><a href="%s"> | Google Scholar</a>' % profile["scholar"] + '</h1>' + '<h1><a href="%s"> | GitHub</a>' % profile["github"] + '</h1>' + '<h1><a href="%s"> | Email</a>' % profile["email"] + '</h1>\n'
    name_header_html += '</div>\n' # CV link
    # name_header_html += '<div class="column">\n' + '<h1><a href="%s">CV</a>' % profile["cv"] + '</h1> </div>\n' # CV link
    # name_header_html += '<div class="column">\n' + '<h1><a href="%s">Google Scholar</a>' % profile["scholar"] + '</h1> </div>\n' # Google Scholar link
    # name_header_html += '<div class="column">\n' + '<h1><a href="%s">GitHub</a>' % profile["github"] + '</h1> </div>\n' # GitHub link
    # name_header_html += '<div class="column">\n' + '<h1><a href="%s">Email</a>' % profile["email"] + '</h1> </div>\n' # Email link
    name_header_html += "</div>\n"  # close rows
    name_header_html += "</div>\n"  # close main links

    return name_header_html

def build_profile(profile: Dict[str, str], style: Dict[str, str]):
    profile_html = '<div class="profile">\n'
    profile_html += (
        '<img class="headshot-img" src="%s" alt="Headshot"/><img class="headshot-img-dark" src="%s" alt="Headshot"/>\n' % (style["headshot-img"], style["headshot-img-dark"])
    )
    profile_html += "<p>" + "</p><p>".join(profile["about"].split("\n")) + "</p>"
    if "research" in profile:
        profile_html += "<p>" + "</p><p>".join(profile["research"].split("\n")) + "</p>"
    # profile_html += "\n<p>Here is my "
    # profile_html += '<a href="%s">CV</a> and ' % profile["cv"]
    # profile_html += '<a href="%s">Google Scholar</a>. ' % profile["scholar"]
    # profile_html += "You can reach me at %s." % profile["email"]
    # profile_html += "</p>\n"  # close description paragraph
    profile_html += "</div>\n"  # close profile

    return profile_html

def add_notes(html: str, notes: Dict[str, str]):
    status("\nAdding notes:", 2)

    toreplace = sorted(notes.keys(), key=len, reverse=True)

    for name in toreplace:
        pos = html.find(name)
        while pos != -1:
            prefix = html[:pos]
            suffix = html[pos:]

            open = html[:pos].count("<abbr title=")
            close = html[:pos].count("</abbr>")

            status(f"- {name} {pos} {open} {close}", 2)
            target = name + " "
            if pos >= 0 and open == close:
                target = '<abbr title="%s">%s</abbr>' % (notes[name], name)
                suffix = suffix.replace(name, target, 1)
                html = prefix + suffix

            start = (len(prefix) - len(name)) + len(
                target
            )  # we got rid of name and replaced it with target
            tmp = html[start:].find(name)
            pos = tmp + start if tmp >= 0 else tmp

    return html


def add_links(html: str, links: Dict[str, str]):
    status("\nAdding links:", 2)

    toreplace = sorted(links.keys(), key=len, reverse=True)

    for name in toreplace:
        pos = html.find(name)
        while pos != -1:
            prefix = html[:pos]
            suffix = html[pos:]

            open = html[:pos].count("<a href=")
            close = html[:pos].count("</a>")

            status(f"- {name} {pos} {open} {close}", 2)
            target = name + " "
            if pos >= 0 and open == close:
                target = '<a href="%s" target="_blank" rel="noopener noreferrer">%s</a>' % (links[name], name)
                suffix = suffix.replace(name, target, 1)
                html = prefix + suffix

            start = (len(prefix) - len(name)) + len(
                target
            )  # we got rid of name and replaced it with target
            tmp = html[start:].find(name)
            pos = tmp + start if tmp >= 0 else tmp

    return html

#     <!-- This SVG is from https://codepen.io/Ali_Farooq_/pen/gKOJqx -->
def add_blobs(style: Dict[str, str]): 
    blob_html = '<div class="blob"><svg xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 310 350"><path d="M156.4,339.5c31.8-2.5,59.4-26.8,80.2-48.5c28.3-29.5,40.5-47,56.1-85.1c14-34.3,20.7-75.6,2.3-111  c-18.1-34.8-55.7-58-90.4-72.3c-11.7-4.8-24.1-8.8-36.8-11.5l-0.9-0.9l-0.6,0.6c-27.7-5.8-56.6-6-82.4,3c-38.8,13.6-64,48.8-66.8,90.3c-3,43.9,17.8,88.3,33.7,128.8c5.3,13.5,10.4,27.1,14.9,40.9C77.5,309.9,111,343,156.4,339.5z"/></svg></div>'
    blob_html += '<div class="blob2"><svg xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 310 350"><path d="M156.4,339.5c31.8-2.5,59.4-26.8,80.2-48.5c28.3-29.5,40.5-47,56.1-85.1c14-34.3,20.7-75.6,2.3-111  c-18.1-34.8-55.7-58-90.4-72.3c-11.7-4.8-24.1-8.8-36.8-11.5l-0.9-0.9l-0.6,0.6c-27.7-5.8-56.6-6-82.4,3c-38.8,13.6-64,48.8-66.8,90.3c-3,43.9,17.8,88.3,33.7,128.8c5.3,13.5,10.4,27.1,14.9,40.9C77.5,309.9,111,343,156.4,339.5z"/></svg></div>'
    blob_html += '<div class="blob3"><svg xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 310 350"><path d="M156.4,339.5c31.8-2.5,59.4-26.8,80.2-48.5c28.3-29.5,40.5-47,56.1-85.1c14-34.3,20.7-75.6,2.3-111  c-18.1-34.8-55.7-58-90.4-72.3c-11.7-4.8-24.1-8.8-36.8-11.5l-0.9-0.9l-0.6,0.6c-27.7-5.8-56.6-6-82.4,3c-38.8,13.6-64,48.8-66.8,90.3c-3,43.9,17.8,88.3,33.7,128.8c5.3,13.5,10.4,27.1,14.9,40.9C77.5,309.9,111,343,156.4,339.5z"/></svg></div>'
    blob_html += '<div class="blob4"><svg xmlns:xlink="http://www.w3.org/1999/xlink" version="1.1" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 310 350"><path d="M156.4,339.5c31.8-2.5,59.4-26.8,80.2-48.5c28.3-29.5,40.5-47,56.1-85.1c14-34.3,20.7-75.6,2.3-111  c-18.1-34.8-55.7-58-90.4-72.3c-11.7-4.8-24.1-8.8-36.8-11.5l-0.9-0.9l-0.6,0.6c-27.7-5.8-56.6-6-82.4,3c-38.8,13.6-64,48.8-66.8,90.3c-3,43.9,17.8,88.3,33.7,128.8c5.3,13.5,10.4,27.1,14.9,40.9C77.5,309.9,111,343,156.4,339.5z"/></svg></div>'
    return blob_html


def build_index(
    profile_json: Dict[str, str],
    news_json: List[Dict[str, str]],
    pubs_json: List[Dict[str, str]],
    links: Dict[str, str],
    notes: Dict[str, str],
    has_dark: bool,
):
    body_html = "<body>\n"
    body_html += header(has_dark)
    body_html += add_blobs(style_json)
    body_html += '<div class="content">\n'
    body_html += build_name_header(profile_json)
    body_html += build_profile(profile_json, style_json)
    body_html += build_news(news_json, 5, False)
    body_html += build_pubs(pubs_json, False)
    body_html += "</div>\n"
    body_html += footer_html
    body_html += "</body>\n"

    index_page = "<!DOCTYPE html>\n"
    index_page += '<html lang="en">\n'
    index_page += head_html + "\n\n"
    index_page += add_notes(add_links(body_html, links), notes)
    index_page += "</html>\n"

    return inspect.cleandoc(index_page)


def build_news_page(
    news_json: List[Dict[str, str]],
    links: Dict[str, str],
    notes: Dict[str, str],
    has_dark: bool,
):
    content = build_news(news_json, len(news_json), True)

    if content == "":
        return ""

    body_html = "<body>\n"
    body_html += header(has_dark)
    body_html += '<div class="content">\n'
    body_html += content
    body_html += "</div>\n"
    body_html += footer_html
    body_html += "</body>\n"

    news_html = "<!DOCTYPE html>\n"
    news_html += '<html lang="en">\n'
    news_html += head_html + "\n\n"
    news_html += add_notes(add_links(body_html, links), notes)
    news_html += "</html>\n"

    return inspect.cleandoc(news_html)


def build_pubs_page(
    pubs_json: List[Dict[str, str]],
    links: Dict[str, str],
    notes: Dict[str, str],
    has_dark: bool,
):
    content = build_pubs(pubs_json, True)

    if content == "":
        return ""

    body_html = "<body>\n"
    body_html += header(has_dark)
    body_html += '<div class="content">\n'
    body_html += content
    body_html += "</div>\n"
    body_html += footer_html
    body_html += "</body>\n"

    pubs_html = "<!DOCTYPE html>\n"
    pubs_html += '<html lang="en">\n'
    pubs_html += head_html + "\n\n"
    pubs_html += add_notes(add_links(body_html, links), notes)
    pubs_html += "</html>\n"

    return inspect.cleandoc(pubs_html)


if __name__ == "__main__":
    config = Config(
        verbosity=int(sys.argv[1]) if len(sys.argv) > 1 else 0,
        prefix=os.path.dirname(__file__),
        target="docs",
        templates="templates",
    )

    cleanup()

    # Load json files
    status("Loading json files:")

    meta_json = read_data("data/meta.json", optional=False)
    fail_if_not("name" in meta_json, 'Must include a "name" in data/meta.json!')
    fail_if_not(
        "description" in meta_json, 'Must include a "description" in data/meta.json!'
    )
    fail_if_not("favicon" in meta_json, 'Must include a "favicon" in data/meta.json!')
    fill_if_missing(meta_json, "tracker")

    style_json = read_data("data/style.json", optional=False)
    fail_if_not(
        "font-color" in style_json, 'Must include a "font-color" in data/style.json!'
    )
    fail_if_not(
        "background-color" in style_json,
        'Must include a "background-color" in data/style.json!',
    )
    fail_if_not(
        "header-color" in style_json,
        'Must include a "header-color" in data/style.json!',
    )
    fail_if_not(
        "accent-color" in style_json,
        'Must include a "accent-color" in data/style.json!',
    )
    fail_if_not(
        "link-hover-color" in style_json,
        'Must include a "link-hover-color" in data/style.json!',
    )
    fail_if_not(
        "divider-color" in style_json,
        'Must include a "divider-color" in data/style.json!',
    )
    fail_if_not(
        "paper-img" in style_json, 'Must include a "paper-img" in data/style.json!'
    )
    fail_if_not(
        "extra-img" in style_json, 'Must include a "extra-img" in data/style.json!'
    )
    fail_if_not(
        "slides-img" in style_json, 'Must include a "slides-img" in data/style.json!'
    )
    fail_if_not(
        "bibtex-img" in style_json, 'Must include a "bibtex-img" in data/style.json!'
    )

    fill_if_missing(style_json, "font-color-dark", style_json["font-color"])
    fill_if_missing(style_json, "background-color-dark", style_json["background-color"])
    fill_if_missing(style_json, "header-color-dark", style_json["header-color"])
    fill_if_missing(style_json, "accent-color-dark", style_json["accent-color"])
    fill_if_missing(style_json, "link-hover-color-dark", style_json["link-hover-color"])
    fill_if_missing(style_json, "divider-color-dark", style_json["divider-color"])
    fill_if_missing(style_json, "paper-img-dark", style_json["paper-img"])
    fill_if_missing(style_json, "extra-img-dark", style_json["extra-img"])
    fill_if_missing(style_json, "slides-img-dark", style_json["slides-img"])
    fill_if_missing(style_json, "bibtex-img-dark", style_json["bibtex-img"])
    fill_if_missing(style_json, "headshot-img-dark", style_json["headshot-img"])

    profile_json = read_data("data/profile.json", optional=False)
    fail_if_not(
        "headshot" in profile_json,
        'Must include a "headshot" field in data/profile.json!',
    )
    fail_if_not(
        "about" in profile_json,
        'Must include a "about" field in data/profile.json!',
    )
    fail_if_not("cv" in profile_json, 'Must include a "cv" field in data/profile.json!')
    fail_if_not(
        "email" in profile_json, 'Must include a "email" field in data/profile.json!'
    )
    fail_if_not(
        "scholar" in profile_json,
        'Must include a "scholar" field in data/profile.json!',
    )

    # These next four can be empty
    news_json = read_data("data/news.json", optional=True)
    for news in news_json:
        fail_if_not(
            "date" in news,
            'Must include a "date" field for each news in data/news.json!',
        )
        fail_if_not(
            "text" in news,
            'Must include a "text" field for each news in data/news.json!',
        )

    dates = [datetime.strptime(n["date"], "%m/%Y") for n in news_json]
    warn_if_not(
        dates == sorted(dates, reverse=True),
        "The dates in data/news.json are not in order.",
    )

    pubs_json = read_data("data/publications.json", optional=True)
    for pub in pubs_json:
        fail_if_not(
            "title" in pub,
            'Must include a "title" field for each pub in data/publications.json!',
        )
        fail_if_not(
            "venue" in pub,
            'Must include a "venue" field for each pub in data/publications.json!',
        )
        fail_if_not(
            "short" in pub["venue"],
            'Must include a "short" subfield for each pub venue in data/publications.json!',
        )
        fail_if_not(
            "name" in pub["venue"],
            'Must include a "name" subfield for each pub venue in data/publications.json!',
        )
        fail_if_not(
            "authors" in pub,
            'Must include a "authors" field for each pub in data/publications.json!',
        )

        fill_if_missing(pub, "link")
        fill_if_missing(pub, "extra")
        fill_if_missing(pub, "slides")

        fail_if_not(
            "section" in pub,
            'Must include a "section" field for each pub in data/publications.json!',
        )
        fail_if_not(
            "selected" in pub,
            'Must include a "selected" field for each pub in data/publications.json!',
        )

    auto_links_json = read_data("data/auto_links.json", optional=True)
    auto_notes_json = read_data("data/auto_notes.json", optional=True)

    # Sanity checks
    if not is_federicos(meta_json["name"]):
        status("\nPerforming sanity checks:")
        check_cname()
        check_tracker(meta_json["tracker"])

    # Load templates
    status("\nLoading template files:")
    main_css = read_template(f"{config.templates}/main.css", optional=False)
    light_css = read_template(f"{config.templates}/light.css", optional=False)
    dark_css = read_template(f"{config.templates}/dark.css", optional=True)
    dark_css = light_css if dark_css == "" else dark_css
    has_dark = light_css != dark_css
    head_html = read_template(f"{config.templates}/head.html", optional=False)
    footer_html = read_template(f"{config.templates}/footer.html", optional=False)
    paper_html = read_template(f"{config.templates}/paper.html", optional=False)
    news_item_html = read_template(f"{config.templates}/news-item.html", optional=False)

    if is_federicos(meta_json["name"]):
        footer_html = """\n<footer>\n<p>Feel free to <a href="https://github.com/FedericoAureliano/FedericoAureliano.github.io">use this website template</a>.</p>\n</footer>\n"""
    else:
        footer_html = "\n" + footer_html

    # Create HTML and CSS
    head_html = replace_placeholders(head_html, meta_json)
    footer_html = replace_placeholders(footer_html, meta_json)
    main_css = replace_placeholders(main_css, style_json)
    light_css = replace_placeholders(light_css, style_json)
    dark_css = replace_placeholders(dark_css, style_json)
    news_page = build_news_page(news_json, auto_links_json, auto_notes_json, has_dark)
    pubs_page = build_pubs_page(pubs_json, auto_links_json, auto_notes_json, has_dark)
    index_page = build_index(
        profile_json, news_json, pubs_json, auto_links_json, auto_notes_json, has_dark
    )

    # Write to files
    status("\nWriting website:")
    write_file(f"{config.target}/index.html", index_page)
    write_file(f"{config.target}/news.html", news_page)
    write_file(f"{config.target}/pubs.html", pubs_page)
    write_file(f"{config.target}/main.css", main_css)
    write_file(f"{config.target}/light.css", light_css)
    write_file(f"{config.target}/dark.css", dark_css)

    # Got to here means everything went well
    msg = f"Open {config.target}/index.html in your browser to see your website!"
    success(msg)
    exit(0)
