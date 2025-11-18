#!/usr/bin/env python3

import logging
from bq_vector import retrieve_similar_questions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def main():
    try:
        query_content = "Customer Name: Cloud Ace, Requirements: Build a support tool for creating documents based on historical data, Business domain: IT and software service"
        
        logger.info("Starting BigQuery retrieval demo...")
        logger.info(f"Query: {query_content}")
        
        similar_questions = retrieve_similar_questions(
            query_content=query_content,
            top_k=10
        )
        
        if similar_questions:
            logger.info(f"Found {len(similar_questions)} similar questions")
            print("\n" + "="*80)
            print("TOP SIMILAR QUESTIONS")
            print("="*80)
            
            for i, q in enumerate(similar_questions, 1):
                print(f"\n{i}. SCORE: {q['similarity_score']:.4f}")
                print(f"   TITLE: {q['title']}")
                print(f"   SECTION: {q['section']}")
                print(f"   QUESTION: {q['question']}")
                print("-" * 60)
        else:
            logger.warning("No similar questions found")
            
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")
        raise

def test_custom_query(query: str, top_k: int = 5):
    try:
        logger.info(f"Testing custom query: {query}")
        return retrieve_similar_questions(query_content=query, top_k=top_k)
    except Exception as e:
        logger.error(f"Error in test_custom_query: {str(e)}")
        return []

if __name__ == "__main__":
    main()