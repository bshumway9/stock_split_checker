from dotenv import dotenv_values
import logging
import time
from google import genai
from helper_functions import sort_key

env = dotenv_values(".env")

# Configure Gemini API
def configure_gemini():
    """Configure Gemini API client with API key from environment variables."""
    api_key = env.get('GEMINI_API_KEY')
    if not api_key:
        logging.warning("Gemini API key not found in environment variables")
        return None
    
    # Initialize the Gemini client with the API key
    client = genai.Client(api_key=api_key)
    return client

def check_roundup(splits):
    """
    Use Gemini API with grounding to check if companies are rounding up fractional shares in reverse splits.
    Uses Google Search as a grounding tool to get up-to-date information from the web.
    
    Args:
        splits (list): List of dictionaries containing reverse split information
    
    Returns:
        list: The same splits list with updated 'fractional' information
    """
    client = configure_gemini()
    if not client:
        logging.warning("Gemini API not configured, skipping fractional shares check")
        return splits
    
    # Define the grounding tool for Google Search
    grounding_tool = genai.types.Tool(
        google_search=genai.types.GoogleSearch()
    )
    
    # Configure generation settings
    config = genai.types.GenerateContentConfig(
        tools=[grounding_tool],
        temperature=0.2,  # Lower temperature for more factual responses
        top_k=40,
        top_p=0.95,
        max_output_tokens=500
    )
    
    for i, split in enumerate(splits):
        symbol = split.get('symbol')
        company = split.get('company', '')
        date = split.get('effective_date', '')
        ratio = split.get('ratio', '')
        article_link = split.get('article_link', [])
        
        if not symbol:
            continue
            
        try:
            # Create a more specific prompt with context to help the search
            article_info = ""
            if article_link and len(article_link) > 0:
                logging.info(f"Found {len(article_link)} article links for {symbol}, including in prompt")
                if len(article_link) == 1:
                    article_info = f"\nAdditionally, please check this specific article about the split: {article_link[0]}"
                else:
                    article_links_text = "\n".join([f"- {link}" for link in article_link])
                    article_info = f"\nAdditionally, please check these specific articles about the split:\n{article_links_text}"
            else:
                logging.info(f"No article links found for {symbol}, skipping article info in prompt")
            
            prompt = f"""
            Search for factual information about how {symbol} ({company}) will handle fractional shares 
            in their upcoming reverse stock split (ratio: {ratio}) scheduled for {date}.
            Please specifically search for their latest SEC filings, press releases, or investor relations
            information about this reverse split for the most up to date and accurate information.{article_info}

            Based on factual information only, tell me how they will handle fractional shares after this split:
            1. Will they round up fractional shares to the nearest whole share?
            2. Will they pay cash in lieu of fractional shares?
            3. Will they round down fractional shares?
            4. Will they round up only if fractional shares exceed a certain threshold?
            5. Is there another method they will use?

            Respond with only one of these exact phrases:
            "ROUND_UP" - if they'll certainly round up to nearest whole share
            "CASH_IN_LIEU" - if they'll certainly pay cash for fractional shares
            "ROUND_DOWN" - if they'll certainly round down
            "THRESHOLD ROUND_UP" - if they'll certainly round up only if fractional shares exceed a certain threshold
            "OTHER: [brief explanation]" - for other methods or uncertainty (explain briefly)
            "NO_INFO" - if no information is available
            
            Do not include any explanations, just respond with one of these exact phrases.
            """
            # prompt = f"""
            # You must use the Google Search grounding tool and base your decision ONLY on content you open with it.
            # Do not use prior knowledge. If you cannot open an authoritative source that explicitly states the policy,
            # respond NO_INFO.

            # Task
            # Determine how {symbol} ({company}) will handle fractional shares in the reverse stock split with ratio {ratio}
            # scheduled for {date}.

            # Authority order (strict)
            # 1) SEC filings on sec.gov for this issuer that mention this reverse split and fractional shares
            #    (e.g., 8-K, 6-K, DEF 14A/14C/Information Statement, S-1/S-3 prospectus, 10-Q/10-K, Form 25, Certificate of Amendment).
            # 2) Official issuer press release or investor relations page that explicitly describes fractional share treatment.
            # Ignore blogs, forums, third-party summaries, brokers, and news sites unless they link to and quote an SEC filing.

            # Grounding protocol
            # - First search: site:sec.gov {symbol} {company} "reverse stock split" fractional {ratio} {date}
            # - Also try variations: "cash in lieu", "no fractional shares", "rounded", "fractional", "reverse split".
            # - Open the most recent filing related to this split. Verify issuer matches the ticker/company and that ratio/date align.
            # - Extract the exact language about fractional shares. If unclear, search again or open another filing.
            # - If sources conflict or the filing is about a different event, respond NO_INFO.

            # Decision mapping (use the extracted sentence to choose exactly one)
            # - Says no fractional shares will be issued and cash will be paid for any fractional share -> CASH_IN_LIEU
            # - Says fractional shares will be rounded up to the nearest whole share, or each holder receives one whole share in place of any fractional interest -> ROUND_UP
            # - Says fractional shares will be rounded down (truncated) -> ROUND_DOWN
            # - Says rounding up occurs only above a specific threshold (e.g., >= 0.5 share, "nearest whole share") -> THRESHOLD ROUND_UP
            # - Any other explicit treatment (e.g., aggregate fractional interests, broker/record-holder aggregation, scrip) -> OTHER: <brief explanation>
            # - If you cannot find an authoritative source per the order above, or the ratio/date/issuer do not match -> NO_INFO

            # Output
            # Respond with only one of these exact strings and nothing else:
            # ROUND_UP
            # CASH_IN_LIEU
            # ROUND_DOWN
            # THRESHOLD ROUND_UP
            # OTHER: <brief explanation>
            # NO_INFO
            # """
            
            # Query Gemini API with grounding
            logging.info(f"Querying Gemini API for {symbol} with grounding")
            response = client.models.generate_content(
                model="gemini-2.5-flash",  # or gemini-1.5-pro if you prefer
                contents=prompt,
                config=config
            )
            
            result = response.text.strip() if response.text is not None else ""
            if result == "":
                logging.warning(f"No response text for {symbol} defaulting to NO_INFO, api response: {response.body}")
                result = "NO_INFO"
            logging.info(f"Grounded Gemini API response for {symbol}: {result}")
            
            # Update the split information based on response
            if "ROUND_UP" in result:
                splits[i]['fractional'] = "Rounded up to nearest whole share"
            elif "CASH_IN_LIEU" in result:
                splits[i]['fractional'] = "Cash payment for fractional shares"
            elif "ROUND_DOWN" in result:
                splits[i]['fractional'] = "Rounded down to nearest whole share"
            elif "THRESHOLD ROUND_UP" in result:
                splits[i]['fractional'] = "Rounded up if fractional shares exceed a certain threshold"
            elif result.startswith("OTHER:"):
                splits[i]['fractional'] = result.replace("OTHER:", "").strip()
            else:
                splits[i]['fractional'] = "Not specified"
                
            # Don't overwhelm the API, add a small delay between requests
            time.sleep(1)
            
        except Exception as e:
            logging.error(f"Error querying Gemini API for {symbol}: {e}")
            logging.error(f"Exception details: {str(e)}")
            splits[i]['fractional'] = "Error checking fractional shares handling"
    # Order splits by fractional handling
    # Remove splits where fractional handling is "cash payment for fractional shares" or "rounded down to nearest whole share"
    splits = [
        split for split in splits
        if split.get('fractional', '').lower() not in [
            "cash payment for fractional shares",
            "rounded down to nearest whole share"
        ]
    ]

    splits.sort(key=sort_key)
    return splits