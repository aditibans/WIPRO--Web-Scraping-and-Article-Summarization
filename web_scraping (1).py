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
        website_urls = data["Website URL"].tolist()
        search_keywords = data["Search Keyword"].tolist()
        return website_urls, search_keywords
    except Exception as e:
        # Log the error for debugging
        print(f"Error reading CSV file: {e}")
        return [], []

def scrape_websites(urls, keywords):
    matched_articles = []

    for url in urls:
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

                    if any(keyword in article_text for keyword in keywords):
                        matched_articles.append(absolute_link)
                except Exception as e:
                    # Log the error for debugging
                    print(f"Error while scraping article {absolute_link}: {e}")
        except Exception as e:
            # Log the error for debugging
            print(f"Error while fetching URL {url}: {e}")

    return matched_articles

def summarize_article(article_url):
    try:
        scraped_data = urllib.request.urlopen(article_url)
        article = scraped_data.read()

        parsed_article = bs.BeautifulSoup(article, 'lxml')

        paragraphs = parsed_article.find_all('p')

        article_text = ""

        for p in paragraphs:
            article_text += p.text

        article_text = re.sub(r'\[[0-9]*\]', ' ', article_text)
        article_text = re.sub(r'\s+', ' ', article_text)

        formatted_article_text = re.sub('[^a-zA-Z]', ' ', article_text)
        formatted_article_text = re.sub(r'\s+', ' ', formatted_article_text)

        sentence_list = nltk.sent_tokenize(article_text)

        stopwords = nltk.corpus.stopwords.words('english')

        word_frequencies = {}
        for word in nltk.word_tokenize(formatted_article_text):
            if word not in stopwords:
                if word not in word_frequencies.keys():
                    word_frequencies[word] = 1
                else:
                    word_frequencies[word] += 1

        maximum_frequency = max(word_frequencies.values())

        for word in word_frequencies.keys():
            word_frequencies[word] = (word_frequencies[word] / maximum_frequency)

        sentence_scores = {}
        for sent in sentence_list:
            for word in nltk.word_tokenize(sent.lower()):
                if word in word_frequencies.keys():
                    if len(sent.split(' ')) < 50:
                        if sent not in sentence_scores.keys():
                            sentence_scores[sent] = word_frequencies[word]
                        else:
                            sentence_scores[sent] += word_frequencies[word]

        summary_sentences = heapq.nlargest(7, sentence_scores, key=sentence_scores.get)

        summary = ' '.join(summary_sentences)
        return summary
    except Exception as e:
        # Log the error for debugging
        print(f"Error while summarizing article {article_url}: {e}")
        return None

@app.route('/')
def show_results():
    try:
        # Read URLs and keywords from the CSV file
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
        # Log the error for debugging
        print(f"An error occurred: {e}")
        return "Oops! Something went wrong."

if __name__ == '__main__':
    app.run(debug=True)

