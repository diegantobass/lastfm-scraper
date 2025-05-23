import csv
import time
import argparse
import logging
import requests
from tqdm import tqdm
from bs4 import BeautifulSoup
from pathlib import Path

logger = logging.getLogger()
temps_debut = time.time()

# scrape infos from a page of similar artists
def get_similars(soup):
    artists = []
    for item in soup.find_all("li", {"class": "similar-artists-item-wrap"}):
        name = item.find("h3", {"class": "similar-artists-item-name"})
        if name != None:
            name = name.find("a").text
            listens = item.find("p", {"class": "similar-artists-item-listeners"}).text
            listens = listens.strip().split(" ")[0].replace(',','')
            tags = ','.join([x.text for x in item.find_all("li", {"class": "tag"})])
            #description = item.find("div", {"similar-artists-item-wiki-inner-2"}).text
            artist = [name, listens, tags]
            artists.append(artist)
        else:
            pass
    return artists

# scrape all (fixed 239) similar artists for a given artist name
def scrape_artist(artist, restricted):
    try:
        url = f"https://www.last.fm/music/{artist}/+similar"
        soup = BeautifulSoup(requests.get(url).content, "lxml")
        similars = []
        if restricted:
            similars = similars + get_similars(soup)
        else:
            while soup.find("li", {"class": "pagination-next"}):
                similars = similars + get_similars(soup)
                logger.debug("Total artists number : %s", len(similars))
                lien = soup.find("li", {"class": "pagination-next"}).find("a")["href"]
                logger.debug("Next page : %s/{lien}", url)
                soup = BeautifulSoup(requests.get(f"{url}/{lien}").content, "lxml")
        return similars
    except Exception as e:
        logger.error("%s", e)

# main handles output dir creation and options
def main():
    args = parse_args()
    if not args.artists and not args.input:
        raise Exception("Use the -a flag or the -i flag to input artists to scrap.")
    if args.artists:
        artists = [x.strip() for x in args.artists.split(",")]
    if args.input:
        artists = []
        for artist in csv.reader(args.input):
            artists.append(artist[0])

    Path("Exports").mkdir(parents=True, exist_ok=True)

    for artist in tqdm(artists, dynamic_ncols=True):
        artist_output_file = Path("Exports/" + artist + "_similar-artists_bs4.csv")
        if not artist_output_file.is_file():

            if args.restricted:
                similars = scrape_artist(artist, True)
            else:
                similars = scrape_artist(artist, False)

            if args.deeper:
                similars_of_similars = []
                print("Scraping similar artists of " + artist)
                for similar in tqdm(similars, dynamic_ncols=True):
                    if args.restricted:
                        similars_of_similars.extend(scrape_artist(similar[0], True))
                    else:
                        similars_of_similars.extend(scrape_artist(similar[0], False))

                similars = similars + similars_of_similars

            with open(f"Exports/{artist}_similar-artists_bs4.csv", "w") as f:
                output = csv.writer(f)
                if similars != None and len(similars) > 0:
                    for artist in similars:
                        output.writerow(artist)

    logger.info("Runtime : %.2f seconds" % (time.time() - temps_debut))

# cli argument parsing
def parse_args():
    parser = argparse.ArgumentParser(description="artist lastfm scraper.")
    parser.add_argument(
        "--debug",
        help="Display debugging information.",
        action="store_const",
        dest="loglevel",
        const=logging.DEBUG,
        default=logging.WARNING,
    )
    parser.add_argument(
        "-a",
        "--artists",
        type=str,
        help="artists to scrap (separated by comma).",
    )
    parser.add_argument(
        "-i",
        "--input",
        type=argparse.FileType('r'),
        help="comma-separated file containing a list of artists in its first column. Typically a lastfm-scraper output file."
    )
    parser.add_argument(
        "-d",
        "--deeper",
        action='store_true',
        help="Deepen the crawl: get similar artists of the similar artists!"
    )
    parser.add_argument(
        "-r",
        "--restricted",
        action='store_true',
        help="Will scrape only the first page of similar artists of the similar artists"
    )
    args = parser.parse_args()

    logging.basicConfig(level=args.loglevel)
    return args

if __name__ == "__main__":
    main()
