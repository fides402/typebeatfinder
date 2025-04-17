import os
import json
import time
import requests
from urllib.parse import quote
from bs4 import BeautifulSoup

# Percorso al file JSON contenente i libri
BOOKS_PATH = os.path.join(os.path.dirname(__file__), "../data/books.json")

def get_cover_from_ibs(title, author):
    """
    Funzione per ottenere l'URL della copertina di un libro da IBS.it
    
    Args:
        title (str): Titolo del libro
        author (str): Autore del libro
    
    Returns:
        str: URL dell'immagine della copertina o stringa vuota se non trovata
    """
    # Formatta la query di ricerca per IBS
    query = f"{title} {author}"
    encoded_query = quote(query)
    
    # URL di ricerca su IBS
    search_url = f"https://www.ibs.it/search/?ts=as&query={encoded_query}"
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
        "Accept-Language": "it-IT,it;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8"
    }
    
    try:
        # Esegui la ricerca su IBS
        print(f"Ricerca su IBS per: {title} di {author}")
        response = requests.get(search_url, headers=headers, timeout=15)
        response.raise_for_status()
        
        # Analizza la pagina di ricerca
        soup = BeautifulSoup(response.text, "html.parser")
        
        # Cerca i risultati della ricerca
        book_items = soup.select(".search-item-book")
        
        if not book_items:
            print(f"Nessun risultato trovato per '{title}' di {author}")
            return ""
        
        # Prendi il primo risultato (il più rilevante)
        first_book = book_items[0]
        
        # Trova il link alla pagina del libro
        book_link_element = first_book.select_one(".description a")
        if not book_link_element:
            print(f"Link non trovato per '{title}'")
            return ""
        
        book_link = book_link_element.get("href")
        if not book_link.startswith("http"):
            book_link = "https://www.ibs.it" + book_link
        
        # Visita la pagina del libro
        print(f"Accesso alla pagina del libro: {book_link}")
        book_response = requests.get(book_link, headers=headers, timeout=15)
        book_response.raise_for_status()
        
        book_soup = BeautifulSoup(book_response.text, "html.parser")
        
        # Cerca l'ISBN nella pagina (spesso presente nell'URL o nei meta tag)
        isbn = None
        
        # Estrai ISBN dall'URL se è nel formato standard
        # Esempio: https://www.ibs.it/sentiero-del-sale-libro-raynor-winn/e/9788807034664
        if "/e/" in book_link:
            isbn = book_link.split("/e/")[1].strip()
        
        # Se non troviamo l'ISBN nell'URL, cerchiamo nei meta tag
        if not isbn:
            meta_isbn = book_soup.select_one('meta[property="og:url"]')
            if meta_isbn and "/e/" in meta_isbn.get("content", ""):
                isbn = meta_isbn.get("content").split("/e/")[1].strip()
        
        # Se abbiamo trovato un ISBN, costruiamo direttamente l'URL dell'immagine
        if isbn and len(isbn) >= 10:
            # Il formato tipico dell'URL della copertina su IBS
            cover_url = f"https://www.ibs.it/images/{isbn}_0_0_536_0_75.jpg"
            print(f"Copertina trovata con ISBN: {cover_url}")
            return cover_url
        
        # Se non troviamo l'ISBN, cerchiamo direttamente l'immagine nella pagina
        cover_img = book_soup.select_one('img[src*="/images/"][src*=".jpg"]')
        if cover_img:
            cover_url = cover_img.get("src")
            # Assicuriamoci che l'URL sia completo
            if not cover_url.startswith("http"):
                cover_url = "https://www.ibs.it" + cover_url
            print(f"Copertina trovata nella pagina: {cover_url}")
            return cover_url
        
        print(f"Nessuna copertina trovata per '{title}'")
        return ""
        
    except Exception as e:
        print(f"[IBS] Errore per '{title}': {str(e)}")
        return ""

def enrich_books_with_ibs_covers():
    """
    Arricchisce il file JSON dei libri con le copertine da IBS
    """
    if not os.path.exists(BOOKS_PATH):
        print(f"File non trovato: {BOOKS_PATH}")
        return
    
    # Carica il file JSON
    with open(BOOKS_PATH, "r", encoding="utf-8") as file:
        books = json.load(file)
    
    total_books = len(books)
    processed = 0
    updated = 0
    
    for book in books:
        processed += 1
        title = book.get("title", "")
        author = book.get("author", "")
        
        # Salta i libri che hanno già una copertina
        if book.get("cover_url") and book.get("cover_url").strip():
            print(f"[{processed}/{total_books}] '{title}' ha già una copertina, saltato.")
            continue
        
        if not title:
            print(f"[{processed}/{total_books}] Libro senza titolo, saltato.")
            continue
        
        print(f"[{processed}/{total_books}] Ricerca copertina per '{title}' di {author}")
        
        # Ottieni la copertina da IBS
        cover_url = get_cover_from_ibs(title, author)
        
        if cover_url:
            book["cover_url"] = cover_url
            updated += 1
            print(f"✓ Copertina aggiunta per '{title}'")
        else:
            print(f"✗ Copertina non trovata per '{title}'")
        
        # Salva il file dopo ogni aggiornamento per evitare perdite in caso di errori
        with open(BOOKS_PATH, "w", encoding="utf-8") as file:
            json.dump(books, file, ensure_ascii=False, indent=2)
        
        # Piccola pausa per non sovraccaricare il server
        time.sleep(2)
    
    print(f"\nOperazione completata: {updated} copertine aggiunte su {total_books} libri.")

if __name__ == "__main__":
    print("Avvio del processo di arricchimento dei libri con copertine da IBS...")
    enrich_books_with_ibs_covers()
    print("Processo completato!")
