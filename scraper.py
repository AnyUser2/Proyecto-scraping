from pathlib import Path
from urllib.parse import urlparse

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.support.ui import WebDriverWait

import config
from parseo import (
    buscar_enlaces,
    buscar_siguiente_pagina,
    leer_publicaciones,
    limpiar,
    url_busqueda,
)


def buscar(driver, texto, estado):
    url = url_busqueda(texto, estado)
    driver.get(url)
    WebDriverWait(driver, config.ESPERA).until(
        lambda navegador: bool(buscar_enlaces(navegador.page_source, 1))
        or any(
            frase in limpiar(navegador.page_source)
            for frase in (
                "no hay publicaciones",
                "no encontramos resultados",
                "sin resultados",
            )
        )
    )

    if f"/{estado}/" not in urlparse(driver.current_url).path:
        print(f"Mercado Libre quitó el filtro '{estado}'.")
    print(f"Filtro {estado} activo: {driver.current_url}")


def ejecutar():
    perfil = Path(r"C:\SeleniumProfile")
    perfil.mkdir(parents=True, exist_ok=True)
    opciones = Options()
    opciones.add_argument(f"--user-data-dir={perfil}")
    navegador = webdriver.Chrome(options=opciones)
    publicaciones = []

    for estado in ("nuevo", "usado"):
        print(f"Buscando equipo {estado}...")
        buscar(navegador, config.BUSQUEDA, estado)

        guardadas = 0
        paginas_vistas = set()
        enlaces_vistos = set()

        for _ in range(config.PAGINAS_MAX):
            url_pagina = navegador.current_url
            if url_pagina in paginas_vistas:
                break
            paginas_vistas.add(url_pagina)

            html = navegador.page_source
            avisos, conteo = leer_publicaciones(
                html, estado, config.PALABRAS, config.CANTIDAD - guardadas
            )
            siguiente = buscar_siguiente_pagina(html, url_pagina)
            print(
                f"Página: {conteo['tarjetas']} tarjetas, "
                f"{conteo['modelo']} del modelo, "
                f"{conteo['precio']} con precio."
            )

            for aviso in avisos:
                if aviso["url"] in enlaces_vistos:
                    continue
                enlaces_vistos.add(aviso["url"])
                publicaciones.append(aviso)
                guardadas += 1
                print(f'{aviso["condicion"]}: {aviso["titulo"]} - ${aviso["precio"]}')

            if guardadas >= config.CANTIDAD or siguiente is None:
                break

            navegador.get(siguiente)
            WebDriverWait(navegador, config.ESPERA).until(
                lambda pagina: (
                    pagina.current_url != url_pagina
                    and bool(buscar_enlaces(pagina.page_source, 1))
                )
            )
            if f"/{estado}/" not in urlparse(navegador.current_url).path:
                print(f"Se perdió el filtro '{estado}' al pasar a otra página.")

        if guardadas == 0:
            print(f"No se encontraron avisos {estado}.")
        elif guardadas < config.CANTIDAD:
            print(f"Solo se encontraron {guardadas} avisos {estado} en las páginas revisadas.")

    navegador.quit()
    print(f"\nSe encontraron {len(publicaciones)} avisos en esta ejecución.")
    return publicaciones
