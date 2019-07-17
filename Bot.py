import logging
import time

import timeout_decorator

import Avito
import Tools
import Youla


@timeout_decorator.timeout(280)
def main():
    logging.getLogger('requests').setLevel(logging.CRITICAL)
    logging.basicConfig(format='[%(asctime)s] %(filename)s:%(lineno)d %(levelname)s - %(message)s', level=logging.INFO,
                        filename=Tools.FILE_LOG, datefmt='%d.%m.%Y %H:%M:%S')
    try:
        # get_proxy()
        pass
    except Exception as e:
        logging.error(f'Exception of type {type(e).__name__!s} in get_proxy(): {e}')
    if not Tools.SINGLE_RUN:
        while True:
            Tools.clear_log()
            Tools.create_db_if_notexist()
            avt = Avito.Avito()
            avt.check_new_posts_avito()
            you = Youla.Youla()
            you.check_new_posts_youla()
            logging.info('[App] Script went to sleep.')
            time.sleep(60 * 10)
    else:
        Tools.clear_log()
        Tools.create_db_if_notexist()
        try:
            avt = Avito.Avito()
            avt.check_new_posts_avito()
        except Exception as ex:
            logging.error(f'Exception of type {type(ex).__name__!s} in main(): {ex}')
        try:
            you = Youla.Youla()
            you.check_new_posts_youla()
        except Exception as ex:
            logging.error(f'Exception of type {type(ex).__name__!s} in main(): {ex}')
    logging.info('[App] Script exited.\n')


if __name__ == '__main__':
    try:
        main()
    except Exception as ex:
        logging.error(f'Exception of type {type(ex).__name__!s} in main(): {ex}')
