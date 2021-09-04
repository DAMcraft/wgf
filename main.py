import praw
import os
import requests
import re
import base64
import json
from base64 import b64encode
import time
from PIL import Image
import urllib.parse
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
from difflib import SequenceMatcher

from flask import Flask
from threading import Thread
import logging
log = logging.getLogger('werkzeug')
log.setLevel(logging.ERROR)

app = Flask('')

@app.route('/')
def main():
  return "Your Bot Is Ready"

def run():
  app.run(host="0.0.0.0", port=443)

def keep_alive():
  server = Thread(target=run)
  server.start()

# import pytesseract

# pytesseract.pytesseract.tesseract_cmd = "tesseract"
# os.environ["TESSDATA_PREFIX"] = "tessdata"
url = "https://api.imgur.com/3/upload.json"
imgur_client_id = os.environ['imgur_client_id']
imgur_client_secret = os.environ['imgur_client_secret']
api_key = os.environ['api_key']


file_name = ""
post_info = {}



reddit = praw.Reddit(client_id=os.getenv("client_id"),
                     client_secret=os.getenv("client_secret"),
                     username=os.getenv("username"),
                     password=os.getenv("password"),
                     user_agent=os.getenv("user_agent"))

subreddit = reddit.subreddit('wirklichgutefrage')
already_checked = 'checked.txt'

def is_checked(submission):
    val = False
    for comment in submission.comments:
        if comment.author == reddit.user.me():
            val = True
    return val


