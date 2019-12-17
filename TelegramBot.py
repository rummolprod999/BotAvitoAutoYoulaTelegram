from datetime import datetime

import Post
import Tools


class TelegramBot:
    def send_new_posts(self, item: Post):
        last_price = "<i>Старая цена:</i> " + item.last_price + "\n" if item.last_price else ""
        phone = f"Телефон: {item.phone}\n" if item.phone else ""
        name = f"Имя: {item.user_name}\n" if item.user_name else ""
        place = f"<i>Местоположение:</i> {item.city}\n" if item.city else ""
        message = f"""<i>Дата:</i> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} \n<i>Тип:</i> {item.type_url.type_url}\n<i>Название:</i> <b>{item.title}</b>\n{place}<i>Цена:</i> <b>{item.price}</b>\n{last_price}<i>Описание:</i> {
        item.desc}\n{phone}{name}<i>Дата последнего обновления:</i> {item.data}\n<i>Ссылка:</i> {item.url} """
        # print(message)
        Tools.bot.send_message(chat_id=Tools.CHANNEL_NAME, text=message, parse_mode='HTML')
