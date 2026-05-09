import httpx, time

prompt = (
    'You are an educational assistant for Learnova. Analyze this document and return a single JSON object.\n\n'
    'Document content:\nThis is a test document about machine learning. '
    'Machine learning is a subset of artificial intelligence that enables computers to learn from data '
    'without being explicitly programmed. The field includes supervised learning, unsupervised learning, '
    'and reinforcement learning. Neural networks are a key component. Deep learning uses many layers.\n\n'
    'Return ONLY valid JSON with this exact structure:\n'
    '{"summary":{"body":["paragraph 1","paragraph 2"],"takeaways":["key point 1","key point 2","key point 3"]},'
    '"quiz":[{"q":"q1","opts":["A","B","C","D"],"correct":0,"explanation":"e1"},'
    '{"q":"q2","opts":["A","B","C","D"],"correct":1,"explanation":"e2"},'
    '{"q":"q3","opts":["A","B","C","D"],"correct":2,"explanation":"e3"},'
    '{"q":"q4","opts":["A","B","C","D"],"correct":3,"explanation":"e4"},'
    '{"q":"q5","opts":["A","B","C","D"],"correct":0,"explanation":"e5"},'
    '{"q":"q6","opts":["A","B","C","D"],"correct":1,"explanation":"e6"},'
    '{"q":"q7","opts":["A","B","C","D"],"correct":2,"explanation":"e7"},'
    '{"q":"q8","opts":["A","B","C","D"],"correct":3,"explanation":"e8"}],'
    '"analysis":{"strengths":["s1","s2","s3"],"weaknesses":["w1","w2"],'
    '"recommendations":["r1","r2","r3"],"studyNext":["t1","t2","t3"]},'
    '"modules":[{"title":"t1","type":"youtube","query":"machine learning","description":"d1"},'
    '{"title":"t2","type":"google","query":"machine learning tutorial","description":"d2"},'
    '{"title":"t3","type":"youtube","query":"ML basics","description":"d3"},'
    '{"title":"t4","type":"google","query":"AI fundamentals","description":"d4"},'
    '{"title":"t5","type":"youtube","query":"deep learning","description":"d5"}]}'
)

print("Sending prompt to Ollama... (timeout=300s)")
t0 = time.time()
try:
    r = httpx.post(
        "http://host.docker.internal:11434/api/generate",
        json={"model": "llama3:latest", "prompt": prompt, "stream": False,
              "format": "json", "options": {"temperature": 0.3}},
        timeout=300
    )
    elapsed = round(time.time() - t0, 1)
    resp = r.json().get("response", "")
    print(f"OK in {elapsed}s, response_len={len(resp)}")
    print("First 200 chars:", resp[:200])
except Exception as e:
    elapsed = round(time.time() - t0, 1)
    print(f"FAILED in {elapsed}s: {repr(e)}")
