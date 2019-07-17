import Post
import Tools


class TelegramBot:
    def send_new_posts(self, item: Post):
        last_price = "Старая цена: " + item.last_price + "\n" if item.last_price else ""
        phone = f"Телефон: {item.phone}\n" if item.phone else ""
        name = f"Имя: {item.user_name}\n" if item.user_name else ""
        place = f"Местоположение: {item.city}\n" if item.city else ""
        message = f"""Новое объявление!\nТип: {item.type_url.type_url}\nНазвание: {item.title}\n{place}Цена: <b>{item.price}</b>\n{last_price}Описание: {
        item.desc}\n{phone}{name}Дата последнего обновления: {item.data}\nСсылка: {item.url} """
        # print(message)
        Tools.bot.send_message(chat_id=Tools.CHANNEL_NAME, text=message, parse_mode='HTML')
