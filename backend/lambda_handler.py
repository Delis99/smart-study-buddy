import os
import json
import boto3
import urllib.request
import urllib.error
from datetime import datetime

# ========== CONFIGURATION ==========
INFERENCE_PROFILE_ARN = os.environ.get("INFERENCE_PROFILE_ARN", "").strip()
TAVILY_API_KEY = os.environ.get("TAVILY_API_KEY", "").strip()
NEWS_API_KEY = os.environ.get("NEWS_API_KEY", "").strip()

# ========== CORS Configuration ==========
def get_cors_headers(event):
    """Return proper CORS headers for the request"""
    headers = event.get("headers") or {}
    origin = headers.get("origin") or headers.get("Origin") or "*"
    
    # Allow all origins during development, restrict in production
    allowed_origins = [
        "http://localhost:5173",
        "http://localhost:3000",
        "https://smart-study-buddy-tnef.vercel.app",
        "https://smart-study-buddy-lemon.vercel.app",
    ]
    
    # If origin is in allowed list or ends with .vercel.app, allow it
    if origin in allowed_origins or origin.endswith(".vercel.app"):
        cors_origin = origin
    else:
        cors_origin = "*"  # Fallback for development
    
    return {
        "Access-Control-Allow-Origin": cors_origin,
        "Access-Control-Allow-Headers": "Content-Type, Authorization",
        "Access-Control-Allow-Methods": "OPTIONS, POST, GET",
        "Access-Control-Allow-Credentials": "true"
    }

# ========== TAVILY SEARCH ==========
def tavily_search(query, max_results=6):
    """Search using Tavily API for educational content"""
    if not TAVILY_API_KEY:
        print("⚠️ TAVILY_API_KEY not configured")
        return {"results": [], "answer": None}
    
    try:
        url = "https://api.tavily.com/search"
        payload = {
            "api_key": TAVILY_API_KEY,
            "query": query,
            "search_depth": "advanced",
            "max_results": max_results,
            "include_answer": True,
            "include_images": False,
            "topic": "general",
        }
        
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )
        
        with urllib.request.urlopen(req, timeout=15) as response:
            data = json.loads(response.read().decode("utf-8"))
            
        results = []
        for r in data.get("results", []):
            results.append({
                "title": r.get("title", "Source"),
                "url": r.get("url", ""),
                "snippet": (r.get("content") or "")[:400],
                "score": r.get("score", 0)
            })
        
        return {
            "results": results[:max_results],
            "answer": data.get("answer")
        }
        
    except Exception as e:
        print(f"❌ Tavily search error: {str(e)}")
        return {"results": [], "answer": None}

# ========== NEWS API SEARCH ==========
def news_search(query, max_results=3):
    """Search recent news using NewsAPI"""
    if not NEWS_API_KEY:
        print("⚠️ NEWS_API_KEY not configured")
        return []
    
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            "q": query,
            "apiKey": NEWS_API_KEY,
            "sortBy": "relevancy",
            "pageSize": max_results,
            "language": "en"
        }
        
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        full_url = f"{url}?{query_string}"
        
        req = urllib.request.Request(full_url)
        with urllib.request.urlopen(req, timeout=10) as response:
            data = json.loads(response.read().decode("utf-8"))
        
        articles = []
        for article in data.get("articles", [])[:max_results]:
            articles.append({
                "title": article.get("title", "Article"),
                "url": article.get("url", ""),
                "snippet": article.get("description", "")[:300],
                "source": article.get("source", {}).get("name", "Unknown")
            })
        
        return articles
        
    except Exception as e:
        print(f"❌ NewsAPI error: {str(e)}")
        return []

# ========== BUILD EDUCATIONAL PROMPT ==========
def build_educational_prompt(user_query, web_results, news_results):
    """Create a comprehensive educational prompt with context"""
    
    sections = []
    
    # Add web search context
    if web_results:
        sections.append("=== RELIABLE SOURCES ===")
        for i, source in enumerate(web_results, 1):
            sections.append(f"\n[{i}] {source['title']}")
            sections.append(f"URL: {source['url']}")
            if source.get('snippet'):
                sections.append(f"Content: {source['snippet']}")
    
    # Add news context if available
    if news_results:
        sections.append("\n=== RECENT NEWS & UPDATES ===")
        for i, article in enumerate(news_results, 1):
            sections.append(f"\n[N{i}] {article['title']}")
            sections.append(f"Source: {article['source']}")
            if article.get('snippet'):
                sections.append(f"Summary: {article['snippet']}")
    
    context = "\n".join(sections)
    
    prompt = f"""You are Smart Study Buddy, an expert AI tutor that helps students learn effectively.

{context}

STUDENT'S QUESTION: {user_query}

YOUR TASK:
1. Provide a clear, step-by-step explanation using the sources above
2. Break down complex concepts into simple, understandable parts
3. Use real-world examples and analogies where helpful
4. Cite sources inline using [1], [2], [N1], etc.
5. Structure your response with headers and bullet points for clarity
6. End with 2-3 follow-up questions to deepen understanding

Keep your tone friendly, educational, and encouraging. Make learning enjoyable!"""

    return prompt

