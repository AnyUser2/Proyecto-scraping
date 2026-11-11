import config


def ejecutar(publicaciones):
    precios = {"nuevo": [], "usado": []}

    for aviso in publicaciones:
        condicion = aviso["condicion"]
        if condicion in precios:
            precios[condicion].append(float(aviso["precio"]))

    print(f"\nPromedio de precios del {config.MODELO}:")
    promedios = {}
    for condicion, lista in precios.items():
        if lista:
            promedios[condicion] = sum(lista) / len(lista)
            print(f"{condicion.title()}: ${promedios[condicion]:,.0f} ({len(lista)} avisos)")
        else:
            print(f"{condicion.title()}: no hay avisos")

    if "nuevo" in promedios and "usado" in promedios:
        diferencia = promedios["nuevo"] - promedios["usado"]
        print(f"Diferencia entre promedios: ${diferencia:,.0f}")
