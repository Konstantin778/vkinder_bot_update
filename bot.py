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

def write_msg(user_id, message, attachment):
    vk_session.method("messages.send", {"user_id": user_id, "message": message, "attachment": attachment,  "random_id": get_random_id()})

def run_bot():
    offset = 0
    while True:
        for event in longpoll.listen():
            if event.type == VkEventType.MESSAGE_NEW and event.to_me and event.text:
                request = event.text
                if request.lower() == "поиск" or request.lower() == "search":

                    def get_user():
                        user_id = event.user_id
                        user = (vk_client.get_params(user_ids=user_id)["response"][0])
                        if "bdate" not in user.keys():
                            write_msg(event.user_id, f'Недостаточно данных для поиска пары.'
                                                     f' Укажите дату рождения в настройках профиля и разрешите её показ')
                            return False
                        if "city" not in user.keys():
                            write_msg(event.user_id, f'Недостаточно данных для поиска пары. Укажите в профиле город своего проживания')
                            return False
                        try:
                            return user
                        except vk_api.exceptions.ApiError:
                            write_msg(event.user_id, f'Ошибка api Вконтакте')
                            return False

                    def get_offset():
                        return offset

                    def get_offered_people():
                        birth_year = int(get_user()["bdate"][-4:])
                        current_year = date.today().year
                        age = current_year - birth_year

                        sex = 0
                        if get_user()["sex"] == 1:
                            sex += 2
                        else:
                            sex += 1
                        user_city = get_user()["city"]["id"]
                        relation = get_user()["relation"]
                        offered_people = vk_client.search_people(age - 1, age + 1, sex, user_city, relation, get_offset())
                        try:
                            return offered_people
                        except vk_api.exceptions.ApiError:
                            write_msg(event.user_id, f'Ошибка api Вконтакте')
                            return False

                    def get_people_ids():
                        people_ids = []
                        for people in get_offered_people():
                            if people['is_closed'] == False:
                                people_info = (people["id"], f'{people["first_name"]} {people["last_name"]}')
                                people_ids.append(people_info)
                        return people_ids

                    def get_whole_info():
                        whole_info = []
                        for couple in get_people_ids():
                            couple_name = couple[1]
                            try:
                                id_couple = f'https://vk.com/id{vk_client.get_photos(owner_id=str(couple[0]))[1]}'
                                all_photos = vk_client.get_photos(owner_id=str(couple[0]))[0]
                            except vk_api.exceptions.ApiError:
                                write_msg(event.user_id, f'Ошибка api Вконтакте')
                                return False

                            photos_ids = {}
                            if len(all_photos) >= 3:
                                for photo in all_photos:
                                    photos_ids[(photo["id"])] = photo["comments"]["count"] + photo["likes"][
                                                 "count"] + photo["likes"]["user_likes"]
                            sorted_ids = (sorted(photos_ids.items(), key=lambda x: x[1]))[-3:]
                            only_ids = []
                            for id in sorted_ids:
                                only_ids.append(f'photo{id_couple[17:]}_{id[0]}')
                            info = (couple_name, id_couple, only_ids)
                            whole_info.append(info)
                        return whole_info

                    for couple in get_whole_info():
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


run_bot()


