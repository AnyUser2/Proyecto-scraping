import json
import re
import unicodedata
from urllib.parse import urljoin

from bs4 import BeautifulSoup

ID_AVISO = re.compile(r"MCO-?\d{6,}", re.IGNORECASE)


def limpiar(texto):
    texto = unicodedata.normalize("NFKD", texto or "")
    return "".join(letra for letra in texto if not unicodedata.combining(letra)).lower()


def url_busqueda(texto, condicion):
    filtros = {
        "nuevo": ("2230284", "Nuevo", "1"),
        "usado": ("2230581", "Usado", "3"),
    }
    slug = re.sub(r"[^a-z0-9]+", "-", limpiar(texto)).strip("-")
    valor_id, nombre, orden = filtros[condicion]
    return (
        "https://listado.mercadolibre.com.co/"
        f"computacion/portatiles-accesorios/portatiles/{condicion}/"
        f"{slug}_NoIndex_True?sb=all_mercadolibre"
        "#applied_filter_id%3DITEM_CONDITION"
        "%26applied_filter_name%3DCondici%C3%B3n"
        "%26applied_filter_order%3D7"
        f"%26applied_value_id%3D{valor_id}"
        f"%26applied_value_name%3D{nombre}"
        f"%26applied_value_order%3D{orden}"
        "%26applied_value_results%3D20"
        "%26is_custom%3Dfalse"
    )


def buscar_enlaces(html, limite):
    pagina = BeautifulSoup(html, "lxml")
    tarjetas = pagina.select(
        "li.ui-search-layout__item, div.poly-card, div.ui-search-result__wrapper"
    )
    anclas = [ancla for tarjeta in tarjetas for ancla in tarjeta.select("a[href]")]
    if not anclas:
        anclas = pagina.select("a[href]")

    enlaces = []
    vistos = set()

    for ancla in anclas:
        url = ancla["href"].split("#")[0].split("?")[0]
        if ("mercadolibre.com.co" not in url
                or not ID_AVISO.search(url) and "click1" not in url
                or url in vistos):
            continue
        enlaces.append(url)
        vistos.add(url)
        if len(enlaces) == limite:
            break
    return enlaces


def leer_publicaciones(html, condicion, palabras, limite):
    pagina = BeautifulSoup(html, "lxml")
    tarjetas = pagina.select(
        "li.ui-search-layout__item, div.poly-card, div.ui-search-result__wrapper"
    )
    publicaciones = []
    vistos = set()
    modelos_encontrados = 0
    con_precio = 0

    for tarjeta in tarjetas:
        enlace = None
        titulo = ""
        for ancla in tarjeta.select("a[href]"):
            href = ancla.get("href", "")
            texto = ancla.get_text(" ", strip=True)
            if texto and ("mercadolibre.com.co" in href or href.startswith("/")):
                enlace = ancla
                titulo = texto
                break

        if enlace is None or not es_el_modelo(titulo, palabras):
            continue
        modelos_encontrados += 1

        url = urljoin("https://www.mercadolibre.com.co/", enlace["href"])
        url = url.split("#")[0].split("?")[0]
        if url in vistos:
            continue
        vistos.add(url)

        precio = tarjeta.select_one(
            ".andes-money-amount__fraction, "
            ".poly-price__current .andes-money-amount__fraction"
        )
        precio = re.sub(r"\D", "", precio.get_text()) if precio else ""
        if not precio:
            continue
        con_precio += 1

        titulo = titulo.replace(chr(8482), "").replace(chr(174), "")
        publicaciones.append({
            "url": url,
            "titulo": " ".join(titulo.split()),
            "precio": precio,
            "condicion": condicion,
        })
        if len(publicaciones) >= limite:
            break

    estadisticas = {
        "tarjetas": len(tarjetas),
        "modelo": modelos_encontrados,
        "precio": con_precio,
    }
    return publicaciones, estadisticas


def buscar_siguiente_pagina(html, url_actual):
    pagina = BeautifulSoup(html, "lxml")
    enlace = pagina.select_one(
        "a.andes-pagination__link[title='Siguiente'], "
        "li.andes-pagination__button--next a, "
        "a[aria-label='Siguiente']"
    )
    if enlace is None or not enlace.get("href"):
        return None
    return urljoin(url_actual, enlace["href"])


def leer_aviso(html, url, condicion_busqueda=None):
    pagina = BeautifulSoup(html, "lxml")
    titulo = pagina.select_one("h1")
    precio = pagina.select_one('meta[itemprop="price"]')

    if precio and precio.get("content"):
        precio = precio["content"]
    else:
        precio = pagina.select_one(".andes-money-amount__fraction")
        precio = re.sub(r"\D", "", precio.get_text()) if precio else ""

    condiciones_json = []

    def buscar_condiciones(dato):
        if isinstance(dato, dict):
            for clave, valor in dato.items():
                if clave.lower() == "itemcondition" and isinstance(valor, str):
                    condicion_json = limpiar(valor)
                    if "usedcondition" in condicion_json:
                        condiciones_json.append("usado")
                    elif "newcondition" in condicion_json:
                        condiciones_json.append("nuevo")
                buscar_condiciones(valor)
        elif isinstance(dato, list):
            for elemento in dato:
                buscar_condiciones(elemento)

    for script in pagina.select('script[type="application/ld+json"]'):
        buscar_condiciones(json.loads(script.get_text()))

    if condicion_busqueda in ("nuevo", "usado"):
        condicion = condicion_busqueda
    elif "usado" in condiciones_json and "nuevo" not in condiciones_json:
        condicion = "usado"
    elif "nuevo" in condiciones_json and "usado" not in condiciones_json:
        condicion = "nuevo"
    else:
        subtitulo = pagina.select_one(".ui-pdp-subtitle")
        texto = limpiar(subtitulo.get_text(" ", strip=True)) if subtitulo else ""
        if re.search(r"\busado\b", texto):
            condicion = "usado"
        elif re.search(r"\bnuevo\b", texto):
            condicion = "nuevo"
        else:
            condicion = "desconocido"

    titulo_texto = titulo.get_text(" ", strip=True) if titulo else ""
    titulo_texto = titulo_texto.replace(chr(8482), "").replace(chr(174), "")
    titulo_texto = " ".join(titulo_texto.split())

    return {
        "url": url,
        "titulo": titulo_texto,
        "precio": precio,
        "condicion": condicion,
    }


def es_el_modelo(titulo, palabras):
    titulo = limpiar(titulo)
    return all(limpiar(palabra) in titulo for palabra in palabras)