# ========== EXTRACT BEDROCK RESPONSE ==========
def extract_bedrock_text(response_body):
    """Extract text from various Bedrock response formats"""
    try:
        # Anthropic Claude format
        if "content" in response_body:
            for item in response_body["content"]:
                if item.get("type") == "text":
                    return item.get("text", "")
        
        # Alternative format
        if "output" in response_body:
            output = response_body["output"]
            if isinstance(output, dict) and "content" in output:
                for item in output["content"]:
                    if item.get("type") == "text":
                        return item.get("text", "")
        
        # Fallback
        return str(response_body)[:1000]
        
    except Exception as e:
        print(f"❌ Error extracting text: {e}")
        return "Error processing response"

# ========== MAIN HANDLER ==========
def lambda_handler(event, context):
    """Main Lambda function handler"""
    
    print(f"📥 Received event: {json.dumps(event)}")
    
    # CORS headers
    cors_headers = get_cors_headers(event)
    
    # Handle preflight OPTIONS request
    if event.get("requestContext", {}).get("http", {}).get("method") == "OPTIONS":
        return {
            "statusCode": 200,
            "headers": cors_headers,
            "body": json.dumps({"message": "CORS preflight OK"})
        }
    
    # Parse request body
    try:
        body = event.get("body", "{}")
        if isinstance(body, str):
            body = json.loads(body)
    except json.JSONDecodeError as e:
        return {
            "statusCode": 400,
            "headers": {**cors_headers, "Content-Type": "application/json"},
            "body": json.dumps({"error": f"Invalid JSON: {str(e)}"})
        }
    
    # Get user query (support both 'prompt' and 'query' fields)
    user_query = body.get("prompt") or body.get("query") or ""
    user_query = user_query.strip()
    
    if not user_query:
        return {
            "statusCode": 400,
            "headers": {**cors_headers, "Content-Type": "application/json"},
            "body": json.dumps({"error": "Missing 'prompt' or 'query' in request body"})
        }
    
    print(f"📝 Processing query: {user_query}")
    
    # Step 1: Search for context
    web_results = tavily_search(user_query, max_results=5)
    news_results = news_search(user_query, max_results=2)
    
    sources = web_results.get("results", [])
    news_articles = news_results
    
    print(f"🔍 Found {len(sources)} web sources and {len(news_articles)} news articles")
    
    # Step 2: Build educational prompt
    educational_prompt = build_educational_prompt(user_query, sources, news_articles)
    
    # Step 3: Call Bedrock (Claude)
    try:
        bedrock_client = boto3.client("bedrock-runtime", region_name="us-east-1")
        
        payload = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": 2000,
            "temperature": 0.7,
            "messages": [
                {
                    "role": "user",
                    "content": [{"type": "text", "text": educational_prompt}]
                }
            ]
        }
        
        # Use inference profile if configured, otherwise use direct model
        if INFERENCE_PROFILE_ARN:
            model_id = INFERENCE_PROFILE_ARN
            print(f"🤖 Using inference profile: {model_id}")
        else:
            model_id = "us.anthropic.claude-3-5-sonnet-20241022-v2:0"
            print(f"🤖 Using model: {model_id}")
        
        response = bedrock_client.invoke_model(
            modelId=model_id,
            body=json.dumps(payload).encode("utf-8"),
            accept="application/json",
            contentType="application/json"
        )
        
        response_body = json.loads(response["body"].read().decode("utf-8"))
        answer_text = extract_bedrock_text(response_body).strip()
        
        if not answer_text:
            answer_text = "I apologize, but I couldn't generate a proper response. Please try rephrasing your question."
        
        print(f"✅ Generated answer: {len(answer_text)} characters")
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Bedrock error: {error_msg}")
        return {
            "statusCode": 500,
            "headers": {**cors_headers, "Content-Type": "application/json"},
            "body": json.dumps({
                "error": "AI service error",
                "details": error_msg,
                "message": "Failed to generate response. Please check Lambda logs."
            })
        }
    
    # Step 4: Prepare response
    all_sources = []
    
    # Add web sources
    for source in sources:
        all_sources.append({
            "type": "web",
            "title": source["title"],
            "url": source["url"],
            "snippet": source.get("snippet", "")
        })
    
    # Add news sources
    for article in news_articles:
        all_sources.append({
            "type": "news",
            "title": article["title"],
            "url": article["url"],
            "snippet": article.get("snippet", ""),
            "source": article.get("source", "")
        })
    
    response_data = {
        "answer": answer_text,
        "sources": all_sources,
        "metadata": {
            "web_sources_found": len(sources),
            "news_articles_found": len(news_articles),
            "timestamp": datetime.utcnow().isoformat(),
            "model_used": model_id
        }
    }
    
    print(f"📤 Returning response with {len(all_sources)} sources")
    
    return {
        "statusCode": 200,
        "headers": {**cors_headers, "Content-Type": "application/json"},
        "body": json.dumps(response_data)
    }