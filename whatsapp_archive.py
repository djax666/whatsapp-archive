#!/usr/bin/python3

"""Reads a WhatsApp conversation export file and writes a HTML file."""

import argparse
import datetime
import dateutil.parser
import itertools
import jinja2
import logging
import os.path
import re
import sys
import urllib, os, uuid, wget
#################################################################################################
from re import U
import urllib3
import sys
from bs4 import BeautifulSoup
from html import unescape, escape
from termcolor import colored
from urllib.parse import urlparse, urljoin, urlunparse
from datetime import datetime

def print_warning(*args, **kwargs):
    # print(*[colored(s, 'red') for s in args], **kwargs)
    if False:
        print()
    

def print_decision(*args, **kwargs):
    # print(*[colored(s, 'green') for s in args], **kwargs)
    if False:
        print()



def resolve_title(soup):
    tag = soup.find('meta', attrs={'property' : 'og:title'})
    if tag is not None and 'content' in tag.attrs:
        print_decision('title acquired from meta \"og:title\"')
        return tag['content']

    tag = soup.find('title')
    if tag is not None:
        print_decision('title acquired from title tag')
        return tag.text

    print_warning('unable to extract title from page')
    return None


def resolve_image(soup, urlBase):
   

    tag = soup.find('meta', attrs={'property' : 'og:image'})
    if tag is not None and 'content' in tag.attrs:
        print_decision('image acquired from meta \"og:image\"')
        return urljoin(urlBase, tag['content'])

    tag = soup.find('link', attrs={'rel' : 'shortcut icon'})
    if tag is not None and 'href' in tag.attrs:
        print_decision('image acquired from shortcut icon')
        return urljoin(urlBase, tag['href'])

    tag = soup.find('img')
    if tag is not None and 'src' in tag.attrs:
        print_decision('image acquired from the first image in page')
        return urljoin(urlBase, tag['src'])

    print_warning('unable to resolve image for page')
    return None

def resolve_description(soup):
    

    tag = soup.find('meta', attrs={'property' : 'og:description'})
    if tag is not None and 'content' in tag.attrs:
        print_decision('description acquired from meta \"og:description\"')
        return tag['content']

    body = soup.find('body')
    if body is not None:
        tag = body.find('p')
        if tag is not None:
            print_decision('description acquired from first paragraph')
            return tag.text

    print_warning('unable to resolve description for page')
    return None


def resolve_domain(soup, urlInfo):
 

    tag = soup.find('meta', attrs={'property' : 'og:url'})
    if tag is not None and 'content' in tag.attrs:
        ogUrlInfo = urlparse(tag['content'])
        if len(ogUrlInfo.netloc) > 0:
            print_decision('domain name acquired from meta \"og:url\"')
            return ogUrlInfo.netloc

    print_decision('domain name acquired from input')
    return urlInfo.netloc

def show_result(result):
    

    for key, val in result.items():
        print(key + ': ' + val)

def build_link_preview(result):
    template = r'''
    <div class="div-link-preview">
        <div class="div-link-preview-col div-link-preview-col-l">
            <img class="div-link-preview-img" src="{img_link:}">
        </div>
        <div class="div-link-preview-col div-link-preview-col-r">
            <div style="display: block; height: 100%; padding-left: 10px;">
                <div class="div-link-preview-title"><a href="{page_link:}">{page_title:}</a></div>
                <div class="div-link-preview-content">{page_description:}</div>
                <div class="div-link-preview-domain">
                <span style="font-size: 80%;">&#x1F4C5;</span>&nbsp;{proc_date:}
                <span style="font-size: 80%; margin-left: 20px;">&#x1F517;</span>&nbsp;{page_domain:}</div>
            </div>
        </div>
    </div>
    '''

    return template.format(
        img_link=result['image'],
        page_title=result['title'],
        page_link=result['link'],
        page_description=result['description'],
        page_domain=result['domain'],
        proc_date=result['access_date']
    )


def PreviewLink(url):
    hdr = {'User-Agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.11 (KHTML, like Gecko) Chrome/23.0.1271.64 Safari/537.11',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
        'Accept-Charset': 'ISO-8859-1,utf-8;q=0.7,*;q=0.3',
        'Accept-Encoding': 'none',
        'Accept-Language': 'en-US,en;q=0.8',
        'Connection': 'keep-alive'}

    urlInfo = urlparse(url)
    if len(urlInfo.scheme) == 0 or len(urlInfo.netloc) == 0:
        raise RuntimeError('please use complete URL starting with http:// or https://')
    urlBase = urlInfo.scheme + '://' + urlInfo.netloc
    urllib3.disable_warnings()
    http = urllib3.PoolManager()
    request = http.request('GET', url, headers=hdr)
    content = request.data

    soup = BeautifulSoup(content, 'html5lib')

    result = {}
    result['title'] = resolve_title(soup, )
    img = resolve_image( soup,urlBase)
    cacheimg_path = "." + DownloadImage(img)
    result['image'] = cacheimg_path #resolve_image( soup,urlBase)
    result['description'] = resolve_description( soup)
    result['domain'] = resolve_domain( soup,urlBase)
    result['link'] = url
    result['access_date'] =  datetime.now().strftime('%Y-%m-%d')

    return build_link_preview(result)
