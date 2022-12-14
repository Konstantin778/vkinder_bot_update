import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, sessionmaker
import psycopg2
from pprint import pprint
import datetime
from datetime import date
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from vk_api.utils import get_random_id
import random
from random import randrange
from vkinder import *
from database import *

with open("token_bot.txt", "r") as file:
    bot_token = file.read().strip()

vk_session = vk_api.VkApi(token=bot_token)
longpoll = VkLongPoll(vk_session)
vk = vk_session.get_api()

def write_msg(user_id, message, attachment = None):
    vk_session.method("messages.send", {"user_id": user_id, "message": message,
                                        "attachment": attachment,  "random_id": get_random_id()})

offset = 0
got_user = []
shown_couple = []

def get_user():
    # функция получает параметры пользователя бота и при каждом новом вызове перезаписывает
    # полученные данные в переменную got_user
    for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
                try:
                    request = event.text
                    if request.lower() == "старт" or request.lower() == "start":
                        write_msg(event.user_id, 'Для начала поиска введите "поиск" ')
                        user_id = event.user_id
                        user = (vk_client.get_params(user_ids=user_id)["response"][0])
                        if "bdate" not in user.keys():
                            write_msg(event.user_id, f'Недостаточно данных для поиска пары.'
                                                     f' Укажите дату рождения в настройках профиля\
                                                        и разрешите её показ')
                            continue
                        if "city" not in user.keys():
                            write_msg(event.user_id,
                                    f'Недостаточно данных для поиска пары. Укажите в профиле город своего проживания')
                            continue
                        try:
                            user
                        except vk_api.exceptions.ApiError:
                            write_msg(event.user_id, f'Ошибка api Вконтакте')
                            continue
                        else:
                            if user is not None:
                                shown_couple.clear()
                                got_user.clear()
                                got_user.append(user)
                            else:
                                write_msg(event.user_id, 'Невозможно определить пользователя.\
                                                            Проверьте настройки учётной записи ')
                    if request.lower() == "поиск" or request.lower() == "search":
                        write_msg(event.user_id, 'Для подтверждения поиска введите "поиск" ')
                        user = (vk_client.get_params(user_ids=event.user_id)["response"][0])
                        if user is not None:
                            got_user.clear()
                            got_user.append(user)
                except:
                    write_msg(event.user_id, f'Ошибка api Вконтакте ')
                break

def get_offered_people():
    # функция получает данные из переменной got_user и на их основании ищет подходящие пары пользователю
    # и при каждом вызове возвращает список из 50 новых анкет
    if got_user[0] is not None:
        birth_year = int(got_user[0]["bdate"][-4:])
        current_year = date.today().year
        age = current_year - birth_year

        sex = 0
        if got_user[0]["sex"] == 1:
            sex += 2
        else:
            sex += 1
        user_city = got_user[0]["city"]["id"]
        relation = got_user[0]["relation"]
        try:
            offered_people = vk_client.search_people(age - 1, age + 1, sex, user_city, relation, offset)
        except vk_api.exceptions.ApiError:
            write_msg(event.user_id, f'Ошибка api Вконтакте')
        else:
            if offered_people is not None:
                return offered_people
            else:
                write_msg(event.user_id, f'Не удалось найти подходящу пару.\
                                Измените параметры профиля или повторите попытку позже')
    else:
        write_msg(event.user_id, f'Не удалось обнаружить пользователя и осуществить поиск')

def get_people_ids():
    # функция обрабатывает данные, полученные из функции get_offered_people() и возвращает список
    # кортежей, каждый из которых состоит из id и имени с фамилией найденного человека. Найденные пользователи,
    # с закрытой страницей профиля на попадают в данный список.
    people_ids = []
    for people in get_offered_people():
        if people['is_closed'] == False:
            people_info = (people["id"], f'{people["first_name"]} {people["last_name"]}')
            if people_info is not None:
                people_ids.append(people_info)
    return people_ids

def get_whole_info():
    # функция обрабатывает данные, полученные из функции get_people_ids() и осуществляет поиск трёх
    # самых популярных фотографий профиля у каждого из найденных людей. Возвращает список кортежей,
    # каждый из которых состоит из имени-фамилии найденного человека, ссылке на его/её страницу vk.com
    # и список из трёх самых популярных фотографий профиля, записанных в формате для передачи в метод messages.send
    whole_info = []
    for couple in get_people_ids():
        couple_name = couple[1]
        try:
            id_couple = f'https://vk.com/id{vk_client.get_photos(owner_id=str(couple[0]))[1]}'
            all_photos = vk_client.get_photos(owner_id=str(couple[0]))[0]
        except vk_api.exceptions.ApiError:
            write_msg(event.user_id, f'Ошибка api Вконтакте')

        photos_ids = {}
        if all_photos is not None:
            if len(all_photos) >= 3:
                for photo in all_photos:
                    photos_ids[(photo["id"])] = photo["comments"]["count"] + photo["likes"][
                                 "count"] + photo["likes"]["user_likes"]
            else:
                pass
        else:
            write_msg(event.user_id, f'не удалось найти фотографии для показа. Повторите поиск')
        sorted_ids = (sorted(photos_ids.items(), key=lambda x: x[1]))[-3:]
        only_ids = []
        for id in sorted_ids:
            only_ids.append(f'photo{id_couple[17:]}_{id[0]}')
        info = (couple_name, id_couple, only_ids)
        whole_info.append(info)
    return whole_info

def run():
    # функция проверяет данные пользователя после запуска бота, активирует вышеописанные функции и
    # выводит в бота сообщение, состоящее из имени-фамилии пары, ссылки на его/её страницу в вк и
    # три фотографии. При каждом запуске выводятся профили, у которых альбом фото профиля содержит 3 и более фото.
    global offset
    for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
                request = event.text
                get_offered_people()
                get_people_ids()
                get_whole_info()

                for couple in get_whole_info():
                    if couple not in shown_couple and couple is not None:
                        shown_couple.append(couple)
                        try:
                            write_msg(event.user_id, message=f'Ваша пара - {couple[0]}, {couple[1]}',
                                            attachment=f'{couple[2][0]},{couple[2][1]},{couple[2][2]}')
                            user_table_name = f'id{event.user_id}'
                            couple_id = f'{couple[1][15:]}'

                            engine = sq.create_engine(DSN)
                            Session = sessionmaker(bind=engine)
                            session = Session()
                            User = create_models(user_table_name)
                            create_table(engine)
                            try:
                                table_columns = User(id_couple=couple_id, name_couple=couple[0])
                                session.add(table_columns)
                                session.commit()
                            except:
                                pass
                            session.close()
                        except:
                            continue

                offset += 50
                write_msg(event.user_id, 'для продолжения поиска введите "поиск" ')

def run_bot():
    get_user()
    while True:
        run()





run_bot()

