import os
import json
import boto3
import urllib.request
import urllib.error

# --------- env ---------
INFERENCE_PROFILE_ARN = os.environ.get("INFERENCE_PROFILE_ARN", "").strip()
SEARCH_PROVIDER       = os.environ.get("SEARCH_PROVIDER", "tavily").strip().lower()
TAVILY_API_KEY        = os.environ.get("TAVILY_API_KEY", "").strip()
NEWS_API_KEY          = os.environ.get("NEWS_API_KEY", "").strip()

# --------- CORS helpers (fixes "Failed to fetch") ---------
ALLOWED_ORIGINS = {
    # Development - ADDED FOR LOCAL TESTING
    "http://localhost:5173",
    "http://localhost:3000",
    "http://127.0.0.1:5173",
    # Production Vercel domains
    "https://smart-study-buddy-tnef.vercel.app",
    "https://smart-study-buddy-lemon.vercel.app",
    "https://smart-study-buddy-tan.vercel.app",
}

def _pick_allow_origin(event) -> str:
    """Return the Origin we will allow for this request."""
    hdrs = event.get("headers") or {}
    origin = hdrs.get("origin") or hdrs.get("Origin") or ""
    
    # Allow localhost for development
    if origin.startswith("http://localhost") or origin.startswith("http://127.0.0.1"):
        return origin
    
    if origin in ALLOWED_ORIGINS:
        return origin
    
    # Allow preview subdomains like https://<repo>-git-<branch>-<user>.vercel.app
    if origin.startswith("https://") and origin.endswith(".vercel.app"):
        return origin
    
    # Safe default to your primary prod site
    return "https://smart-study-buddy-tnef.vercel.app"

def _cors_headers(event):
    allow_origin = _pick_allow_origin(event)
    return {
        "Access-Control-Allow-Origin": allow_origin,
        "Vary": "Origin",
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Methods": "OPTIONS,POST,GET",
    }

# --------- small HTTP helper ---------
def _http_json(url: str, payload: dict, headers: dict) -> dict:
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=20) as resp:
        return json.loads(resp.read().decode("utf-8"))

# --------- Language Detection ---------
def detect_language(text: str) -> str:
    """
    Simple language detection based on common words.
    Returns 'es' for Spanish, 'en' for English
    """
    # Common Spanish words/patterns
    spanish_indicators = [
        'qué', 'cómo', 'cuál', 'cuándo', 'dónde', 'quién', 'por qué',
        'el', 'la', 'los', 'las', 'un', 'una', 'es', 'son', 'está',
        'de', 'del', 'para', 'con', 'sin', 'sobre', 'entre',
        'yo', 'tú', 'él', 'ella', 'nosotros', 'ustedes',
        'explica', 'explicar', 'dime', 'cuéntame', 'ayuda'
    ]
    
    text_lower = text.lower()
    
    # Check for Spanish indicators
    spanish_count = sum(1 for word in spanish_indicators if word in text_lower)
    
    # If we find Spanish words, it's Spanish
    if spanish_count >= 1:
        print(f"🌍 Language detected: Spanish (found {spanish_count} indicators)")
        return 'es'
    
    print(f"🌍 Language detected: English (default)")
    return 'en'

# --------- Web search (Tavily) with language support ---------
def tavily_search(query: str, language: str = 'en', max_results: int = 6) -> dict:
    if not TAVILY_API_KEY:
        print("⚠️ TAVILY_API_KEY not set - skipping web search")
        return {"results": [], "answer": None}
    
    url = "https://api.tavily.com/search"
    body = {
        "api_key": TAVILY_API_KEY,
        "query": query,
        "search_depth": "advanced",
        "max_results": max_results,
        "include_answer": True,
        "include_images": False,
        "topic": "general",
    }
    
    # Add language-specific domains for better results
    if language == 'es':
        # Prioritize Spanish-language sources
        body["include_domains"] = ["es.wikipedia.org", ".es", ".mx", ".ar", ".co", ".cl"]
    
    try:
        data = _http_json(url, body, {"Content-Type": "application/json"})
        results = []
        for r in data.get("results", []):
            results.append({
                "type": "web",
                "title": r.get("title") or r.get("url") or "Source",
                "url": r.get("url", ""),
                "snippet": (r.get("content") or "")[:400],
            })
        print(f"✅ Tavily search ({language}): found {len(results)} results")
        return {"results": results, "answer": data.get("answer")}
    except Exception as e:
        print(f"❌ Tavily search error: {str(e)}")
        return {"results": [], "answer": None}

