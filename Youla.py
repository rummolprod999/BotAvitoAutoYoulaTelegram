import logging
import random
import sqlite3
import urllib

import eventlet
import fake_useragent
import lxml
import timeout_decorator

import Post
import TelegramBot
import Tools
import Url


class Youla(TelegramBot.TelegramBot):
    XPATH_YOULA = '//li[@class = "product_item"]'
    LIST_PAGE = [Url.Url('https://youla.ru/klintsy/kompyutery?attributes[sort_field]=date_published',
                         '#Компьютеры_и_комплектующие'),
                 Url.Url('https://youla.ru/klintsy/smartfony-planshety?attributes[sort_field]=date_published',
                         '#Телефоны_планшеты'),
                 Url.Url('https://youla.ru/klintsy/ehlektronika?attributes[sort_field]=date_published',
                         '#ТВ_аудио_видео'),
                 Url.Url('https://youla.ru/klintsy/foto-video?attributes[sort_field]=date_published',
                         '#Фото_и_видеокамеры')]
    driver = None

    def __init__(self):
        self.url_page = ""

    def __del__(self):
        if self.driver:
            self.driver.close()

    @timeout_decorator.timeout(280)
    def check_new_posts_youla(self):
        for i in self.LIST_PAGE:
            try:
                self.check_post_youla(i)
            except Exception as ex:
                logging.error(f'Exception of type {type(ex).__name__!s} in check_new_posts_youla(): {ex}')

    def check_post_youla(self, i: Url):
        list_av: list = []
        hand = self.get_data(i.url)
        if hand is not None:
            self.check_one_post_youla(hand, i, list_av)

        conn = sqlite3.connect(Tools.DBNAME)
        cursor = conn.cursor()
        for p in list_av:
            if 'klintsy' not in p.url:
                continue
            self.post_checker(conn, cursor, i, p)
        cursor.close()
        conn.close()

    def check_one_post_youla(self, hand, i, list_av):
        doc_youla = lxml.html.document_fromstring(hand)
        doc_a = [i for i in doc_youla.xpath(self.XPATH_YOULA)]
        doc_a.reverse()
        for post in doc_a:
            try:
                list_av.append(self.get_post_youla(post, i))
            except Exception as ex:
                logging.error(
                        'Exception of type {0!s} in check_one_post_youla(): {1!s}\n{2}'.format(type(ex).__name__,
                                                                                               str(ex),
                                                                                               lxml.html.etree.tostring(
                                                                                                       post,
                                                                                                       pretty_print=True,
                                                                                                       encoding='unicode')))

    def get_post_youla(self, post, type_url) -> Post:
        url_av = post.cssselect('a')
        url_av = url_av[0].get('href')
        id_elem = url_av
        url_av = 'https://youla.ru' + url_av
        title = ''
        try:
            title_av = post.xpath('.//div[contains(@class, \'product_item__title\')]')[0].text_content()
            title = title_av.strip(' \t\n')
        except Exception:
            pass
        city = ''
        try:
            city_av = post.xpath('.//span[@class = "product_item__location"]')[0].text_content()
            city = city_av.strip(' \t\n')
        except Exception:
            pass
        price = 'Неизвестно'
        try:
            price_av = post.xpath('.//div[contains(@class, \'product_item__description\')]/div[1]')[0].text_content()
            price_av = price_av.replace('руб.', '')
            price = price_av.strip(' \t\n')
        except Exception:
            pass
        desc = ''
        data = ''
        try:
            data = post.xpath('.//div[@class = "product_item__date"]/span[1]')[0].text
            data = data.strip(' \t\n')
        except Exception:
            pass
        return Post.Post(url_av, price, desc, data, id_elem, title, city, type_url, "не удалось получить номер",
                         "нет имени", None)

    def post_checker(self, conn, cursor, i, p: Post):
        cursor.execute("""SELECT id FROM avito WHERE id_av=? AND price=?""", (p.id_elem, p.price))
        if not cursor.fetchone():
            try:
                p.phone, p.user_name = ("", "")  # self.get_phone_num(i.url, p.id_elem)
                cursor.execute("""SELECT price FROM avito WHERE id_av=? ORDER BY id DESC LIMIT 1""", (p.id_elem,))
                res = cursor.fetchone()
                if res:
                    p.last_price = res[0]
            except Exception as exp:
                logging.error(f'Exception of type {type(exp).__name__!s} in get_phone_num(): {exp}')
            try:
                self.send_new_posts(p)
            except Exception as ex:
                logging.error(f'Exception of type {type(ex).__name__!s} in send_new_posts(): {ex}')
            else:
                cursor.execute("""INSERT INTO avito (id_av, price) VALUES(?, ?)""", (p.id_elem, p.price))
                conn.commit()
            # time.sleep(2)

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
                    doc_youla, page = self.get_page_av(url)
                    if doc_youla == [] and page is None:
                        logging.warning(f'404 Exception {url}')
                        return None
                    if len(doc_youla.xpath(self.XPATH_YOULA)) > 0:
                        return page
                    else:
                        logging.warning(f'Empty list in {url}')
                        WITH_PROXY = 0
                except Exception as ex:
                    count += 1
                    WITH_PROXY = 0
                    logging.error(f'Exception of type {type(ex).__name__!s} in get_data(): {ex}')

        except eventlet.timeout.Timeout:
            logging.warning('Got Timeout while retrieving Youla.ru data. Cancelling...')
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
            doc_youla = lxml.html.document_fromstring(page)
            return doc_youla, page
        else:
            req = urllib.request.Request(url=url, headers={
                'User-Agent': fake_useragent.UserAgent().random,
                'Cookie': 'location=%7B%22isConfirmed%22%3Atrue%2C%22lat%22%3A52.7585111%2C%22lng%22%3A32.2400969%2C%22r%22%3A5000%2C%22title%22%3A%22%5Cu041a%5Cu043b%5Cu0438%5Cu043d%5Cu0446%5Cu044b%22%2C%22city%22%3Anull%2C%22citySlug%22%3A%22all%22%2C%22cityLocation%22%3Afalse%2C%22pointLocation%22%3Atrue%2C%22defaultRadius%22%3Afalse%7D'}, )
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
            doc_youla = lxml.html.document_fromstring(page)
            return doc_youla, page
