import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import random
import bs4 as bs
import urllib.request
import re
import heapq
import nltk
import pandas as pd
from flask import Flask, render_template

app = Flask(__name__)

def read_csv_file(csv_file):
    try:
        data = pd.read_csv(csv_file)
        website_urls = data["URL"].tolist()
        search_keywords = data["Keyword"].tolist()
        return website_urls, search_keywords
    except Exception as e:
        print(f"Error reading CSV file: {e}")
        return [], []

def scrape_websites(website_urls, search_keywords):
    matched_articles = []

    for url in website_urls:
        try:
            response = requests.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')
            articles = soup.find_all('article')

            for article in articles:
                try:
                    article_link = article.find('a')['href']
                    absolute_link = urljoin(url, article_link)

                    article_response = requests.get(absolute_link)
                    article_response.raise_for_status()

                    article_soup = BeautifulSoup(article_response.content, 'html.parser')
                    article_text = article_soup.get_text().lower().strip()

                    if any(keyword in article_text for keyword in search_keywords):
                        matched_articles.append(absolute_link)
                except Exception as e:
                    print(f"Error while scraping article {absolute_link}: {e}")
        except Exception as e:
            print(f"Error while fetching URL {url}: {e}")

    return matched_articles

def summarize_article(article_url):
    try:
        scraped_data = urllib.request.urlopen(article_url)
        article = scraped_data.read()

        parsed_article = bs.BeautifulSoup(article, 'lxml')

        paragraphs = parsed_article.find_all('p')
        article_text = ' '.join(p.text for p in paragraphs)

        article_text = re.sub(r'\[[0-9]*\]', ' ', article_text)
        article_text = re.sub(r'\s+', ' ', article_text)

        formatted_article_text = re.sub('[^a-zA-Z]', ' ', article_text)
        formatted_article_text = re.sub(r'\s+', ' ', formatted_article_text)

        word_frequencies = {}
        for word in nltk.word_tokenize(formatted_article_text):
            if word not in nltk.corpus.stopwords.words('english'):
                word_frequencies[word] = word_frequencies.get(word, 0) + 1

        maximum_frequency = max(word_frequencies.values())

        for word, frequency in word_frequencies.items():
            word_frequencies[word] = frequency / maximum_frequency

        sentence_list = nltk.sent_tokenize(article_text)
        sentence_scores = {sent: sum(word_frequencies.get(word, 0) for word in nltk.word_tokenize(sent.lower()) if len(sent.split()) < 50) for sent in sentence_list}

        summary_sentences = heapq.nlargest(7, sentence_scores, key=sentence_scores.get)
        summary = ' '.join(summary_sentences)

        return summary
    except Exception as e:
        print(f"Error while summarizing article {article_url}: {e}")
        return None

@app.route('/')
def show_results():
    try:
        csv_file = "input_data.csv"
        website_urls, search_keywords = read_csv_file(csv_file)
        matched_articles = scrape_websites(website_urls, search_keywords)

        random_article_url = random.choice(matched_articles) if matched_articles else None
        summary = summarize_article(random_article_url) if random_article_url else None

        return render_template('results.html', website_urls=website_urls,
                               search_keywords=search_keywords,
                               matched_articles=matched_articles,
                               random_article_url=random_article_url,
                               summary=summary)
    except Exception as e:
        print(f"An error occurred: {e}")
        return "Oops! Something went wrong."

if __name__ == '__main__':
    app.run(debug=True)