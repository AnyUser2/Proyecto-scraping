import analisis


def main():
    import scraper

    publicaciones = scraper.ejecutar()
    analisis.ejecutar(publicaciones)


if __name__ == "__main__":
    main()