def post_to_image():
  for submission in subreddit.new(limit=1):
    if hasattr(submission, "post_hint"):
      if not is_checked(submission) and submission.post_hint == "image":
        try:
          post_info["title"] = submission.title
          file_name = submission.url.split("/")
          if len(file_name) == 0:
              file_name = re.findall("/(.*?)", submission.url)
          file_name = file_name[-1]
          if "." not in file_name:
              file_name += ".jpg"
          with open("checked.txt","a") as f:
            f.write(submission.id+"\n")
          r = requests.get(submission.url)
          with open(file_name,"wb") as f:
            f.write(r.content)
          original = Image.open(file_name)
          width, height = original.size
          left = 0
          top = 0
          right = width
          bottom = height / 2
          cropped = original.crop((left, top, right, bottom))
          # cropped = cropped.filter(ImageFilter.MedianFilter())
          cropped.save(file_name)
          # imgur = requests.post(
          # url, 
          # headers = {"Authorization": "Client-ID "+imgur_client_id},
          # data = {
          #     'key': imgur_client_secret, 
          #     'image': b64encode(open(file_name, 'rb').read()),
          #     'type': 'base64',
          #     'name': submission.id,
          #     'title': submission.id
          # })
          # imgurl = print(imgur.json()["data"]["link"])
          # json=  {
          #       "folderId": "b1gvmob95yysaplct532",
          #       "analyze_specs": [{
          #           "content": b64encode(open(file_name, 'rb').read()),
          #           "features": [{
          #               "type": "TEXT_DETECTION",
          #               "text_detection_config": {
          #                   "language_codes": ["de"]
          #               }
          #           }]
          #       }]
          #   }
          spam, file_extension = os.path.splitext(file_name)
          # text = requests.get('https://api.ocr.space/parse/imageurl?apikey='+api_key+'&url='+imgur.json()["data"]["link"]+'&language=ger')
          img_raw = open(file_name, 'rb')

          s = requests.Session()
          s.mount('https://', HTTPAdapter(max_retries=Retry(total=4, backoff_factor=3)))
          s.params = {'srv': 'android'}

          params_ = {'lang': "de"}
          files = {'file': ("file", img_raw, 'image/jpeg')}
          response = s.post('https://translate.yandex.net/ocr/v1.1/recognize', params=params_, files=files)
          resp_j = response.json()
          text = ""
          for block in resp_j['data']['blocks']:
              for box in block['boxes']:
                  text += box['text'] + '\n'
          tstrip = text.strip()
          # text = pytesseract.image_to_string(Image.open(file_name))
          # print(text)
          os.remove(file_name)
          #   for line in data:
          #   if line.__contains__('251212'):
          #       print(line)
          #       dataLog.append(line)
          # print(dataLog)
          # print(text.text)
          # output = json.loads(text.content.decode())["ParsedResults"][0]["ParsedText"]
          line_num = 0
          for line in tstrip.splitlines():
            if "?" in line:
              search_term = line
              break
          try:    
            for line in tstrip.splitlines():
                line_num += 1
                if "Frage von" in line:
                    break
            frage_anfang = line_num + 2
            line_num = 0
            for line in tstrip.splitlines():
              line_num += 1
              if line_num == frage_anfang:
                anfang = line
          except:
            anfang = ""
          print(anfang + " "+ search_term)
          for line in tstrip.splitlines():
              if "Frage von" in line:
                  reddit_erkannt_frage_von = line.replace("Frage von", "")

          if anfang != search_term:
            search_term = anfang + " "+ search_term
          urlenc = urllib.parse.quote(search_term)
          gutefrage_search = requests.get("https://www.gutefrage.net/home/suche?begriff="+urlenc, headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36", "Origin":"https://www.gutefrage.net", "Referer":"https://www.gutefrage.net/"})


          content = gutefrage_search.content
          bsdoc = BeautifulSoup(content, 'html.parser')
          post = bsdoc.find("a", {"class": "ListingElement-questionLink"})["href"]

          get_titel = requests.get("https://www.gutefrage.net"+post, headers = {"User-Agent":"Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36", "Origin":"https://www.gutefrage.net", "Referer":"https://www.gutefrage.net/"})
          if get_titel.status_code == 200:
            content = get_titel.content
            bsdoc = BeautifulSoup(content, 'html.parser')
            gf_titel = bsdoc.find("h1", {"class":"Question-title Question-title--large"}).get_text().strip()
            gf_user = bsdoc.find("span", {"class":"ContentMeta-authorName--big"}).get_text().strip()
          else:
            print("Error: "+requests.status_code)
          print("Gutefrage User: "+gf_user+"\nErkannt im Reddit Post:"+reddit_erkannt_frage_von)
          pinme = submission.reply("#[Link zum Post](https://www.gutefrage.net"+post+")    \nErkannter Titel: "+search_term+"\n\nTitel der (möglichen) Frage: "+gf_titel+"\n***\n    \n^(Ich bin ein Roboter von) [^(u/DAMcraft)](https://reddit.com/u/DAMcraft)^(.) ^( Der Aufwand, diesen Bot zu schreiben, war enorm, deswegen könnt ihr helfen, indem ihr diesem Bot eure Gratisauszeichnung verleiht (Durch mehr Karma kann der Bot schneller kommentieren\))\n\n^(Ihr habt Fehler gefunden oder Feedback? Alles )[^(hier)](https://www.reddit.com/message/compose/?to=DAMcraft&subject=R%C3%BCckmeldung)^( abgeben!)\n\n^(Falls der Link nicht zur richtigen Frage führt, könnte es daran liegen, dass sich der vom Bot erkannte Text zu sehr von dem des Posts unterscheidet, der Beitrag auf Gutefrage gelöscht wurde oder es zu viele ähnlich klingende Fragen gibt.)")
          try:
            pinme.mod.distinguish(sticky=True) 
          except:
            print("error at pinning")
          print(post_info)
          print(submission.id)
          print(gf_titel)
        except:
          print("error")
          try:
            with open(file_name,"rb") as f:
              lines = f.readlines()
              lines = lines[:-1]
              with open(file_name, "wb") as f:
                f.write(lines)
          except:
            print("error x2")
keep_alive()
while 0==0:
  post_to_image()
  time.sleep(5)
