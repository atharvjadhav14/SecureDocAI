
import re
import unicodedata

from secure_semantic_search import search_authorized_documents
from llm_provider import generate_answer


TENANT_ID = 1
SIMILARITY_THRESHOLD = 0.30

TEST_CASES = [
    {
        "question": "How many vacation days do employees get each year?",
        "expected_keywords": ["18 days"],
        "must_refuse": False,
    },
    {
        "question": "How far in advance should planned leave be requested?",
        "expected_keywords": ["3 days"],
        "must_refuse": False,
    },
    {
        "question": "What should an employee do during emergency leave?",
        "expected_keywords": ["manager"],
        "must_refuse": False,
    },
    {
        "question": "Who invented Python?",
        "expected_keywords": [],
        "must_refuse": True,
    },
    {
        "question": "Can employees carry forward unused leave?",
        "expected_keywords": [],
        "must_refuse": True,
    },
]


def normalize_text(text: str) -> str:
    """Normalize Unicode and whitespace before comparing text."""
    text = unicodedata.normalize("NFKC", text).lower()
    return re.sub(r"\s+", " ", text).strip()


def is_refusal(answer: str) -> bool:
    """Check whether the AI explicitly refuses an unsupported question."""
    text = normalize_text(answer)

    refusal_phrases = [
        "could not find the answer",
        "cannot find the answer",
        "couldn't find the answer",
        "not found in the authorized documents",
        "not available in the authorized documents",
        "does not contain",
        "do not contain",
        "not specified in the document",
        "not mentioned in the document",
        "not enough information",
        "insufficient information",
    ]

    return any(phrase in text for phrase in refusal_phrases)


def run_evaluation():
    passed = 0
    failed = 0

    print("=" * 65)
    print("SecureDoc AI - Generated Answer Evaluation")
    print("=" * 65)

    for number, test in enumerate(TEST_CASES, start=1):
        question = test["question"]

        print(f"\nTest {number}: {question}")

        try:
            results = search_authorized_documents(
                question=question,
                tenant_id=TENANT_ID,
                top_k=3,
            )

            # Keep only passages above the retrieval threshold.
            context_results = [
                result
                for result in results
                if result["similarity"] >= SIMILARITY_THRESHOLD
            ]

            if not context_results:
                answer = (
                    "I could not find the answer in the authorized documents."
                )
            else:
                context = "\n\n".join(
                    result["content"] for result in context_results
                )

                answer = generate_answer(
                    question=question,
                    context=context,
                )

            print("AI answer:", answer)

            refused = is_refusal(answer)

            # IMPORTANT: Use separate logic for refusal and answer tests.
            if test["must_refuse"]:
                # Unsupported questions must receive a refusal.
                success = refused
            else:
                # Supported questions must not be refused and should
                # contain all expected keywords.
                answer_normalized = normalize_text(answer)

                success = (
                    not refused
                    and all(
                        normalize_text(keyword) in answer_normalized
                        for keyword in test["expected_keywords"]
                    )
                )

            if success:
                passed += 1
                print("Result: PASS")
            else:
                failed += 1
                print("Result: FAIL")

                if test["must_refuse"]:
                    print("Expected: A refusal based on missing evidence.")
                else:
                    print("Expected keywords:", test["expected_keywords"])

        except Exception as error:
            failed += 1
            print("Result: ERROR")
            print("Error type:", type(error).__name__)
            print(
                "Check the API key, internet connection, "
                "and model access."
            )

    total = len(TEST_CASES)

    print("\n" + "=" * 65)
    print("FINAL SUMMARY")
    print("=" * 65)
    print(f"Total tests: {total}")
    print(f"Passed: {passed}")
    print(f"Failed/errors: {failed}")
    print(f"Pass rate: {passed / total * 100:.1f}%")

    if failed == 0:
        print("All evaluation checks passed.")
    else:
        print("Some evaluation checks need investigation.")


if __name__ == "__main__":
    run_evaluation()
