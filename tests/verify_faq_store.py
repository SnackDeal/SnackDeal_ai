"""Manual verification script for faq_store integration."""

import sys
sys.path.insert(0, '.')
from src.chatbot import faq_store

# Test FAQ loading
store = faq_store._get_store()
print(f"Loaded FAQs: {len(store.faqs)}")

# Test 1: 주문 취소
q1 = "주문 취소는 어떻게 하나요?"
faqs1 = faq_store.retrieve_relevant_faqs(q1, limit=5)
print(f"\n--- Test 1: {q1}")
print(f"Retrieved {len(faqs1)} FAQs:")
for f in faqs1:
    print(f"  [{f['type']}] {f['title']}")

# Test 2: 배송
q2 = "배송 얼마나 걸려요?"
faqs2 = faq_store.retrieve_relevant_faqs(q2, limit=5)
print(f"\n--- Test 2: {q2}")
print(f"Retrieved {len(faqs2)} FAQs:")
for f in faqs2:
    print(f"  [{f['type']}] {f['title']}")

# Test 3: 품절
q3 = "품절 상품 재입고 되나요?"
faqs3 = faq_store.retrieve_relevant_faqs(q3, limit=5)
print(f"\n--- Test 3: {q3}")
print(f"Retrieved {len(faqs3)} FAQs:")
for f in faqs3:
    print(f"  [{f['type']}] {f['title']}")

# Test 4: 이메일 인증
q4 = "이메일 인증 코드가 안 와요"
faqs4 = faq_store.retrieve_relevant_faqs(q4, limit=5)
print(f"\n--- Test 4: {q4}")
print(f"Retrieved {len(faqs4)} FAQs:")
for f in faqs4:
    print(f"  [{f['type']}] {f['title']}")

# Test 5: Personal lookup detection
q5 = "내 주문번호 1234 배송 상태 알려줘"
print(f"\n--- Test 5: {q5}")
print(f"is_personal_lookup: {faq_store.is_personal_lookup(q5)}")

# Test 6: Unrelated question
q6 = "오늘 날씨 어때?"
faqs6 = faq_store.retrieve_relevant_faqs(q6, limit=5)
print(f"\n--- Test 6: {q6}")
print(f"Retrieved {len(faqs6)} FAQs (should be 0):")
for f in faqs6:
    print(f"  [{f['type']}] {f['title']}")
print(f"is_personal_lookup: {faq_store.is_personal_lookup(q6)}")

# Test 7: Personal lookup answer
q7 = "내 결제 상태 확인해줘"
print(f"\n--- Test 7: {q7}")
print(f"is_personal_lookup: {faq_store.is_personal_lookup(q7)}")

# Test 8: 비밀번호
q8 = "비밀번호를 잊어버렸어요"
faqs8 = faq_store.retrieve_relevant_faqs(q8, limit=5)
print(f"\n--- Test 8: {q8}")
print(f"Retrieved {len(faqs8)} FAQs:")
for f in faqs8:
    print(f"  [{f['type']}] {f['title']}")

# Test 9: 내 환불
q9 = "내 환불 처리됐어?"
print(f"\n--- Test 9: {q9}")
print(f"is_personal_lookup: {faq_store.is_personal_lookup(q9)}")

# Test 10: 회원가입
q10 = "회원가입 어떻게 하나요?"
faqs10 = faq_store.retrieve_relevant_faqs(q10, limit=5)
print(f"\n--- Test 10: {q10}")
print(f"Retrieved {len(faqs10)} FAQs:")
for f in faqs10:
    print(f"  [{f['type']}] {f['title']}")

# Build context for test 1
ctx = faq_store.build_faq_context(faqs1)
print(f"\n--- Context for test 1 (first 500 chars):")
print(ctx[:500])

# Test 11: check personal answer text
print(f"\n--- Personal lookup answer:")
print(faq_store.PERSONAL_LOOKUP_ANSWER)

print(f"\n--- Unknown fallback answer:")
print(faq_store.UNKNOWN_FALLBACK_ANSWER)

print("\n=== All verification tests completed ===")