from nltk.sentiment.vader import SentimentIntensityAnalyzer
import os
import fitz
import re
from models.db import db


def extract_text_from_pdf(pdf_path):
    """
    Extract text content from a PDF file.
    Args:
        pdf_path (str): Path to the PDF file
    Returns:
        str: Extracted text from the PDF
    """
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page_num in range(len(doc)):
            page = doc.load_page(page_num)
            text += page.get_text("text")
        doc.close()
        return text
    except Exception as e:
        print(f"Error extracting text from PDF {pdf_path}: {e}")
        return ""


def clean_text(text):
    """
    Clean and normalize text for sentiment analysis.
    Args:
        text (str): Raw text to clean
    Returns:
        str: Cleaned text
    """
    text = text.lower()
    text = re.sub(r'[^a-z0-9\s]', '', text)
    return text


def get_sentiment_counts(text):
    """
    Analyze sentiment of text and return sentiment classification.
    Args:
        text (str): Text to analyze
    Returns:
        tuple: (is_positive, is_negative, is_neutral)
    """
    sia = SentimentIntensityAnalyzer()
    sentiment_scores = sia.polarity_scores(text)

    is_positive = 1 if sentiment_scores['compound'] > 0 else 0
    is_negative = 1 if sentiment_scores['compound'] < 0 else 0
    is_neutral = 1 if sentiment_scores['compound'] == 0 else 0

    return (is_positive, is_negative, is_neutral)


def get_company_pdfs(company_code):
    """
    Get list of PDF files for a specific company.
    Args:
        company_code (str): Company code to search for
    Returns:
        list: List of PDF filenames for the company
    """
    pdf_folder = r"C:\Leonora Siljanovska\FINKI\3 godina\DAS\Homework3\pdfs"
    return [f for f in os.listdir(pdf_folder)
            if f.startswith(company_code) and f.endswith('.pdf')]


def determine_recommendation(positive_count, negative_count):
    """
    Determine recommendation based on sentiment counts.
    Args:
        positive_count (int): Number of positive sentiments
        negative_count (int): Number of negative sentiments
    Returns:
        str: Recommendation in Macedonian
    """
    if positive_count > negative_count:
        return "Buy"
    elif negative_count > positive_count:
        return "Sell"
    else:
        return "Hold"


def perform_nlp_recommendation(company_code):
    """
    Main function to perform NLP analysis and generate recommendation.
    Args:
        company_code (str): Company code to analyze
    Returns:
        str: Investment recommendation in Macedonian
    """
    try:
        # Get company PDFs
        company_pdfs = get_company_pdfs(company_code)

        if not company_pdfs:
            print(f"No PDFs found for company {company_code}")
            return

        # Initialize counters
        positive_count = 0
        negative_count = 0
        neutral_count = 0

        # Process each PDF
        pdf_folder = r"C:\Leonora Siljanovska\FINKI\3 godina\DAS\Homework3\pdfs"
        for pdf_file in company_pdfs:
            try:
                # Extract and process text
                pdf_path = os.path.join(pdf_folder, pdf_file)
                raw_text = extract_text_from_pdf(pdf_path)
                if not raw_text:
                    continue

                cleaned_text = clean_text(raw_text)

                # Get sentiment counts
                pos, neg, neu = get_sentiment_counts(cleaned_text)
                positive_count += pos
                negative_count += neg
                neutral_count += neu

            except Exception as e:
                print(f"Error processing PDF {pdf_file}: {e}")
                continue

        # Get final recommendation
        recommendation = determine_recommendation(positive_count, negative_count)
        return recommendation

    except Exception as e:
        print(f"Error in perform_nlp_recommendation: {e}")
        return