#################################################################################################
# Format of the standard WhatsApp export line. This is likely to change in the
# future and so this application will need to be updated.
DATE_RE = '(?P<date>[\d/-]+)'
TIME_RE = '(?P<time>[\d:]+( [AP]M)?)'
DATETIME_RE = '\[?' + DATE_RE + ',? ' + TIME_RE + '\]?'
SEPARATOR_RE = '( - |: | )'
NAME_RE = '(?P<name>[^:]+)'
WHATSAPP_RE = (DATETIME_RE +
               SEPARATOR_RE +
               NAME_RE +
               ': '
               '(?P<body>.*$)')

FIRSTLINE_RE = (DATETIME_RE +
               SEPARATOR_RE +
               '(?P<body>.*$)')

 
class Error(Exception):
    """Something bad happened."""


def ParseLine(line):
    """Parses a single line of WhatsApp export file."""
    m = re.match(WHATSAPP_RE, line)
    if m:
        d = dateutil.parser.parse("%s %s" % (m.group('date'),
            m.group('time')), dayfirst=False)  ## probleme ici
        return d, m.group('name'), m.group('body')
    # Maybe it's the first line which doesn't contain a person's name.
    m = re.match(FIRSTLINE_RE, line)
    if m:
        d = dateutil.parser.parse("%s %s" % (m.group('date'),
            m.group('time')), dayfirst=True)
        return d, "nobody", m.group('body')
    return None


def IdentifyMessages(lines):
    """Input text can contain multi-line messages. If there's a line that
    doesn't start with a date and a name, that's probably a continuation of the
    previous message and should be appended to it.
    """
    messages = []
    msg_date = None
    msg_user = None
    msg_body = None
    for line in lines:
        m = ParseLine(line)
        if m is not None:
            if msg_date is not None:
                # We have a new message, so there will be no more lines for the
                # one we've seen previously -- it's complete. Let's add it to
                # the list.
                messages.append((msg_date, msg_user, msg_body))
            msg_date, msg_user, msg_body = m
        else:
            if msg_date is None:
                raise Error("Can't parse the first line: " + repr(line) +
                        ', regexes are FIRSTLINE_RE=' + repr(FIRSTLINE_RE) +
                        ' and WHATSAPP_RE=' + repr(WHATSAPP_RE))
            msg_body += '\n' + line.strip()
    # The last message remains. Let's add it, if it exists.
    if msg_date is not None:
        messages.append((msg_date, msg_user, msg_body))
    return messages


def TemplateData(messages, input_filename):
    """Create a struct suitable for procesing in a template.
    Returns:
        A dictionary of values.
    """
    by_user = []
    file_basename = os.path.basename(input_filename)
    for user, msgs_of_user in itertools.groupby(messages, lambda x: x[1]):
        by_user.append((user, list(msgs_of_user)))
    return dict(by_user=by_user, input_basename=file_basename,
            input_full_path=input_filename)


