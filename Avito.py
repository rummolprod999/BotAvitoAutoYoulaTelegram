import base64
import logging
import random
import re
import sqlite3
import time
import urllib

import eventlet
import fake_useragent
import lxml.html
import timeout_decorator

import Post
import TelegramBot
import Tools
import Url


class Avito(TelegramBot.TelegramBot):
    XPATH_AVITO = '//div[@id and not(contains(@id, \'ads\'))][@data-type]'
    LIST_PAGE = [Url.Url('https://www.avito.ru/klintsy/bytovaya_elektronika?geoCoords=52.752811%2C32.234301&radius=5',
                         '#Бытовая_электроника')]
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
                self.check_post_avito(i)
            except Exception as ex:
                logging.error(f'Exception of type {type(ex).__name__!s} in check_new_posts_avito(): {ex}')

    def check_post_avito(self, i: Url):
        list_av: list = []
        hand = self.get_data(i.url)
        if hand is not None:
            self.check_one_post_avito(hand, i, list_av)

        conn = sqlite3.connect(Tools.DBNAME)
        cursor = conn.cursor()
        for p in list_av:
            self.post_checker(conn, cursor, i, p)
        cursor.close()
        conn.close()

    def check_one_post_avito(self, hand, i, list_av):
        doc_avito = lxml.html.document_fromstring(hand)
        doc_a = [i for i in doc_avito.xpath(self.XPATH_AVITO)]
        doc_a.reverse()
        for post in doc_a:
            try:
                list_av.append(self.get_post_avito(post, i))
            except Exception as ex:
                logging.error(
                        'Exception of type {0!s} in check_post_avito(): {1!s}\n{2}'.format(type(ex).__name__,
                                                                                           str(ex),
                                                                                           lxml.html.etree.tostring(
                                                                                                   post,
                                                                                                   pretty_print=True,
                                                                                                   encoding='unicode')))

    def post_checker(self, conn, cursor, i, p: Post):
        cursor.execute("""SELECT id FROM avito WHERE id_av=? AND price=?""", (p.id_elem, p.price))
        if not cursor.fetchone():
            try:
                p.phone, p.user_name = ("", "")  # self.get_phone_num(i.url, p.id_elem)
                cursor.execute("""SELECT price FROM avito WHERE id_av=? ORDER BY id DESC""", (p.id_elem,))
                res = cursor.fetchall()
                if res:
                    for r in res:
                        p.last_price += f"{r[0]} -> "
                    p.last_price += f"{p.price}"
            except Exception as exp:
                logging.error(f"Exception of type {type(exp).__name__!s} in post_checker(): {exp}")
            try:
                self.send_new_posts(p)
            except Exception as ex:
                logging.error(f'Exception of type {type(ex).__name__!s} in send_new_posts(): {ex}')
            else:
                cursor.execute("""INSERT INTO avito (id_av, price) VALUES(?, ?)""", (p.id_elem, p.price))
                conn.commit()
            # time.sleep(2)

    def get_phone_num(self, url_av, id_elem):
        FILE_PHONE = "test_phone.png"

        if url_av != self.url_page:
            self.url_page = url_av
            self.driver.get(self.url_page)
            time.sleep(5)
        user_name = ""  # driver.find_element_by_xpath("//div[contains(@class, 'seller-info-name')]/a").text
        elem = self.driver.find_element_by_xpath(f"//div[@id = '{id_elem}']//button[contains(., 'Телефон')]")
        elem.click()
        self.driver.execute_script(
                f"var d = document.querySelectorAll('#{id_elem} button.js-item-extended-contacts'); d[0].click()")
        time.sleep(2)
        self.driver.switch_to.default_content()
        print(self.driver.find_element_by_xpath(f"//div[@id = '{id_elem}']").text)
        phone_clicked = self.driver.find_element_by_xpath(
                f"//div[@id = '{id_elem}']//img[contains(@class, 'item_table-extended-phone')]")
        src = phone_clicked.get_attribute("src")
        src = src.replace("data:image/png;base64,", "")
        phone_temp = base64.b64decode(src)
        with open(FILE_PHONE, "wb") as f:
            f.write(phone_temp)
        print(phone_clicked.text)
        phone = ""
        # phone = pytesseract.image_to_string(Image.open(FILE_PHONE))
        # phone = pytesseract.pytesseract.image_to_string(PIL.Image.open(io.BytesIO(phone_temp)))
        # phone = re.sub(r'\s|-|—', '', phone)
        return phone, user_name

    def get_post_avito(self, post, type_url) -> Post:
        id_elem = post.get('id')
        url_av = post.cssselect('h3 a')
        url_av = url_av[0].get('href')
        url_av = 'https://www.avito.ru' + url_av
        title = ''
        try:
            title_av = post.xpath('.//a[@class = \'snippet-link\']')[0].get('title')
            title = title_av.strip(' \t\n')
        except Exception:
            pass
        city = ''
        try:
            city_av = post.xpath('.//span[@class = \'item-address__string\']')[0].text
            city = city_av.strip(' \t\n')
        except Exception:
            try:
                city_av = post.xpath('.//p[contains(@class, \'address\')]')[0].text_content()
                city = city_av.strip(' \t\n')

            except Exception:
                pass
        price = 'Неизвестно'
        try:
            price_av = post.xpath('.//div[contains(@class, \'about\')]')[0].text
            price = price_av.strip(' \t\n')
            if price == "":
                price_av = post.xpath('.//div[contains(@class, \'about\')]/span')[0].text
                price = price_av.strip(' \t\n')
        except Exception:
            pass
        if price == '':
            try:
                price_av = post.xpath('.//span[contains(@class, \'price-amount\')]')[0].text_content()
                price = price_av.strip(' \t\n')
            except Exception:
                pass
        if price == '':
            try:
                price_av = post.xpath('.//span[contains(@class, \'price\')]')[0].text_content()
                price = price_av.strip(' \t\n')
            except Exception:
                pass
        if price == '':
            logging.warning(
                    'Empty price in check_post_avito(): {0}'.format(
                            lxml.html.etree.tostring(post,
                                                     pretty_print=True,
                                                     encoding='unicode')))
        price = re.sub(r'\s+', ' ', price)
        desc = ''
        try:
            desc = post.xpath('.//span[@class = \'param\']')[0].text.strip(' \t\n')
        except Exception:
            try:
                desc = post.xpath('.//div[contains(@class, \'specific-params\')]')[0].text.strip(' \t\n')
            except Exception:
                pass
        data = ''
        try:
            data = post.xpath('.//div[contains(@class, \'c-2\')]')[0].text
            data = data.strip(' \t\n')
        except Exception:
            pass
        return Post.Post(url_av, price, desc, data, id_elem, title, city, type_url, "не удалось получить номер",
                         "нет имени", "")

    @timeout_decorator.timeout(280)
    def check_new_posts_avito(self):
        for i in self.LIST_PAGE:
            try:
                self.check_post_avito(i)
            except Exception as ex:
                logging.error(f'Exception of type {type(ex).__name__!s} in check_new_posts_avito(): {ex}')

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
                    doc_avito, page = self.get_page_av(url)
                    if doc_avito == [] and page is None:
                        logging.warning(f'404 Exception {url}')
                        return None
                    if len(doc_avito.xpath(self.XPATH_AVITO)) > 0:
                        return page
                    else:
                        logging.warning(f'Empty list in {url}')
                        WITH_PROXY = 0
                except Exception as ex:
                    count += 1
                    WITH_PROXY = 0
                    logging.error(f'Exception of type {type(ex).__name__!s} in get_data(): {ex}')

        except eventlet.timeout.Timeout:
            logging.warning('Got Timeout while retrieving Avito.ru data. Cancelling...')
            return None
        except Exception:
            return None
        finally:
            timeout.cancel()

    @timeout_decorator.timeout(30)
    def get_page_av(self, url):
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
            page = handler.read()
            doc_avito = lxml.html.document_fromstring(page)
            return doc_avito, page
        else:
            req = urllib.request.Request(url=url, headers={
                'User-Agent': fake_useragent.UserAgent().random}, )
            try:
                handler = urllib.request.urlopen(req)
            except urllib.error.HTTPError as e:
                if e.code == 404:
                    return [], None
                else:
                    raise
            except Exception:
                raise
            page = handler.read()
            doc_avito = lxml.html.document_fromstring(page)
            return doc_avito, page
