from dotenv import dotenv_values
import logging
import time
import os
import signal
from contextlib import contextmanager
from google import genai
from helper_functions import sort_key

env = dotenv_values(".env")

# Timeout utilities
class _GeminiTimeout(Exception):
    pass

@contextmanager
def _time_limit(seconds: int):
    """Context manager to raise TimeoutError if block exceeds 'seconds'. Linux-only (uses SIGALRM)."""
    if not seconds or seconds <= 0:
        # No timeout requested
        yield
        return
    def _handler(signum, frame):
        raise _GeminiTimeout(f"Gemini call exceeded {seconds}s")
    prev = signal.signal(signal.SIGALRM, _handler)
    try:
        signal.setitimer(signal.ITIMER_REAL, seconds)
        yield
    finally:
        # Clear timer and restore handler
        signal.setitimer(signal.ITIMER_REAL, 0)
        signal.signal(signal.SIGALRM, prev)

def _call_gemini_with_timeout(client: genai.Client, *, model: str, contents: str, config, timeout_seconds: int):
    """Call Gemini with a hard timeout guard to avoid indefinite hangs."""
    with _time_limit(timeout_seconds):
        return client.models.generate_content(
            model=model,
            contents=contents,
            config=config,
        )

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

def extract_allowed_output(response, allowed_outputs):
    """
    Extracts the first allowed output phrase from Gemini response parts.
    """
    # Defensive: response.parts may be nested under response.content or response.candidates[0].content
    parts = []
    if hasattr(response, "parts"):
        parts = response.parts
    elif hasattr(response, "candidates") and response.candidates:
        candidate = response.candidates[0]
        if hasattr(candidate, "content") and hasattr(candidate.content, "parts"):
            parts = candidate.content.parts

    for part in parts:
        text = getattr(part, "text", "").strip()
        for phrase in allowed_outputs:
            if text == phrase:
                return phrase
    # Fallback: check if any allowed phrase is in any part
    for part in parts:
        text = getattr(part, "text", "").strip()
        for phrase in allowed_outputs:
            if phrase in text:
                return phrase
    return "OTHER/NOT_ENOUGH_INFO"

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
    timeout_seconds = int(os.getenv("GEMINI_TIMEOUT_SECONDS", env.get("GEMINI_TIMEOUT_SECONDS", 45)) or 45)
    
    # Define the grounding tool for Google Search
    # grounding_tool = genai.types.Tool(
    #     google_search=genai.types.GoogleSearch(),
    #     google_search_retrieval=genai.types.GoogleSearchRetrieval(),
    #     url_context=genai.types.UrlContext()
    # )
    google_search = genai.types.Tool(google_search=genai.types.GoogleSearch())
    # google_search_retrieval = genai.types.Tool(google_search_retrieval=genai.types.GoogleSearchRetrieval())
    url_context = genai.types.Tool(url_context=genai.types.UrlContext())

    tools = [google_search, url_context]
    
    # Define fallback models to try when encountering 503 errors
    available_models = [
        "gemini-flash-latest",      # Primary model
        "gemini-2.5-flash",          # Fallback 1
        "gemini-2.5-lite",            # Fallback 2
        "gemini-2.0-flash"                 # Fallback 3
    ]


    for i, split in enumerate(splits):
        symbol = split.get('symbol')
        company = split.get('company', '')
        date = split.get('effective_date', '')
        ratio = split.get('ratio', '')
        article_link = split.get('article_link', [])

        if not symbol:
            continue

        allowed_outputs = [
            "ROUND_UP",
            "CASH_IN_LIEU",
            "ROUND_DOWN",
            "THRESHOLD_ROUND_UP",
            "OTHER/NOT_ENOUGH_INFO"
        ]
        config = genai.types.GenerateContentConfig(
            tools=tools,
            temperature=0.2,
            top_k=40,
            top_p=0.95,
        )

        max_attempts = 3
        attempt = 0
        result = "OTHER/NOT_ENOUGH_INFO"
        last_error = None
        current_model_index = 0  # Start with the primary model
        
        while attempt < max_attempts and result == "OTHER/NOT_ENOUGH_INFO":
            try:
                # Select model - cycle through available models on 503 errors
                current_model = available_models[current_model_index % len(available_models)]
                
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
                "THRESHOLD_ROUND_UP" - if they'll certainly round up only if fractional shares exceed a certain threshold
                "OTHER/NOT_ENOUGH_INFO" - for other methods or uncertainty
                
                Do not include any explanations, just respond with one of these exact phrases.
                """

                logging.info(f"Querying Gemini API for {symbol} with model {current_model}, attempt {attempt+1} (timeout {timeout_seconds}s)")
                response = _call_gemini_with_timeout(
                    client,
                    model=current_model,
                    contents=prompt,
                    config=config,
                    timeout_seconds=timeout_seconds,
                )
                print('response: ', response)
                # logging.info(f"Gemini API response for {symbol}: {response}")
                result = extract_allowed_output(response, allowed_outputs)
                if result == "":
                    logging.warning(f"No response text for {symbol} defaulting to NO_INFO, api response: {getattr(response, 'body', None)}")
                    result = "NO_INFO"
                logging.info(f"Grounded Gemini API response for {symbol}: {result}")
                print(f"Grounded Gemini API response for {symbol}: {result}")
            except _GeminiTimeout as e:
                last_error = e
                logging.error(f"Timeout querying Gemini API for {symbol} (attempt {attempt+1}): {e}")
            except Exception as e:
                last_error = e
                error_str = str(e)
                logging.error(f"Error querying Gemini API for {symbol} (attempt {attempt+1}): {e}")
                logging.error(f"Exception details: {error_str}")
                
                # Check if this is a 503 error (model overloaded)
                if "503" in error_str:
                    # Switch to next model for the retry
                    current_model_index += 1
                    next_model = available_models[current_model_index % len(available_models)]
                    logging.warning(f"Model {current_model} is overloaded (503), switching to {next_model} for next attempt")
            
            attempt += 1
            if result == "OTHER/NOT_ENOUGH_INFO" and attempt < max_attempts:
                time.sleep(2)
            else:
                time.sleep(1)

        # Update the split information based on response (exact matches; check THRESHOLD before ROUND_UP)
        if result == "THRESHOLD_ROUND_UP":
            splits[i]['fractional'] = "Rounded up if fractional shares exceed a certain threshold"
        elif result == "ROUND_UP":
            splits[i]['fractional'] = "Rounded up to nearest whole share"
        elif result == "CASH_IN_LIEU":
            splits[i]['fractional'] = "Cash payment for fractional shares"
        elif result == "ROUND_DOWN":
            splits[i]['fractional'] = "Rounded down to nearest whole share"
        else:
            splits[i]['fractional'] = "Not enough information"
            if last_error:
                logging.error(f"Final error for {symbol} after {max_attempts} attempts: {last_error}")
            

            
            # Query Gemini API with grounding
            logging.info(f"Querying Gemini API for {symbol} with grounding")
            try:
                response = _call_gemini_with_timeout(
                    client,
                    model="gemini-flash-latest",  # or gemini-1.5-pro if you prefer
                    contents=prompt,
                    config=config,
                    timeout_seconds=timeout_seconds,
                )
            except _GeminiTimeout as e:
                last_error = e
                logging.error(f"Timeout on final Gemini retry for {symbol}: {e}")
                response = None
            
            print('response: ', response)
            if response is not None:
                result = extract_allowed_output(response, allowed_outputs)
            if result == "":
                logging.warning(f"No response text for {symbol} defaulting to NO_INFO, api response: {getattr(response, 'body', None)}")
                result = "OTHER/NOT_ENOUGH_INFO"
            logging.info(f"Grounded Gemini API response for {symbol}: {result}")
            print(f"Grounded Gemini API response for {symbol}: {result}")

            # # Log each URI used for the response, if available
            # try:
            #     print(f"response: {response}")
            #     print()
            #     print(f"\nGemini grounding metadata for {symbol}: {response.candidates}")
            #     print()
            #     print(f"Gemini grounding metadata for {symbol}: {response.candidates[0]}")
            #     logging.info(f"Gemini grounding metadata for {symbol}: {response.candidates[0].grounding_metadata}")
            #     supports = response.candidates[0].grounding_metadata.grounding_supports
            #     logging.info(f"Gemini grounding supports for {symbol}: {supports}")
            #     chunks = response.candidates[0].grounding_metadata.grounding_chunks
            #     logging.info(f"Gemini grounding chunks for {symbol}: {chunks}")
            #     if chunks:
            #         uris = set()
            #         for chunk in chunks:
            #             # Defensive: chunk.web may not exist
            #             web = getattr(chunk, 'web', None)
            #             if web and hasattr(web, 'uri'):
            #                 uris.add(web.uri)
            #         for uri in uris:
            #             logging.info(f"Gemini grounding support URI for {symbol}: {uri}")
            # except Exception as e:
            #     logging.warning(f"Could not extract Gemini grounding URIs for {symbol}: {e}")
            
            # Update the split information based on response (exact matches; check THRESHOLD before ROUND_UP)
            if result == "THRESHOLD_ROUND_UP":
                splits[i]['fractional'] = "Rounded up if fractional shares exceed a certain threshold"
            elif result == "ROUND_UP":
                splits[i]['fractional'] = "Rounded up to nearest whole share"
            elif result == "CASH_IN_LIEU":
                splits[i]['fractional'] = "Cash payment for fractional shares"
            elif result == "ROUND_DOWN":
                splits[i]['fractional'] = "Rounded down to nearest whole share"
            else:
                splits[i]['fractional'] = "Not enough information"

                # Don't overwhelm the API, add a small delay between requests
                time.sleep(1)
        
    # Keep all splits (including cash in lieu / rounded down) so they can be persisted to the DB
    # Sort for stability
    splits.sort(key=sort_key)
    return splits



def get_split_details(splits):
    """
    For each split, use Gemini API with grounding to get details:
    - ratio
    - effective_date
    - fractional (how fractional shares are handled)
    - is_reverse
    - article_link (used for grounding)
    Returns a list of dicts for each stock (excluding symbol and article_link in output schema).
    """
    client = configure_gemini()
    if not client:
        logging.warning("Gemini API not configured, skipping split details check")
        return []
    timeout_seconds = int(os.getenv("GEMINI_TIMEOUT_SECONDS", env.get("GEMINI_TIMEOUT_SECONDS", 45)) or 45)

    google_search = genai.types.Tool(google_search=genai.types.GoogleSearch())
    url_context = genai.types.Tool(url_context=genai.types.UrlContext())
    tools = [google_search, url_context]
    
    # Define fallback models to try when encountering 503 errors
    available_models = [
        "gemini-flash-latest",      # Primary model
        "gemini-2.5-flash",          # Fallback 1
        "gemini-2.5-lite",            # Fallback 2
        "gemini-2.0-flash"                 # Fallback 3
    ]

    results = []
    for split in splits:
        symbol = split.get('symbol')
        article_link = split.get('article_link', [])
        if not symbol:
            continue

        config = genai.types.GenerateContentConfig(
            tools=tools,
            temperature=0.2,
            top_k=40,
            top_p=0.95,
        )

        max_attempts = 3
        attempt = 0
        current_model_index = 0  # Start with the primary model
        extracted = {
            'symbol': symbol,
            'ratio': None,
            'effective_date': None,
            'fractional': None,
            'is_reverse': None,
            'article_link': article_link
        }
        last_error = None
        import re, json
        while attempt < max_attempts:
            try:
                # Select model - cycle through available models on 503 errors
                current_model = available_models[current_model_index % len(available_models)]
                
                article_info = ""
                if article_link and len(article_link) > 0:
                    if len(article_link) == 1:
                        article_info = f"\nAdditionally, please check this specific article about the split: {article_link[0]}"
                    else:
                        article_links_text = "\n".join([f"- {link}" for link in article_link])
                        article_info = f"\nAdditionally, please check these specific articles about the split:\n{article_links_text}"

                prompt = f"""
                Search for factual information about the stock split for {symbol}.
                Please extract and return the following information if available:
                - The split ratio (e.g. "10->1", "80->1", "1->5")
                - The effective date of the split (format YYYY-MM-DD)
                - Whether this is a reverse split (True/False)
                - How fractional shares will be handled
                Use the latest SEC filings, press releases, investor relations, and the following articles for grounding:{article_info}

                    For the split ratio, reply ONLY with the ratio in the format "X->Y" (e.g., "5->1"). Do not include any extra words, ranges, or explanations. If the ratio cannot be determined, reply with "unknown".

                    For fractional, respond with ONLY one of these exact phrases:
                    "ROUND_UP" - if they'll certainly round up to nearest whole share
                    "CASH_IN_LIEU" - if they'll certainly pay cash for fractional shares
                    "ROUND_DOWN" - if they'll certainly round down
                    "THRESHOLD_ROUND_UP" - if they'll certainly round up only if fractional shares exceed a certain threshold
                    "OTHER/NOT_ENOUGH_INFO" - for other methods or uncertainty

                    Respond in the following JSON format:
                    {{
                        "ratio": "<split ratio in X->Y format>",
                        "effective_date": "<effective date>",
                        "is_reverse": <true/false>,
                        "fractional": "<one of the above phrases>"
                    }}
                    If any information is not found, use "unknown" or false for is_reverse.
                    """

                logging.info(f"Querying Gemini API for {symbol} split details with model {current_model}, attempt {attempt+1}")
                response = _call_gemini_with_timeout(
                    client,
                    model=current_model,
                    contents=prompt,
                    config=config,
                    timeout_seconds=timeout_seconds,
                )
                # Extract text from Gemini response
                response_text = None
                if hasattr(response, "parts") and response.parts:
                    response_text = getattr(response.parts[0], "text", None)
                elif hasattr(response, "candidates") and response.candidates:
                    candidate = response.candidates[0]
                    if hasattr(candidate, "content") and hasattr(candidate.content, "parts") and candidate.content.parts:
                        response_text = getattr(candidate.content.parts[0], "text", None)
                if not response_text:
                    response_text = str(response)

                # Remove markdown code block formatting
                code_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
                if code_match:
                    json_str = code_match.group(1)
                else:
                    # Fallback: extract first {...} block
                    brace_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                    json_str = brace_match.group(0) if brace_match else None

                if json_str:
                    try:
                        data = json.loads(json_str)
                        logging.info(f"Gemini API response for {symbol}: {data}")
                        # Ratio formatting: convert e.g. "80-for-1" or "1-for-5" to "80->1" or "1->5"
                        raw_ratio = data.get('ratio', None)
                        is_reverse = data.get('is_reverse', None)
                        if raw_ratio and raw_ratio != "unknown":
                            ratio_match = re.match(r"(\d+)[- ]*for[- ]*(\d+)", raw_ratio)
                            if ratio_match:
                                left = ratio_match.group(1)
                                right = ratio_match.group(2)
                                if is_reverse is True or (isinstance(is_reverse, str) and is_reverse.lower() == 'true'):
                                    # Reverse split: always X->1
                                    extracted['ratio'] = f"{max(int(left), int(right))}->{min(int(left), int(right))}"
                                else:
                                    # Forward split: always 1->Y
                                    extracted['ratio'] = f"{min(int(left), int(right))}->{max(int(left), int(right))}"
                            else:
                                extracted['ratio'] = raw_ratio.replace("for", "->").replace("-", "->")
                        if not extracted['ratio'] and raw_ratio:
                            extracted['ratio'] = raw_ratio

                        # Date formatting: try to parse and format as YYYY-MM-DD
                        raw_date = data.get('effective_date', None)
                        if raw_date and raw_date != "unknown":
                            date_match = re.search(r"(\d{4})[-/](\d{2})[-/](\d{2})", raw_date)
                            if date_match:
                                extracted['effective_date'] = f"{date_match.group(1)}-{date_match.group(2)}-{date_match.group(3)}"
                            else:
                                extracted['effective_date'] = raw_date
                        if not extracted['effective_date'] and raw_date:
                            extracted['effective_date'] = raw_date

                        # is_reverse
                        is_reverse = data.get('is_reverse', None)
                        if isinstance(is_reverse, bool):
                            extracted['is_reverse'] = is_reverse
                        elif isinstance(is_reverse, str):
                            extracted['is_reverse'] = is_reverse.lower() == 'true'

                        # Fractional handling (same logic as check_roundup, exact matches)
                        result = data.get('fractional', None)
                        if result:
                            if result == "THRESHOLD_ROUND_UP":
                                extracted['fractional'] = "Rounded up if fractional shares exceed a certain threshold"
                            elif result == "ROUND_UP":
                                extracted['fractional'] = "Rounded up to nearest whole share"
                            elif result == "CASH_IN_LIEU":
                                extracted['fractional'] = "Cash payment for fractional shares"
                            elif result == "ROUND_DOWN":
                                extracted['fractional'] = "Rounded down to nearest whole share"
                            else:
                                extracted['fractional'] = "Not enough information"
                        if not extracted['fractional'] and result:
                            extracted['fractional'] = result
                    except Exception as e:
                        last_error = e
                        logging.info(f"Error parsing JSON response for {symbol}: {e}")
            except _GeminiTimeout as e:
                last_error = e
                logging.info(f"Timeout occurred for {symbol}: {e}")
            except Exception as e:
                last_error = e
                error_str = str(e)
                logging.info(f"Error occurred for {symbol}: {e}")
                
                # Check if this is a 503 error (model overloaded)
                if "503" in error_str:
                    # Switch to next model for the retry
                    current_model_index += 1
                    next_model = available_models[current_model_index % len(available_models)]
                    logging.warning(f"Model {current_model} is overloaded (503), switching to {next_model} for next attempt")
            attempt += 1
            # If any field is still missing, try again and merge
            if attempt < max_attempts and (not extracted['ratio'] or not extracted['effective_date'] or not extracted['fractional'] or extracted['ratio'] == 'unknown' or extracted['effective_date'] == 'unknown' or extracted['fractional'] == 'unknown'):
                time.sleep(2)
            else:
                break

        # Fill any missing fields with 'unknown' for output
        for k in ['ratio', 'effective_date', 'fractional', 'is_reverse']:
            if extracted[k] is None:
                extracted[k] = 'unknown'
        results.append(extracted)

    # Keep decided fractional outcomes; only drop obvious non-reverse splits
    filtered = []
    for split in results:
        if split['is_reverse'] is False:
            logging.info(f"Skipping non-reverse split: {split['symbol']} on {split['effective_date']}")
            continue
        filtered.append(split)
    return filtered


def get_threshold_minimum_shares(symbol, ratio, grounding_link=None):
    """
    Use Gemini API to extract the minimum fractional share threshold for rounding up, given a stock symbol, split ratio, and optional grounding link.
    Returns (minimum_shares_required, threshold_info) or (None, None) if not found.
    Example: If threshold is 1/2 and ratio is 10, returns 5.
    """
    client = configure_gemini()
    if not client:
        logging.warning("Gemini API not configured, skipping threshold minimum shares check")
        return None, None
    timeout_seconds = int(os.getenv("GEMINI_TIMEOUT_SECONDS", env.get("GEMINI_TIMEOUT_SECONDS", 45)) or 45)

    # Define fallback models to try when encountering 503 errors
    available_models = [
        "gemini-flash-latest",      # Primary model
        "gemini-2.5-flash",          # Fallback 1
        "gemini-2.5-lite",            # Fallback 2
        "gemini-2.0-flash"                 # Fallback 3
    ]

    article_info = ""
    if grounding_link:
        article_info = f"\nAdditionally, please check this specific article or SEC filing: {grounding_link}"

    prompt = f"""
    Given the following context about a reverse stock split for {symbol} with a split ratio of {ratio}, extract the minimum fractional share threshold required for rounding up to a whole share. If the threshold is described as a fraction (e.g., 1/2), return it as a decimal. If the split ratio is X-for-1, compute the minimum shares required for rounding up as X * threshold. If the information is not found, reply with 'unknown'.

    Example context:
    "No fractional Common Shares will be issued in connection with the Consolidation. Any fractional Common Shares remaining after the Consolidation that are less than ½ of a Common Share will be cancelled, and each fractional Common Share that is at least ½ of a Common Share will be rounded up to one whole Common Share."

    Respond in the following JSON format:
    {{
        "threshold_fraction": <decimal>,
        "minimum_shares_required": <decimal>,
        "explanation": <short explanation or quote from context>
    }}
    {article_info}
    """

    config = genai.types.GenerateContentConfig(
        tools=[genai.types.Tool(google_search=genai.types.GoogleSearch()), genai.types.Tool(url_context=genai.types.UrlContext())],
        temperature=0.2,
        top_k=40,
        top_p=0.95,
    )

    import re, json
    max_attempts = 3
    attempt = 0
    current_model_index = 0  # Start with the primary model
    min_shares = None
    explanation = None
    while attempt < max_attempts and (min_shares is None or explanation is None):
        try:
            # Select model - cycle through available models on 503 errors
            current_model = available_models[current_model_index % len(available_models)]
            
            logging.info(f"Querying Gemini API for {symbol} threshold with model {current_model}, attempt {attempt+1}")
            response = _call_gemini_with_timeout(
                client,
                model=current_model,
                contents=prompt,
                config=config,
                timeout_seconds=timeout_seconds,
            )
            response_text = None
            if hasattr(response, "parts") and response.parts:
                response_text = getattr(response.parts[0], "text", None)
            elif hasattr(response, "candidates") and response.candidates:
                candidate = response.candidates[0]
                if hasattr(candidate, "content") and hasattr(candidate.content, "parts") and candidate.content.parts:
                    response_text = getattr(candidate.content.parts[0], "text", None)
            if not response_text:
                response_text = str(response)

            code_match = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response_text, re.DOTALL)
            if code_match:
                json_str = code_match.group(1)
            else:
                brace_match = re.search(r"\{.*\}", response_text, re.DOTALL)
                json_str = brace_match.group(0) if brace_match else None
            if json_str:
                try:
                    data = json.loads(json_str)
                    threshold = data.get("threshold_fraction")
                    if min_shares is None:
                        min_shares = data.get("minimum_shares_required")
                    if explanation is None:
                        explanation = data.get("explanation")
                    if threshold is not None and min_shares is not None:
                        return min_shares, explanation
                except Exception as e:
                    logging.warning(f"Error parsing Gemini threshold response: {e}")
            logging.info(f"Gemini threshold response for {symbol}: {response_text}")
        except _GeminiTimeout as e:
            logging.error(f"Timeout querying Gemini for threshold minimum shares for {symbol}: {e}")
        except Exception as e:
            error_str = str(e)
            logging.error(f"Error querying Gemini for threshold minimum shares for {symbol}: {e}")
            
            # Check if this is a 503 error (model overloaded)
            if "503" in error_str:
                # Switch to next model for the retry
                current_model_index += 1
                next_model = available_models[current_model_index % len(available_models)]
                logging.warning(f"Model {current_model} is overloaded (503), switching to {next_model} for next attempt")
        
        attempt += 1
        if min_shares is None or explanation is None:
            import time
            time.sleep(2)
    return min_shares, explanation