def FormatHTML(data,me):

    tmpl = """<!DOCTYPE html>
    <html>
    <head>
        <title>WhatsApp archive {{ input_basename }}</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <link id="favicon" rel="shortcut icon" href="../icons/favicon.png" type="image/png"/>
		<link rel="apple-touch-icon" sizes="194x194" href="../icons/apple-touch-icon.png" type="image/png"/>

        <link rel="stylesheet" href="../icons/style.css">
        <link rel="stylesheet" href="../icons/image-popup.css">

        <script src="../icons/image-popup.js"></script>
        
    </head>
    <body>
        <div class="tt" id="banner">
            <img class="avatar" src="../avatar/{{ input_basename.replace('.txt','').replace('WhatsApp Chat with ','') }}.jpg"> 
            <h1> {{ input_basename.replace('.txt','').replace('WhatsApp Chat with ','') }}</h1>
        </div>
        <div id="popup-background" class="popup-background" style="display: none;">
            <div class="popup-content">
                <div id="popup-title"></div>
                <!-- <span id="popup-close" class="popup-close">&times;</span> -->
                <img id="popup-image" class="popup-image">
            </div>
        </div>
        <div id="msgs">
            <ol class="users">
            {% for user, messages in by_user %}
                <li>
                    <div class="{% if me == user %}username-me">{% elif "nobody" == user %}username-nobody">{% else %}username-others">{{ user }}{% endif %}
                    </div>
                
                <ol class="messages">
                {% for message in messages %}
                    <li class="{% if me == user %}speech-bubble-me{% elif "nobody" == user %}speech-bubble-nobody{% else %}speech-bubble{% endif %}"> {{ message[2] | e | replace('\n', ' \n<br>') }} 
                        <div class="mdate">{{ message[0] }}</span>
                    </li>
                {% endfor %}
                </ol>
                </li>
            {% endfor %}
            </ol>
        </div>
        <script>
            function adjustLinkPreviewHeight(){
                console.log("running!");
                var cats = document.querySelectorAll('.div-link-preview');
                //console.log(cats.length);
                for (var i = 0; i < cats.length; i++) {
                    var left = cats[i].querySelector('.div-link-preview-col-l');
                    var right = cats[i].querySelector('.div-link-preview-col-r');
                    var width = left.clientWidth;
                    cats[i].style.height = width + "px";
                    left.style.height = width + "px";
                    right.style.height = width + "px";
                }
            }
            adjustLinkPreviewHeight();
        </script>
    </body>
    </html>
    """
    
    return jinja2.Environment().from_string(tmpl).render(**data, me=me)

def RemplaceMedia(data, rep ):

    entrees = os.listdir(rep)
    for nf in entrees:
        nfc = os.path.join(rep, nf)
        if os.path.isfile(nfc) :
            ext = os.path.splitext(nfc)[-1]
            if ext == ".pdf":
                data = data.replace(nf+' (file attached)' , '<a href="'+nf+'"><img class="logo" src="../icons/pdf.png">'+nf+'</a>')
            elif ext ==".vcf":
                data = data.replace(nf+' (file attached)' , '<a href="'+nf+'"><img class="logo" src="../icons/vcf.png">'+nf+'</a>')
            elif ext ==".doc" or ext ==".docx":
                data = data.replace(nf+' (file attached)' , '<a href="'+nf+'"><img class="logo" src="../icons/word.png">'+nf+'</a>')
            elif ext ==".xls" or ext ==".xlsx":
                data = data.replace(nf+' (file attached)' , '<a href="'+nf+'"><img class="logo" src="../icons/excel.png">'+nf+'</a>')            
            elif ext ==".jpg" or ext == ".png" or ext == ".gif" or ext == ".webp":
                data = data.replace(nf+' (file attached)' , '<img class="image-popup" src="'+nf+'">')
            elif ext ==".opus" or ext ==".ogg":
                data = data.replace(nf+' (file attached)','<audio controls><source src="'+nf+'" type="audio/ogg"></audio>' )
            elif ext ==".mp3":
                data = data.replace(nf+' (file attached)','<audio controls><source src="'+nf+'" type="audio/mp3"></audio>' )
            elif ext ==".m4a":
                data = data.replace(nf+' (file attached)','<audio controls><source src="'+nf+'" type="audio/mp4"></audio>' )
            elif ext ==".mp4":
                data = data.replace(nf+' (file attached)','<video controls><source src="'+nf+'" type="video/mp4"></video>' )
            elif ext ==".webm":
                data = data.replace(nf+' (file attached)','<video controls><source src="'+nf+'" type="video/webm"></video>' )
            else:
                data = data.replace(nf+' (file attached)' , '<a href="'+nf+'"><img class="logo" src="../icons/unknown.png">'+nf+'</a>')



    data = data.replace("&lt;Media omitted&gt;",'<img class="logo" src="../icons/missing.png">')
    # transfor URLs into links
    link_regex = re.compile('((https?):((//)|(\\\\))+([\w\d:#@%/;$()~_?\+-=\\\.&](#!)?)*)', re.DOTALL)
    links = re.findall(link_regex, data)
    my_set = set(links)
    unique_links = list(my_set)
    
    for l in unique_links:
        try:
            pu = PreviewLink(l[0])
            data = data.replace(l[0],pu)
        except:
             data = data.replace(l[0],'<a href="'+l[0]+'">'+l[0]+'</a>')
    
        
    return data

#"https://i.ytimg.com/vi/<video_id>/default.jpg"