# --------- News search (NewsAPI) ---------
def news_search(query: str, max_results: int = 3) -> list:
    if not NEWS_API_KEY:
        print("⚠️ NEWS_API_KEY not set - skipping news search")
        return []
    
    try:
        # Build URL with parameters
        params = {
            "q": query,
            "apiKey": NEWS_API_KEY,
            "sortBy": "publishedAt",  # Most recent first
            "pageSize": max_results,
            "language": "en"
        }
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        url = f"https://newsapi.org/v2/everything?{query_string}"
        
        req = urllib.request.Request(url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        
        results = []
        for article in data.get("articles", [])[:max_results]:
            results.append({
                "type": "news",
                "title": article.get("title", "Article"),
                "url": article.get("url", ""),
                "snippet": article.get("description", "")[:300],
                "source": article.get("source", {}).get("name", "Unknown"),
                "published": article.get("publishedAt", "")
            })
        
        print(f"✅ News search: found {len(results)} articles")
        return results
        
    except Exception as e:
        print(f"❌ News search error: {str(e)}")
        return []

# --------- Bedrock response extractor ---------
def extract_text_from_bedrock(payload: dict) -> str:
    # Newer Anthropic
    if isinstance(payload, dict) and "output" in payload:
        out = payload.get("output", {})
        if isinstance(out, dict):
            for part in out.get("content", []):
                if isinstance(part, dict) and part.get("type") == "text":
                    txt = part.get("text")
                    if isinstance(txt, str):
                        return txt

    # Content array
    if isinstance(payload, dict) and isinstance(payload.get("content"), list):
        for part in payload["content"]:
            if isinstance(part, dict) and part.get("type") == "text":
                txt = part.get("text")
                if isinstance(txt, str):
                    return txt

    # Older message format
    msg = payload.get("message")
    if isinstance(msg, dict):
        for part in msg.get("content", []):
            if isinstance(part, dict) and part.get("type") == "text":
                txt = part.get("text")
                if isinstance(txt, str):
                    return txt

    return json.dumps(payload)[:1200]

# --------- Prompt builder ---------
def build_prompt(user_prompt: str, web_hits: list) -> str:
    lines = []
    if web_hits:
        lines.append("=== CURRENT WEB SOURCES (Use this information to answer) ===")
        for i, s in enumerate(web_hits, start=1):
            lines.append(f"\n[{i}] {s.get('title','Source')}")
            lines.append(f"URL: {s.get('url','')}")
            snip = (s.get("snippet") or "").strip()
            if snip:
                lines.append(f"Content: {snip[:400]}")
        lines.append("\n=== END OF SOURCES ===\n")

    lines.append(
        "IMPORTANT INSTRUCTIONS:\n"
        "- You are a helpful AI tutor answering questions for students\n"
        "- The web sources above contain CURRENT, UP-TO-DATE information\n"
        "- For questions about recent events, news, or current information: USE THE WEB SOURCES PROVIDED\n"
        "- Trust the sources - they are from reliable websites and contain factual current information\n"
        "- Answer directly based on what the sources say\n"
        "- Cite sources using [1], [2], [3] etc.\n"
        "- If sources have dates/timelines, include them in your answer\n"
        "- Be clear, educational, and step-by-step\n"
        "- If the question is about current events or recent news, prioritize the web sources over general knowledge\n"
    )
    lines.append(f"\nStudent Question: {user_prompt}\n")
    lines.append("Your Answer:")
    return "\n".join(lines)

# --------- Main handler ---------
def lambda_handler(event, context):
    print(f"📥 Event received: {json.dumps(event)}")
    
    headers = _cors_headers(event)

    # Handle preflight OPTIONS request
    http_method = event.get("requestContext", {}).get("http", {}).get("method")
    request_method = event.get("httpMethod")  # For REST API
    method = http_method or request_method
    
    if method == "OPTIONS":
        print("✅ Handling OPTIONS preflight request")
        return {"statusCode": 200, "headers": headers, "body": ""}

    # Parse body
    try:
        body = event.get("body") or "{}"
        if isinstance(body, str):
            body = json.loads(body)
    except Exception as e:
        print(f"❌ Error parsing body: {str(e)}")
        body = {}

    user_prompt = (body.get("prompt") or "").strip() or "Explain recursion in simple steps."
    print(f"📝 User prompt: {user_prompt}")

    # Web retrieval - Get both web results AND news
    web_results = {"results": [], "answer": None}
    news_results = []
    
    if SEARCH_PROVIDER == "tavily":
        web_results = tavily_search(user_prompt, max_results=5)
    
    # Also search news for current events
    news_results = news_search(user_prompt, max_results=3)
    
    # Combine all sources
    all_sources = web_results.get("results", []) + news_results
    context_block = build_prompt(user_prompt, all_sources)

    # Bedrock call
    print("🤖 Calling AWS Bedrock...")
    client = boto3.client("bedrock-runtime", region_name="us-east-1")

    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": 1500,
        "temperature": 0.7,
        "messages": [
            {
                "role": "user",
                "content": [{"type": "text", "text": context_block}],
            }
        ],
    }

    try:
        if INFERENCE_PROFILE_ARN:
            print(f"Using inference profile: {INFERENCE_PROFILE_ARN}")
            resp = client.invoke_model(
                modelId=INFERENCE_PROFILE_ARN,
                body=json.dumps(payload).encode("utf-8"),
                accept="application/json",
                contentType="application/json",
            )
        else:
            model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
            print(f"Using model: {model_id}")
            resp = client.invoke_model(
                modelId=model_id,
                body=json.dumps(payload).encode("utf-8"),
                accept="application/json",
                contentType="application/json",
            )

        model_json = json.loads(resp["body"].read().decode("utf-8"))
        answer_text = extract_text_from_bedrock(model_json).strip()
        
        if not answer_text or answer_text == "{}":
            answer_text = web_results.get("answer") or \
                "I couldn't find enough reliable information to answer that."
        
        print(f"✅ Generated answer: {len(answer_text)} characters")
        
    except Exception as e:
        print(f"❌ Bedrock error: {str(e)}")
        return {
            "statusCode": 500,
            "headers": {**headers, "Content-Type": "application/json"},
            "body": json.dumps({"error": f"Bedrock error: {str(e)}"}),
        }

    response_body = {
        "answer": answer_text,
        "sources": all_sources,  # Include both web and news sources
        "trace": {"kb_used": False, "web_used": bool(all_sources)},
    }

    print("✅ Returning successful response")
    return {
        "statusCode": 200,
        "headers": {**headers, "Content-Type": "application/json"},
        "body": json.dumps(response_body),
    }