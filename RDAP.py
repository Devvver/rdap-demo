import requests
import json
import streamlit as st
import re


def clean_domain(domain):
    """Удаляет протокол (http://, https://), www и лишние символы из домена."""
    domain = re.sub(r'^https?://', '', domain)  # Убираем http:// или https://
    domain = re.sub(r'^www\.', '', domain)  # Убираем www
    domain = domain.split('/')[0]  # Убираем всё после слэша
    return domain.strip()


def get_rdap_server(domain):
    """Получает RDAP-сервер для доменной зоны"""
    try:
        response = requests.get("https://data.iana.org/rdap/dns.json")
        data = response.json()
        domain_suffix = domain.split('.')[-1]
        for entry in data.get("services", []):
            if domain_suffix in entry[0]:
                return entry[1][0]
    except requests.RequestException as e:
        st.error(f"Ошибка при получении RDAP-сервера: {e}")
    return None


def get_domain_info(domain):
    """Получает информацию о домене через RDAP"""
    domain = clean_domain(domain)
    rdap_server = get_rdap_server(domain)
    if not rdap_server:
        st.error("Не удалось найти RDAP-сервер для домена.")
        return None, None

    rdap_url = f"{rdap_server}/domain/{domain}"
    try:
        response = requests.get(rdap_url)
        return response.json(), rdap_url
    except requests.RequestException as e:
        st.error(f"Ошибка при запросе RDAP: {e}")
        return None, None


def display_info(info, rdap_url):
    """Выводит информацию о домене в развернутом виде"""
    st.subheader("Общая информация")
    st.write(f"**Название:** {info.get('ldhName', 'Не найдено')}")
    st.write(f"**Статус:** {', '.join(info.get('status', []))}")

    events = {event.get('eventAction'): event.get('eventDate') for event in info.get('events', [])}
    st.write(f"**Создан:** {events.get('registration', 'Не найдено')}")
    st.write(f"**Истекает:** {events.get('expiration', 'Не найдено')}")
    st.write(f"**Последнее обновление:** {events.get('last changed', 'Не найдено')}")

    if "entities" in info:
        st.subheader("Контакты и организации")
        for entity in info["entities"]:
            roles = ', '.join(entity.get('roles', []))
            st.write(f"**Роли:** {roles}")

            if "vcardArray" in entity:
                vcard = entity["vcardArray"]
                if isinstance(vcard, list) and len(vcard) > 1:
                    for item in vcard[1]:
                        if item[0] == 'fn':
                            st.write(f"**Название:** {item[3]}")
                        elif item[0] == 'email':
                            st.write(f"**Email:** {item[3]}")
                        elif item[0] == 'tel':
                            st.write(f"**Телефон:** {item[3]}")

            for public_id in entity.get("publicIds", []):
                if public_id.get("type") == "IANA Registrar ID":
                    st.write(f"**IANA Registrar ID:** {public_id.get('identifier')}")

    if "nameservers" in info:
        st.subheader("Серверы имен (DNS)")
        for ns in info["nameservers"]:
            st.write(f"**Имя:** {ns.get('ldhName', 'Не найдено')}")

    if "notices" in info:
        st.subheader("Примечания")
        for notice in info["notices"]:
            st.write(f"**{notice.get('title', 'Не найдено')}**")
            for desc in notice.get('description', []):
                st.write(desc)

    if rdap_url:
        st.subheader("Источник данных")
        st.write(f"[Ссылка на RDAP-запрос]({rdap_url})")


st.title("RDAP Информация о домене")
domain = st.text_input("Введите домен (например, example.com):")
if st.button("Получить информацию"):
    if domain:
        info, rdap_url = get_domain_info(domain)
        if info:
            display_info(info, rdap_url)
    else:
        st.warning("Пожалуйста, введите домен.")
