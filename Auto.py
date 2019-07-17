import json
import logging
import random
import sqlite3
import urllib

import eventlet
import fake_useragent
import lxml.html
import requests
import timeout_decorator

import Post
import TelegramBot
import Tools
import Url


class Auto(TelegramBot.TelegramBot):
    XPATH_AUTO = '//div[@class = "ListingItem-module__container"]/div[@class = "ListingItem-module__main"]'
    LIST_PAGE = [Url.Url('https://auto.ru/bryanskaya_oblast/cars/all/?sort=fresh_relevance_1-desc&price_to=50000',
                         '#ProdamAvto')]
    driver = None

    def __init__(self):
        self.url_page = ""
        # if not self.driver:
        #     self.driver: selenium.webdriver = selenium.webdriver.PhantomJS(executable_path='/usr/local/bin/phantomjs')
        #     self.driver.set_window_size(1024, 768)

    def __del__(self):
        if self.driver:
            self.driver.close()

    def check_post(self):
        for i in self.LIST_PAGE:
            try:
                self.check_post_auto(i)
            except Exception as ex:
                logging.error('Exception of type {0!s} in check_new_posts_auto(): {1}'.format(type(ex).__name__, ex))

    def check_post_auto(self, i: Url):
        list_av: list = []
        hand = self.get_data(i.url)
        if hand is not None:
            self.check_one_post_auto(hand, i, list_av)

        conn = sqlite3.connect(Tools.DBNAME)
        cursor = conn.cursor()
        for p in list_av:
            self.post_checker(conn, cursor, i, p)
        conn.close()

    def post_checker(self, conn, cursor, i, p):
        cursor.execute("""SELECT id FROM avito WHERE id_av=?""", (p.id_elem,))
        if True:  # not cursor.fetchone():
            try:
                p.phone, p.user_name = ("", "")  # self.get_phone_num(i.url, p.id_elem)
            except Exception as exp:
                logging.error('Exception of type {0!s} in get_phone_num(): {1}'.format(type(exp).__name__, exp))
            try:
                self.send_new_posts(p)
            except Exception as ex:
                logging.error('Exception of type {0!s} in send_new_posts(): {1}'.format(type(ex).__name__, ex))
            else:
                cursor.execute("""INSERT INTO avito (id_av, price) VALUES(?, ?)""", (p.id_elem, p.price))
                conn.commit()
            # time.sleep(2)

    def check_one_post_auto(self, hand, i, list_av):
        doc_avito = lxml.html.document_fromstring(hand)
        doc_a = [i for i in doc_avito.xpath(self.XPATH_AUTO)]
        doc_a.reverse()
        for post in doc_a:
            try:
                list_av.append(self.get_post_auto(post, i))
            except Exception as ex:
                logging.error(
                        'Exception of type {0!s} in check_post_avito(): {1!s}\n{2}'.format(type(ex).__name__,
                                                                                           str(ex),
                                                                                           lxml.html.etree.tostring(
                                                                                                   post,
                                                                                                   pretty_print=True,
                                                                                                   encoding='unicode')))

    def get_post_auto(self, post, type_url) -> Post:
        id_elem = json.loads(post.xpath('./@data-bem')[0])
        id_elem = id_elem['listing-item']['id']
        url_av = post.xpath('.//a[@class = \'link clearfix link__control i-bem\']/@href')[0]
        title = ''
        try:
            title_av = \
                post.xpath('.//a[@class = \'link link_theme_auto listing-item__link link__control i-bem\']/text()')[
                    0]
            title = title_av.strip(' \t\n')
        except Exception:
            pass
        city = ''
        try:
            city_av = post.xpath('.//span[@class = \'listing-item__place\']')[0].text
            city = city_av.strip(' \t\n')
        except Exception:
            pass
        price = 'Неизвестно'
        try:
            price_av = post.xpath('.//div[@class = \'listing-item__price\']')[0].text
            price = price_av.strip(' \t\n')
        except Exception:
            try:
                price_av = post.xpath(
                        './/div[@class = \'listing-item__price listing-item__price_type_highlighted dropdown dropdown_switcher_listing-item-switcher dropdown_action_hover listing-item-switcher dropdown-hover__switcher dropdown__switcher dropdown-hover dropdown-hover__switcher i-bem\']')[
                    0].text
                price = price_av.strip(' \t\n')
            except Exception:
                pass
        desc = ''
        try:
            desc = post.xpath('.//div[@class = \'listing-item__description\']')[0].text
        except Exception:
            pass
        data = ''
        try:
            data = post.xpath('.//span[@class = \'listing-item__date\']')[0].text
            data = data.strip(' \t\n')
        except Exception:
            pass
        return Post.Post(url_av, price, desc, data, id_elem, title, city, type_url, "не удалось получить номер",
                         "нет имени", "")

    def check_new_posts_auto(self):
        for i in self.LIST_PAGE:
            try:
                self.check_post_auto(i)
            except Exception as ex:
                logging.error('Exception of type {0!s} in check_new_posts_auto(): {1}'.format(type(ex).__name__, ex))

    def get_data(self, url):
        global WITH_PROXY
        WITH_PROXY = 0
        count = 0
        timeout = eventlet.Timeout(35)
        try:
            while True:
                if count > 6:
                    logging.warning(f'coun = {count} {url}')
                    return None
                try:
                    doc_auto, page = self.get_page_auto(url)
                    if doc_auto == [] and page is None:
                        logging.warning(f'404 Exception {url}')
                        return None
                    if len(doc_auto.xpath(self.XPATH_AUTO)) > 0:
                        return page
                    else:
                        logging.warning(f'Empty list in {url}')
                        WITH_PROXY = 0
                        return None
                except Exception as ex:
                    count += 1
                    WITH_PROXY = 0
                    logging.error(f'Exception of type {type(ex).__name__!s} in get_data(): {ex}')

        except eventlet.timeout.Timeout:
            logging.warning('Got Timeout while retrieving Auto.ru data. Cancelling...')
            return None
        except Exception:
            return None
        finally:
            timeout.cancel()

    @timeout_decorator.timeout(30)
    def get_page_auto(self, url):
        if WITH_PROXY == 1 and len(Tools.PROXY_LIST) > 0:
            random.seed()
            i = random.randint(0, len(Tools.PROXY_LIST) - 1)
            proxy = urllib.request.ProxyHandler({'https': Tools.PROXY_LIST[i]})
            auth = urllib.request.HTTPBasicAuthHandler()
            opener = urllib.request.build_opener(proxy, auth, urllib.request.HTTPHandler)
            urllib.request.install_opener(opener)
            req = urllib.request.Request(url=url, headers={
                'User-Agent': fake_useragent.UserAgent().random}, )
            try:
                handler = urllib.request.urlopen(req)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return [], None
                elif e.code == 403:
                    logging.warning(f'Bad proxy 403 {Tools.PROXY_LIST[i]}')
                    del Tools.PROXY_LIST[i]
                    raise
                else:
                    raise
            except Exception:
                raise
            page = handler.read().decode(handler.headers.get_content_charset())
            doc_avito = lxml.html.document_fromstring(page)
            return doc_avito, page
        else:
            headers = {'user-agent': 'Mozilla/5.0 (X11; U; Linux i686) Gecko/20071127 Firefox/2.0.0.11'}
            feed = requests.get(url, headers=headers)
            feed.encoding = 'utf-8'
            page = feed.text
            doc_avito = lxml.html.document_fromstring(page)
            return doc_avito, page
