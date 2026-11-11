import contextlib
import io
import unittest

import analisis
from parseo import (
    buscar_enlaces,
    buscar_siguiente_pagina,
    es_el_modelo,
    leer_aviso,
    leer_publicaciones,
    limpiar,
    url_busqueda,
)


class PruebasParseo(unittest.TestCase):
    def test_limpia_acentos_y_mayusculas(self):
        self.assertEqual(limpiar("IDEAPÁD 3"), "ideapad 3")

    def test_crea_url_con_filtro_de_condicion(self):
        url = url_busqueda("Portátil Ideapad 3", "nuevo")
        self.assertIn("/nuevo/portatil-ideapad-3_", url)
        self.assertIn("applied_value_id%3D2230284", url)

    def test_filtra_modelo_sin_distinguir_acentos(self):
        self.assertTrue(es_el_modelo("Lenovo IdeaPad 3", ["ideapad", "3"]))
        self.assertFalse(es_el_modelo("Lenovo IdeaPad 5", ["ideapad", "3"]))

    def test_lee_publicaciones_validas_y_omite_otras(self):
        html = """
        <ul>
          <li class="ui-search-layout__item">
            <a href="https://www.mercadolibre.com.co/lenovo-MCO123456789">
              Lenovo IdeaPad 3
            </a>
            <span class="andes-money-amount__fraction">2.500.000</span>
          </li>
          <li class="ui-search-layout__item">
            <a href="https://www.mercadolibre.com.co/lenovo-MCO987654321">
              Lenovo IdeaPad 5
            </a>
            <span class="andes-money-amount__fraction">3.000.000</span>
          </li>
        </ul>
        """

        avisos, conteo = leer_publicaciones(html, "nuevo", ["ideapad", "3"], 10)

        self.assertEqual(len(avisos), 1)
        self.assertEqual(avisos[0]["precio"], "2500000")
        self.assertEqual(avisos[0]["condicion"], "nuevo")
        self.assertEqual(
            avisos[0]["url"],
            "https://www.mercadolibre.com.co/lenovo-MCO123456789",
        )
        self.assertEqual(conteo, {"tarjetas": 2, "modelo": 1, "precio": 1})

    def test_busca_enlaces_de_publicaciones_sin_repetirlos(self):
        html = """
        <li class="ui-search-layout__item">
          <a href="https://www.mercadolibre.com.co/item-MCO123456789?tracking=1">
            Publicación
          </a>
          <a href="https://www.mercadolibre.com.co/item-MCO123456789">
            Duplicado
          </a>
        </li>
        """

        self.assertEqual(
            buscar_enlaces(html, 10),
            ["https://www.mercadolibre.com.co/item-MCO123456789"],
        )

    def test_encuentra_pagina_siguiente(self):
        html = '<a aria-label="Siguiente" href="/pagina-2">Siguiente</a>'

        self.assertEqual(
            buscar_siguiente_pagina(
                html, "https://listado.mercadolibre.com.co/busqueda"
            ),
            "https://listado.mercadolibre.com.co/pagina-2",
        )

    def test_lee_detalle_y_condicion_de_datos_estructurados(self):
        html = """
        <h1>Lenovo IdeaPad 3</h1>
        <meta itemprop="price" content="2500000">
        <script type="application/ld+json">
          {"itemCondition":"https://schema.org/UsedCondition"}
        </script>
        """

        aviso = leer_aviso(html, "https://ejemplo.test/item")

        self.assertEqual(aviso["titulo"], "Lenovo IdeaPad 3")
        self.assertEqual(aviso["precio"], "2500000")
        self.assertEqual(aviso["condicion"], "usado")


class PruebasAnalisis(unittest.TestCase):
    def test_calcula_promedios_por_condicion(self):
        publicaciones = [
            {"condicion": "nuevo", "precio": "300"},
            {"condicion": "nuevo", "precio": "500"},
            {"condicion": "usado", "precio": "200"},
        ]
        salida = io.StringIO()

        with contextlib.redirect_stdout(salida):
            analisis.ejecutar(publicaciones)

        self.assertIn("Nuevo: $400 (2 avisos)", salida.getvalue())
        self.assertIn("Usado: $200 (1 avisos)", salida.getvalue())
        self.assertIn("Diferencia entre promedios: $200", salida.getvalue())


if __name__ == "__main__":
    unittest.main()
