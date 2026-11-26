import requests
from bs4 import BeautifulSoup
import csv
import time
import re
import os


class QuranLetterExtractor:
    def __init__(self):
        self.base_url = "https://corpus.quran.com/"
        self.session = requests.Session()
        self.session.headers.update({"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"})
        self.all_words = []

    def get_all_first_letters(self):
        """Get all possible first letters from the sectionArea div"""
        print("Fetching all Arabic letters...")
        response = self.session.get(self.base_url + "/qurandictionary.jsp")
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        section_area = soup.find("div", class_="sectionArea")
        if not section_area:
            raise ValueError("Could not find sectionArea div.")

        letters = section_area.find_all("a", href=True)
        return [(letter.text.strip(), letter["href"]) for letter in letters]

    def get_letter_sequences(self, letter_href):
        """Get all letter sequences for a specific letter"""
        print(f"Fetching letter sequences for {letter_href}...")
        response = self.session.get(self.base_url + "/qurandictionary.jsp" + letter_href)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        entry_list = soup.find("select", id="entryList")
        if not entry_list:
            raise ValueError("Could not find entryList dropdown.")

        sequences = entry_list.find_all("option", value=True)
        return [(seq.text.strip(), seq["value"]) for seq in sequences]

    def get_words_from_sequence(self, sequence_value):
        """Get all words for a specific letter sequence"""
        print(f"Fetching words for sequence {sequence_value}...")
        response = self.session.get(f"{self.base_url}/qurandictionary.jsp?q={sequence_value}")
        response.raise_for_status()
        soup = BeautifulSoup(response.text, "html.parser")

        taf_tables = soup.find_all("table", class_="taf")
        category = None
        words = {}
        arabic_words = set()

        # Extract category from the preceding <h4> tag
        for table in taf_tables:
            category_tag = table.find_previous("h4", class_="dxe")
            if category_tag:
                category = category_tag.text.strip()

            rows = table.find_all("tr")
            for row in rows:
                columns = row.find_all("td")
                if len(columns) < 3:
                    continue

                # Extract data from the row
                verse_ref = (
                    columns[0].find("span", class_="l").text.strip() if columns[0].find("span", class_="l") else ""
                )
                transliteration = (
                    columns[0].find("i", class_="ab").text.strip() if columns[0].find("i", class_="ab") else ""
                )
                morphology_url = self.base_url + columns[1].find("a")["href"] if columns[1].find("a") else ""
                english_text = columns[1].text.strip()
                arabic_word = (
                    columns[2].find("span", class_="auu").text.strip() if columns[2].find("span", class_="auu") else ""
                )
                context = columns[2].text.strip()

                # Avoid repeated entries by grouping by morphology_url
                if english_text not in words and arabic_word not in arabic_words:
                    words[english_text] = {
                        "verse_reference": verse_ref,
                        "transliteration": transliteration,
                        "morphology_url": morphology_url,
                        "english_text": english_text,
                        "arabic_word": arabic_word,
                        "quran_verse": context,
                        "category": category,
                    }
                    arabic_words.add(arabic_word)
        return list(words.values())

    def extract_all_data(self, writer):
        """Extract all data and save to a CSV file"""
        letters = self.get_all_first_letters()
        for letter, letter_href in letters:
            try:
                sequences = self.get_letter_sequences(letter_href)
                for sequence_text, sequence_value in sequences:
                    words = self.get_words_from_sequence(sequence_value)
                    for word in words:
                        self.all_words.append({"letter": letter, "sequence": sequence_text, **word})
                    time.sleep(0.2)  # Be polite to the server

                self.save_to_csv(writer)
                self.all_words = []
                # break  # Stop after processing one letter for testing
            except Exception as e:
                print(f"Error processing letter {letter}: {e}")

    def save_to_csv(self, writer):
        """Save all extracted data to a CSV file"""
        print("Saving data to file...")
        writer.writerows(self.all_words)
        print("Data saved successfully.")


if __name__ == "__main__":
    output_filename = "quran_words.csv"
    # Check if the file exists and is not empty to decide on writing the header
    file_exists = os.path.exists(output_filename) and os.path.getsize(output_filename) > 0

    extractor = QuranLetterExtractor()
    # Open in append mode 'a'
    with open(output_filename, mode="a", encoding="utf-8", newline="") as file:
        fieldnames = [
            "letter",
            "sequence",
            "arabic_word",
            "transliteration",
            "english_text",
            "category",
            "verse_reference",
            "quran_verse",
            "morphology_url",
        ]
        writer = csv.DictWriter(file, fieldnames=fieldnames)

        if not file_exists:
            writer.writeheader()
            print("CSV file created with headers.")
        else:
            print("Appending to existing CSV file.")

        extractor.extract_all_data(writer)