def DownloadImage(url):
    path = urllib.parse.urlparse(url).path
    ext = os.path.splitext(path)[1]
    # Convert a UUID to a string of hex digits in standard form
    # str(uuid.uuid4())
    # 'f50ec0b7-f960-400d-91f0-c42a6d44e3d0'
    # Convert a UUID to a 32-character hexadecimal string
    #  uuid.uuid4().hex
    img_path = './cache/'+ uuid.uuid4().hex + ext
    wget.download(url, img_path)
    return img_path


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Produce a browsable history '
            'of a WhatsApp conversation')
    parser.add_argument('-i', dest='input_file', required=True)
    parser.add_argument('-o', dest='output_file', required=True)
    parser.add_argument('-m', dest='me', required=True,help="the main receiver")
    # parser.add_argument('-d', dest='media_directory', required=True)
    args = parser.parse_args()
    with open(args.input_file, 'rt', encoding='utf-8-sig') as fd:
        messages = IdentifyMessages(fd.readlines())
    
    media_directory= os.path.dirname(args.input_file)
    # # print message date
    # for d in messages:
    #     print (d[0])
    template_data = TemplateData(messages, args.input_file)
    HTML = FormatHTML(template_data,args.me)
    HTML = RemplaceMedia(HTML,rep=media_directory)
    with open(args.output_file, 'w', encoding='utf-8') as fd:
        fd.write(HTML)


if __name__ == '__main__':
    main()

            m.group('time')), dayfirst=True)
        return d, "nobody", m.group('body')
    return None


def IdentifyMessages(lines):
    """Input text can contain multi-line messages. If there's a line that
    doesn't start with a date and a name, that's probably a continuation of the
    previous message and should be appended to it.
    """
    messages = []
    msg_date = None
    msg_user = None
    msg_body = None
    for line in lines:
        m = ParseLine(line)
        if m is not None:
            if msg_date is not None:
                # We have a new message, so there will be no more lines for the
                # one we've seen previously -- it's complete. Let's add it to
                # the list.
                messages.append((msg_date, msg_user, msg_body))
            msg_date, msg_user, msg_body = m
        else:
            if msg_date is None:
                raise Error("Can't parse the first line: " + repr(line) +
                        ', regexes are FIRSTLINE_RE=' + repr(FIRSTLINE_RE) +
                        ' and WHATSAPP_RE=' + repr(WHATSAPP_RE))
            msg_body += '\n' + line.strip()
    # The last message remains. Let's add it, if it exists.
    if msg_date is not None:
        messages.append((msg_date, msg_user, msg_body))
    return messages


def TemplateData(messages, input_filename):
    """Create a struct suitable for procesing in a template.
    Returns:
        A dictionary of values.
    """
    by_user = []
    file_basename = os.path.basename(input_filename)
    for user, msgs_of_user in itertools.groupby(messages, lambda x: x[1]):
        by_user.append((user, list(msgs_of_user)))
    return dict(by_user=by_user, input_basename=file_basename,
            input_full_path=input_filename)


def FormatHTML(data):
    tmpl = """<!DOCTYPE html>
    <html>
    <head>
        <title>WhatsApp archive {{ input_basename }}</title>
        <meta charset="utf-8"/>
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body {
                font-family: sans-serif;
                font-size: 10px;
            }
            ol.users {
                list-style-type: none;
                list-style-position: inside;
                margin: 0;
                padding: 0;
            }
            ol.messages {
                list-style-type: none;
                list-style-position: inside;
                margin: 0;
                padding: 0;
            }
            ol.messages li {
                margin-left: 1em;
                font-size: 12px;
            }
            span.username {
                color: gray;
            }
            span.date {
                color: gray;
            }
        </style>
    </head>
    <body>
        <h1>{{ input_basename }}</h1>
        <ol class="users">
        {% for user, messages in by_user %}
            <li>
            <span class="username">{{ user }}</span>
            <span class="date">{{ messages[0][0] }}</span>
            <ol class="messages">
            {% for message in messages %}
                <li>{{ message[2] | e }}</li>
            {% endfor %}
            </ol>
            </li>
        {% endfor %}
        </ol>
    </body>
    </html>
    """
    return jinja2.Environment().from_string(tmpl).render(**data)


def main():
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser(description='Produce a browsable history '
            'of a WhatsApp conversation')
    parser.add_argument('-i', dest='input_file', required=True)
    parser.add_argument('-o', dest='output_file', required=True)
    args = parser.parse_args()
    with open(args.input_file, 'rt', encoding='utf-8-sig') as fd:
        messages = IdentifyMessages(fd.readlines())
    template_data = TemplateData(messages, args.input_file)
    HTML = FormatHTML(template_data)
    with open(args.output_file, 'w', encoding='utf-8') as fd:
        fd.write(HTML)


if __name__ == '__main__':
    main()
