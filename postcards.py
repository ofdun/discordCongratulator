from dataclasses import dataclass
from datetime import datetime
from typing import List
import requests
import logging
from bs4 import BeautifulSoup as bs
from pytube import YouTube
import os
from exceptions import *
from const import SITE_WITH_POSTCARDS_HREF, CURRENT_PATH

@dataclass
class Holiday():
    name: str
    href: str

def get_all_todays_holidays_links() -> List[Holiday]:
    site = SITE_WITH_POSTCARDS_HREF
    response = requests.get(site)
    if response.status_code != 200:
        logging.error(
            f'Error while trying to get todays holidays! HTTP status code is {response.status_code}')
        raise NoResponseFromTheSiteError(f"HTTP status code = {response.status_code}")

    hrefs = []
    today = str(datetime.today().day)
    soup = bs(response.content, "html.parser")

    for tag in soup.find_all(class_="album-info"):
        album_info = tag.find_all(class_='name')
        postcards_date = album_info[2].text
        postcards_date = postcards_date[1:postcards_date.find(' ')]
        if postcards_date == today:
            name_of_holiday = album_info[0].find('strong').text
            href = tag.find('a').get('href')
            hrefs.append(Holiday(name=name_of_holiday, href=href))

    logging.info("Todays holidays hrefs were successfully downloaded")
    return hrefs


@dataclass
class Postcard:
    holiday: str
    href: str


def get_number_of_pages(parsed_page: bs) -> int:
    soup = parsed_page.find(id='pages')
    if len(soup) == 0:
        return 1
    elif len(soup) <= 6:
        return int(soup.find_all('a')[-1].text)
    else:
        number_of_pages = soup.find_all('a')[-1].text[4:]
        return int(number_of_pages)


def get_all_todays_postcards(todays_holidays: List[Holiday]) -> List[Postcard]:    
    def youtube_href_to_download_href(youtube_href: str) -> str:
        yt = YouTube(youtube_href)
        try:
            stream = yt.streams.get_highest_resolution()
        except:
            logging.error(f"Login required to download '{youtube_href}'")
            raise LoginRequiredError
        download_url = stream.url
        return download_url

    def get_if_it_is_youtube_href(href: str) -> bool:
        for i in range(len(href)):
            if href[-i] == '.':
                return False
            elif href[-i] == '/':
                return True

    def get_picture_href_from_its_page(page_href: str) -> str:
        response = requests.get(page_href)
        if response.status_code != 200:
            logging.error(
                f'Error while trying to get picture through its own page! HTTP status code is {response.status_code}')
            raise NoResponseFromPicturesPageError(f"HTTP status code = {response.status_code}")
        soup = bs(response.content, 'html.parser')
        button = soup.find(id='download-card-button')
        href = button.get('href')
        if get_if_it_is_youtube_href(href):
            try:
                href = youtube_href_to_download_href(href)
            except LoginRequiredError:
                href = ''
        return href

    def get_postcards_hrefs_from_page(todays_holiday: Holiday, first_use: bool = False, page: int = 0) -> List[Postcard]:
        postcards: List[Postcard] = []
        if page:
            response = requests.get(todays_holiday.href + f'page-{page}/')
        else:
            response = requests.get(todays_holiday.href)
        if response.status_code != 200:
            logging.error(
                f'Error while trying to get todays pictures! HTTP status code is {response.status_code}')
            raise NoResponseFromTheHolidaysPageError(f"HTTP status code = {response.status_code}")
        soup = bs(response.content, 'html.parser')
        if first_use:
            nonlocal number_of_pages
            number_of_pages = get_number_of_pages(soup)
        for card in soup.find_all(class_='card'):
            pictures_page = card.find('a').get('href')
            href = get_picture_href_from_its_page(pictures_page)
            if href == '':
                continue
            postcard = Postcard(holiday=todays_holiday.name, href=href)
            postcards.append(postcard)

        return postcards
    
    postcards: List[Holiday] = []

    for todays_holiday in todays_holidays:
        number_of_pages = 1
        postcards.extend( get_postcards_hrefs_from_page(
            todays_holiday=todays_holiday, first_use=True) )
        for page in range(2, number_of_pages + 1):
            postcards.extend(get_postcards_hrefs_from_page(
                todays_holiday=todays_holiday, page=page))

    return postcards


def get_todays_postcards_hrefs() -> List[Postcard]:
    hrefs = get_all_todays_holidays_links()
    postcards = get_all_todays_postcards(hrefs)
    return postcards


def download_postcard_to_cache_folder(file_url: str) -> None:
    response = requests.get(file_url)
    if response.status_code != 200:
        logging.error(
            f'Error while downloading a picture! Http status code: {response.status_code}')
        raise NoResponseFromPicturesDownloadHrefError(f"HTTP status code = {response.status_code}")
    image = response.content
    if file_url[-4] != '.':
        addition = '.mp4'
    else:
        addition = file_url[-4:]
    filename = datetime.now().strftime("%Y_%m_%d_%H_%M_%S_%f") + addition
    current_path = CURRENT_PATH
    path_to_file = current_path + "/cache/" + filename
    with open(path_to_file, 'wb') as f:
        f.write(image)
        
    logging.info("Postcard was successfully downloaded")


def download_all_postcards(todays_postcards: List[Postcard]) -> None:
    for postcard in todays_postcards:
        download_postcard_to_cache_folder(postcard.href)
        
def clear_postcards() -> None:
    for filename in os.listdir('cache'):
        os.remove('cache/' + filename)
    
    logging.info("Postcards were successfully deleted")


def download_todays_postcards() -> None:
    clear_postcards()
    todays_holidays_hrefs = get_all_todays_holidays_links()
    todays_postcards_hrefs = get_all_todays_postcards(todays_holidays_hrefs)
    download_all_postcards(todays_postcards_hrefs)

    logging.info("Postcards were successfully downloaded!")