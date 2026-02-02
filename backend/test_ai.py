"""Test AI response directly"""
import asyncio

async def test():
    from app.ai.ollama_client import get_ollama_client
    
    ollama = get_ollama_client()
    
    prompt = """אתה מומחה בהתאמת כלים פיננסיים לאתרים.

קיבלת תוכן מאתר עסקי ורשימת מחשבונים פיננסיים.
תפקידך לבחור את המחשבון המתאים ביותר לאתר הזה.

### תוכן מהאתר:
=== תפריט ראשי ===
הלוואות, משכנתאות, ביטוח, פנסיה

=== כותרת ===
הלוואות לעסקים - פתרונות מימון

=== תוכן העמוד ===
אנחנו מציעים הלוואות לעסקים קטנים ובינוניים עד 500,000 שקל

### סוג העסק: lead_site

### רשימת מחשבונים זמינים:
[
  {"id": 1, "name": "מחשבון הלוואה לעסק", "description": "חישוב החזר הלוואה לעסקים"},
  {"id": 2, "name": "מחשבון משכנתא", "description": "חישוב החזר משכנתא"},
  {"id": 3, "name": "מחשבון פנסיה", "description": "חישוב חיסכון פנסיוני"}
]

### הוראות:
1. נתח את תחום העיסוק של האתר
2. זהה את קהל היעד
3. בחר את המחשבון הרלוונטי ביותר
4. אם אין מחשבון מתאים, בחר את הקרוב ביותר

השב בפורמט JSON בלבד:
{
  "calc_id": מספר_המחשבון,
  "calc_name": "שם המחשבון",
  "match_score": 0.0-1.0,
  "reasoning": "הסבר קצר למה זה מתאים (2-3 משפטים)"
}"""

    print("Sending to AI...")
    response = await ollama.generate(
        system_prompt="אתה מומחה בהתאמת כלים פיננסיים לאתרים. השב תמיד ב-JSON תקין בעברית.",
        user_prompt=prompt,
        model="hf.co/dicta-il/DictaLM-3.0-24B-Thinking-GGUF:Q4_K_M",
        temperature=0.3,
        max_tokens=400
    )
    
    print("=" * 60)
    print("RAW RESPONSE:")
    print("=" * 60)
    print(response)
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test())
